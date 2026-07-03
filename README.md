# YouTube Download API

Bot te /short, /video, /download banate eibhabe use koro:

## Auth
Shob `/api/*` call e header lagbe:
```
X-API-Key: SHUVO-apis
```

## /video and /short -> search
`POST /api/search`
```json
{"query": "lofi music", "type": "video", "limit": 5}
```
`type: "short"` dile 60 sec er niche duration wala video filter hoye ashbe.
Response: list of `{video_id, title, channel, duration, view_count, thumbnail, url}`

Bot flow: user `/video <text>` or `/short <text>` dile -> eita call koro -> result list theke user ekta select korবে -> oi `url` diye `/api/download` call koro.

## Full metadata (title, channel, upload date, views, likes, subscribers)
`POST /api/info`
```json
{"url": "https://youtube.com/watch?v=..."}
```
Response:
```json
{
  "title": "...", "channel": "...", "upload_date": "20260701",
  "duration": 245, "view_count": 12345, "like_count": 890,
  "subscriber_count": 45000, "thumbnail": "...", "url": "..."
}
```
Note: `subscriber_count` shob video te naao ashte pare (YouTube depend kore), null hote pare.

## /download -> video file
`POST /api/download`
```json
{"url": "https://youtube.com/watch?v=..."}
```
Always mp4.

## /audio -> song, surah, waz, ba jekono audio-only content
`POST /api/audio`
```json
{"url": "https://youtube.com/watch?v=..."}
```
Always mp3. Bot e `/audio` command diye eita call koro.

## Root endpoint
`GET /` khule shob endpoint (path + body format) dekha jabe — UptimeRobot ping korার jonyo o eita e (open, auth lagbe na).

## Setup
1. `pip install -r requirements.txt`
2. `cookies.txt` already included (YouTube-only cookies).
3. Audio extraction (`audio_only: true`) er jonno **ffmpeg** lagbe server e install kora — Render/Railway er base image e already thake, local e na thakle `apt install ffmpeg`.
4. Run: `python main.py`

## Deploy on Render
Same as TikTok API — private repo push, build `pip install -r requirements.txt`, start `uvicorn main:app --host 0.0.0.0 --port $PORT`.
