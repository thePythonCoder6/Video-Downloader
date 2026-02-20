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

    # Try multiple strategies
    strategies = [
        # Strategy 1: Use proxy
        {
            "outtmpl": template,
            "format": "best",
            "noplaylist": True,
            "quiet": True,
            "proxy": "socks5://orbtl.com:4145",
            "socket_timeout": 30,
        },
        # Strategy 2: tv_embedded with no check certificate
        {
            "outtmpl": template,
            "format": "best",
            "noplaylist": True,
            "quiet": True,
            "nocheckcertificate": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["tv_embedded"],
                    "skip": ["translated_subs"],
                }
            },
        },
        # Strategy 3: mediaconnect client
        {
            "outtmpl": template,
            "format": "best",
            "noplaylist": True,
            "quiet": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["mediaconnect"],
                }
            },
        },
    ]

    last_error = None
    for i, opts in enumerate(strategies, 1):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                ext = info.get("ext", "mp4")

            filename = f"{file_id}.{ext}"
            return JSONResponse({"file": f"/api/file/{filename}"})

        except Exception as e:
            last_error = str(e)
            if i < len(strategies):
                continue  # Try next strategy
            
    return JSONResponse({"error": f"All download strategies failed. Last error: {last_error}"}, status_code=500)


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