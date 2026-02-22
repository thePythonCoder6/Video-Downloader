from fastapi import FastAPI, Form, Cookie, Response as FastAPIResponse
from fastapi.responses import FileResponse, JSONResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import uuid
import os
import re
import hashlib
import secrets
import bcrypt
import json
from pathlib import Path
from datetime import datetime

app = FastAPI()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Load credentials from Render Secret File
SECRETS_FILE = "/etc/secrets/credentials"

def load_credentials():
    """Load credentials from Render secret file"""
    print(f"🔍 Looking for secret file at: {SECRETS_FILE}")
    print(f"🔍 File exists: {os.path.exists(SECRETS_FILE)}")
    
    try:
        if os.path.exists(SECRETS_FILE):
            with open(SECRETS_FILE, "r") as f:
                content = f.read()
                print(f"🔍 File content length: {len(content)} bytes")
                secrets_data = json.loads(content)
                username = secrets_data.get("username", "thepythoncoder6")
                password = secrets_data.get("password", "Qwertyuiop!")
                print(f"✅ Loaded credentials from {SECRETS_FILE}")
                print(f"✅ Username from file: {username}")
                return username.lower(), password
    except Exception as e:
        print(f"⚠️  Error loading secret file: {e}")
        import traceback
        traceback.print_exc()
    
    # Fallback to default
    print(f"⚠️  Using default credentials")
    return "thepythoncoder6", "Qwertyuiop!"

USERNAME, DEFAULT_PASSWORD = load_credentials()
PASSWORD_HASH = bcrypt.hashpw(DEFAULT_PASSWORD.encode(), bcrypt.gensalt()).decode()
print(f"✅ Final username (lowercase): {USERNAME}")
print(f"✅ Password length: {len(DEFAULT_PASSWORD)} chars")

# Session storage (persistent file-based)
SESSION_FILE = os.path.join(DOWNLOAD_DIR, ".sessions.json")

def load_sessions():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_sessions():
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump(list(active_sessions), f)
    except:
        pass

active_sessions = load_sessions()

# Download history storage
HISTORY_FILE = os.path.join(DOWNLOAD_DIR, ".history.json")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history_data(history):
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except:
        pass

def extract_title_from_info(info):
    """Extract video title from yt-dlp info"""
    if not info:
        return "Video"
    
    title = info.get('title', '')
    if title:
        return title[:100]  # Limit length
    
    # Fallback to uploader or video ID
    uploader = info.get('uploader', '')
    video_id = info.get('id', '')
    
    if uploader and video_id:
        return f"{uploader} - {video_id}"
    elif video_id:
        return f"Video {video_id}"
    
    return "Video"


@app.post("/api/login")
async def login(username: str = Form(...), password: str = Form(...)):
    # Check username and password hash
    if username.lower() == USERNAME and bcrypt.checkpw(password.encode(), PASSWORD_HASH.encode()):
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        active_sessions.add(session_token)
        save_sessions()
        
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
        save_sessions()
    
    response = JSONResponse({"success": True})
    response.delete_cookie("session")
    return response


def check_auth(session: str = Cookie(None)):
    return session and session in active_sessions


@app.post("/api/download")
async def download_video(url: str = Form(...), cookies: str = Form(""), format: str = Form("mp4"), session: str = Cookie(None)):
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

    # Configure format based on user selection
    audio_formats = ['mp3', 'm4a', 'wav', 'flac', 'aac', 'opus', 'vorbis']
    video_formats = ['mp4', 'webm', 'mkv', 'avi', 'mov', 'flv']
    
    if format in audio_formats:
        # Audio extraction
        quality = "0" if format in ['wav', 'flac'] else "192"
        opts = {
            "outtmpl": template,
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": format if format != 'vorbis' else 'vorbis',
                "preferredquality": quality,
            }],
            "extractor_args": {
                "youtube": {
                    "player_client": ["tv_embedded"],
                }
            },
        }
    elif format in video_formats:
        # Video conversion
        if format == "mp4":
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
        else:
            # For other video formats, download and convert
            opts = {
                "outtmpl": template,
                "format": "best",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "postprocessors": [{
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": format,
                }],
                "extractor_args": {
                    "youtube": {
                        "player_client": ["tv_embedded"],
                    }
                },
            }
    else:
        # Default to MP4
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
        
        # Add to history
        history = load_history()
        history_item = {
            "id": file_id,
            "url": url,
            "file": f"/api/file/{filename}",
            "filename": filename,
            "timestamp": datetime.now().isoformat(),
            "title": extract_title_from_info(info)
        }
        history.insert(0, history_item)  # Add to beginning
        
        # Keep only last 50 videos
        if len(history) > 50:
            history = history[:50]
        
        save_history_data(history)
        
        return JSONResponse({"file": f"/api/file/{filename}", "id": file_id})

    except Exception as e:
        error_msg = str(e)
        
        # If bot detection and it's a YouTube URL, try multiple Invidious instances
        if ("Sign in to confirm" in error_msg or "bot" in error_msg.lower()) and "youtube.com" in url:
            # Extract video ID
            video_id_match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', url)
            if video_id_match:
                video_id = video_id_match.group(1)
                
                # List of Invidious instances to try
                invidious_instances = [
                    "https://inv.nadeko.net",
                    "https://invidious.privacyredirect.com",
                    "https://yewtu.be",
                    "https://invidious.fdn.fr",
                    "https://inv.riverside.rocks",
                ]
                
                # Strategy 1: Try youtube-nocookie domain
                try:
                    nocookie_url = url.replace("youtube.com", "youtube-nocookie.com")
                    print(f"🔄 Trying youtube-nocookie: {nocookie_url}")
                    
                    opts_nocookie = {
                        "outtmpl": template,
                        "format": "best",
                        "noplaylist": True,
                        "quiet": True,
                        "socket_timeout": 30,
                        "extractor_args": {
                            "youtube": {
                                "player_client": ["tv_embedded"],
                            }
                        },
                    }
                    
                    with yt_dlp.YoutubeDL(opts_nocookie) as ydl:
                        info = ydl.extract_info(nocookie_url, download=True)
                        ext = info.get("ext", "mp4")

                    filename = f"{file_id}.{ext}"
                    
                    # Add to history
                    history = load_history()
                    history_item = {
                        "id": file_id,
                        "url": url,
                        "file": f"/api/file/{filename}",
                        "filename": filename,
                        "timestamp": datetime.now().isoformat(),
                        "title": extract_title_from_info(info)
                    }
                    history.insert(0, history_item)
                    
                    if len(history) > 50:
                        history = history[:50]
                    
                    save_history_data(history)
                    
                    print(f"✅ Successfully downloaded via youtube-nocookie")
                    return JSONResponse({"file": f"/api/file/{filename}", "id": file_id})
                    
                except Exception as nocookie_error:
                    print(f"❌ youtube-nocookie failed: {nocookie_error}")
                
                # Strategy 2: Try Invidious instances
                last_inv_error = None
                for instance in invidious_instances:
                    try:
                        invidious_url = f"{instance}/watch?v={video_id}"
                        print(f"🔄 Trying Invidious instance: {instance}")
                        
                        opts_inv = {
                            "outtmpl": template,
                            "format": "best",
                            "noplaylist": True,
                            "quiet": True,
                            "socket_timeout": 30,
                        }
                        
                        with yt_dlp.YoutubeDL(opts_inv) as ydl:
                            info = ydl.extract_info(invidious_url, download=True)
                            ext = info.get("ext", "mp4")

                        filename = f"{file_id}.{ext}"
                        
                        # Add to history
                        history = load_history()
                        history_item = {
                            "id": file_id,
                            "url": url,
                            "file": f"/api/file/{filename}",
                            "filename": filename,
                            "timestamp": datetime.now().isoformat(),
                            "title": extract_title_from_info(info)
                        }
                        history.insert(0, history_item)
                        
                        if len(history) > 50:
                            history = history[:50]
                        
                        save_history_data(history)
                        
                        print(f"✅ Successfully downloaded via {instance}")
                        return JSONResponse({"file": f"/api/file/{filename}", "id": file_id})
                        
                    except Exception as inv_error:
                        last_inv_error = str(inv_error)
                        print(f"❌ {instance} failed: {inv_error}")
                        continue  # Try next instance
                
                # All strategies failed
                return JSONResponse({"error": f"YouTube blocked. Tried youtube-nocookie and all Invidious instances. Last error: {last_inv_error}. Try providing cookies."}, status_code=500)
        
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


@app.get("/api/history")
async def get_history(session: str = Cookie(None)):
    if not check_auth(session):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    history = load_history()
    return JSONResponse({"history": history})


@app.delete("/api/history/{video_id}")
async def delete_history_item(video_id: str, session: str = Cookie(None)):
    if not check_auth(session):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    history = load_history()
    
    # Find the item to delete
    item_to_delete = None
    for item in history:
        if item.get("id") == video_id:
            item_to_delete = item
            break
    
    # Remove from history
    history = [item for item in history if item.get("id") != video_id]
    save_history_data(history)
    
    # Delete the actual file
    if item_to_delete:
        filename = item_to_delete.get("filename")
        if filename:
            file_path = os.path.join(DOWNLOAD_DIR, filename)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
    
    return JSONResponse({"success": True})


@app.post("/api/history/clear")
async def clear_history(session: str = Cookie(None)):
    if not check_auth(session):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    # Get all files from history before clearing
    history = load_history()
    
    # Delete all video files
    for item in history:
        filename = item.get("filename")
        if filename:
            file_path = os.path.join(DOWNLOAD_DIR, filename)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
    
    # Clear history
    save_history_data([])
    
    return JSONResponse({"success": True})


@app.get("/api/check-auth")
async def check_auth_endpoint(session: str = Cookie(None)):
    return JSONResponse({"authenticated": check_auth(session)})
