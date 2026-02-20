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
async def download_video(url: str = Form(...)):
    file_id = str(uuid.uuid4())
    template = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

    opts = {
        "outtmpl": template,
        "format": "best[height<=1080]",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "no_config": True,
        "age_limit": None,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android_creator"],
                "skip": ["hls", "dash", "translated_subs"],
            }
        },
        "http_headers": {
            "User-Agent": "com.google.android.apps.youtube.creator/24.06.103 (Linux; U; Android 14; en_US) gzip",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-us,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "X-YouTube-Client-Name": "14",
            "X-YouTube-Client-Version": "24.06.103",
        },
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info.get("ext", "mp4")

        filename = f"{file_id}.{ext}"
        return JSONResponse({"file": f"/api/file/{filename}"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


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