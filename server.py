from fastapi import FastAPI, Form, Cookie, Response as FastAPIResponse
from fastapi.responses import FileResponse, JSONResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import uuid
import os
import re
import hashlib
import secrets

app = FastAPI()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Login credentials
USERNAME = "thepythoncoder6"  # Case insensitive
PASSWORD = "Qwertyuiop!"

# Session storage (in-memory)
active_sessions = set()


@app.post("/api/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if username.lower() == USERNAME and password == PASSWORD:
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        active_sessions.add(session_token)
        
        response = JSONResponse({"success": True})
        response.set_cookie(
            key="session",
            value=session_token,
            httponly=True,
            max_age=86400,  # 24 hours
            samesite="lax"
        )
        return response
    
    return JSONResponse({"error": "Invalid credentials"}, status_code=401)


@app.post("/api/logout")
async def logout(session: str = Cookie(None)):
    if session in active_sessions:
        active_sessions.remove(session)
    
    response = JSONResponse({"success": True})
    response.delete_cookie("session")
    return response


def check_auth(session: str = Cookie(None)):
    return session and session in active_sessions


@app.post("/api/download")
async def download_video(url: str = Form(...), cookies: str = Form(""), session: str = Cookie(None)):
    if not check_auth(session):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    file_id = str(uuid.uuid4())
    template = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")
    cookies_file = None
    
    # If cookies provided, save to temp file
    if cookies and cookies.strip():
        cookies_file = os.path.join(DOWNLOAD_DIR, f"{file_id}_cookies.txt")
        with open(cookies_file, "w") as f:
            f.write(cookies.strip())

    opts = {
        "outtmpl": template,
        "format": "best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["tv_embedded"],
            }
        },
    }
    
    # Add cookies file if provided
    if cookies_file:
        opts["cookiefile"] = cookies_file

    # Try direct YouTube download first
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info.get("ext", "mp4")

        filename = f"{file_id}.{ext}"
        return JSONResponse({"file": f"/api/file/{filename}"})

    except Exception as e:
        error_msg = str(e)
        
        # If bot detection and it's a YouTube URL, try Invidious
        if ("Sign in to confirm" in error_msg or "bot" in error_msg.lower()) and "youtube.com" in url:
            # Extract video ID
            video_id_match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', url)
            if video_id_match:
                video_id = video_id_match.group(1)
                invidious_url = f"https://invidious.jing.rocks/watch?v={video_id}"
                
                try:
                    opts_inv = {
                        "outtmpl": template,
                        "format": "best",
                        "noplaylist": True,
                        "quiet": True,
                    }
                    
                    with yt_dlp.YoutubeDL(opts_inv) as ydl:
                        info = ydl.extract_info(invidious_url, download=True)
                        ext = info.get("ext", "mp4")

                    filename = f"{file_id}.{ext}"
                    return JSONResponse({"file": f"/api/file/{filename}"})
                    
                except Exception as inv_error:
                    return JSONResponse({"error": f"YouTube blocked and Invidious failed: {str(inv_error)}. Try providing cookies."}, status_code=500)
        
        return JSONResponse({"error": f"{error_msg}. For YouTube, try providing cookies."}, status_code=500)
    
    finally:
        # Clean up cookies file
        if cookies_file and os.path.exists(cookies_file):
            try:
                os.remove(cookies_file)
            except:
                pass


@app.get("/api/file/{filename}")
async def get_file(filename: str):
    path = os.path.join(DOWNLOAD_DIR, filename)

    if not os.path.exists(path):
        return JSONResponse({"error": "File not found"}, status_code=404)

    return FileResponse(path, filename=filename)


@app.get("/")
async def index(session: str = Cookie(None)):
    if not check_auth(session):
        return FileResponse("static/login.html")
    return FileResponse("static/index.html")


@app.head("/")
async def head_index():
    return Response(status_code=200)


@app.get("/api/check-auth")
async def check_auth_endpoint(session: str = Cookie(None)):
    return JSONResponse({"authenticated": check_auth(session)})
