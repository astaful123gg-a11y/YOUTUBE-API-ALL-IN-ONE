import os
import uuid
import glob
import yt_dlp
from fastapi import FastAPI, HTTPException, Header, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="YouTube Download API")

API_PASSWORD = "SHUVO-apis"
COOKIES_FILE = os.environ.get("COOKIES_FILE", "cookies.txt")
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def check_auth(x_api_key: str = Header(default=None)):
    if x_api_key != API_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


class SearchRequest(BaseModel):
    query: str
    type: str = "video"   # "video" or "short"
    limit: int = 5


class UrlRequest(BaseModel):
    url: str
    audio_only: bool = False


def base_opts():
    opts = {
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 20,
        "retries": 3,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }
    if os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
    return opts


@app.get("/")
def health():
    return {
        "status": "ok",
        "service": "YouTube Download API",
        "auth": "Header X-API-Key: SHUVO-apis (required on all /api/* routes)",
        "endpoints": {
            "search (/video, /short)": {
                "method": "POST",
                "path": "/api/search",
                "body": {"query": "string", "type": "video | short", "limit": 5},
            },
            "info": {
                "method": "POST",
                "path": "/api/info",
                "body": {"url": "string"},
            },
            "download (/download)": {
                "method": "POST",
                "path": "/api/download",
                "body": {"url": "string"},
            },
            "audio (/audio)": {
                "method": "POST",
                "path": "/api/audio",
                "body": {"url": "string"},
            },
        },
    }


# ---------- /video and /short -> search ----------
@app.post("/api/search", dependencies=[Depends(check_auth)])
def search(req: SearchRequest):
    opts = base_opts()
    opts["ignoreerrors"] = True
    opts["extract_flat"] = "in_playlist"   # fast listing, no per-video format resolution
    fetch_n = req.limit * 3 if req.type == "short" else req.limit

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            result = ydl.extract_info(f"ytsearch{fetch_n}:{req.query}", download=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Search failed: {e}")

    entries = [e for e in (result.get("entries") or []) if e]
    items = []
    for e in entries:
        duration = e.get("duration") or 0
        if req.type == "short" and duration > 60:
            continue
        items.append({
            "video_id": e.get("id"),
            "title": e.get("title"),
            "channel": e.get("channel") or e.get("uploader"),
            "duration": duration,
            "view_count": e.get("view_count"),
            "thumbnail": e.get("thumbnails", [{}])[-1].get("url") if e.get("thumbnails") else None,
            "url": f"https://www.youtube.com/watch?v={e.get('id')}",
        })
        if len(items) >= req.limit:
            break

    return {"query": req.query, "type": req.type, "results": items}


# ---------- full metadata (title, channel, date, views, likes, subscribers) ----------
@app.post("/api/info", dependencies=[Depends(check_auth)])
def get_info(req: UrlRequest):
    try:
        with yt_dlp.YoutubeDL(base_opts()) as ydl:
            info = ydl.extract_info(req.url, download=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Extract failed: {e}")

    return {
        "title": info.get("title"),
        "channel": info.get("uploader") or info.get("channel"),
        "channel_url": info.get("channel_url") or info.get("uploader_url"),
        "upload_date": info.get("upload_date"),        # YYYYMMDD
        "duration": info.get("duration"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "subscriber_count": info.get("channel_follower_count"),
        "thumbnail": info.get("thumbnail"),
        "url": req.url,
    }


class UrlOnlyRequest(BaseModel):
    url: str


def _do_download(url: str, audio_only: bool):
    file_id = str(uuid.uuid4())
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

    opts = base_opts()
    opts["outtmpl"] = outtmpl
    if not audio_only:
        opts["merge_output_format"] = "mp4"
    if audio_only:
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    format_chain = ["bestaudio/best"] if audio_only else ["best", "18", "worst"]

    info = None
    last_error = None
    for fmt in format_chain:
        opts["format"] = fmt
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            break
        except Exception as e:
            last_error = e
            continue

    if info is None:
        raise HTTPException(status_code=400, detail=f"Download failed: {last_error}")

    matches = [f for f in glob.glob(os.path.join(DOWNLOAD_DIR, f"{file_id}.*")) if not f.endswith(".part")]
    filepath = matches[0] if matches else None

    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=500, detail="File not found after download")

    ext = "mp3" if audio_only else "mp4"
    media_type = "audio/mpeg" if audio_only else "video/mp4"
    filename = f"{info.get('title', 'youtube_media')}.{ext}"

    cleanup = BackgroundTasks()
    cleanup.add_task(lambda p=filepath: os.remove(p) if os.path.exists(p) else None)
    return FileResponse(filepath, media_type=media_type, filename=filename, background=cleanup)


# ---------- /download -> video file ----------
@app.post("/api/download", dependencies=[Depends(check_auth)])
def download_file(req: UrlOnlyRequest):
    return _do_download(req.url, audio_only=False)


# ---------- /audio -> song, surah, waz, etc. mp3 only ----------
@app.post("/api/audio", dependencies=[Depends(check_auth)])
def download_audio(req: UrlOnlyRequest):
    return _do_download(req.url, audio_only=True)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
