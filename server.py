from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
import yt_dlp
import uuid
import os

app = FastAPI()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


@app.post("/api/download")
async def download_video(url: str = Form(...), cookies: str = Form("")):
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

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info.get("ext", "mp4")

        filename = f"{file_id}.{ext}"
        return JSONResponse({"file": f"/api/file/{filename}"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    
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
async def index():
    return FileResponse("static/index.html")


@app.head("/")
async def head_index():
    return Response(status_code=200)
