import re
from urllib.parse import urlparse

import requests

from media_url_extractor.media import ExtractionError, Media, reading

API = "https://api.redgifs.com/v2"
# RedGifs rejects API requests without these site-origin headers.
_HEADERS = {"referer": "https://www.redgifs.com/", "origin": "https://www.redgifs.com"}

_GIF_PATH = re.compile(r"/(?:watch|ifr)/([a-z0-9]+)", re.IGNORECASE)


def get_media(url: str) -> list[Media]:
    match = _GIF_PATH.search(urlparse(url).path)
    if not match:
        raise ValueError(f"Not a RedGifs watch URL: {url}")
    return [Media("video", get_video_url(match.group(1)))]


def get_video_url(gif_id: str) -> str:
    token = requests.get(f"{API}/auth/temporary", headers=_HEADERS, timeout=10)
    token.raise_for_status()
    with reading("RedGifs"):
        headers = {**_HEADERS, "authorization": f"Bearer {token.json()['token']}"}

    gif = requests.get(f"{API}/gifs/{gif_id.lower()}", headers=headers, timeout=10)
    gif.raise_for_status()
    with reading("RedGifs"):
        urls = gif.json()["gif"]["urls"]
        url = urls.get("hd") or urls.get("sd")
    if not url:
        raise ExtractionError("The gif has no video file")
    return str(url)
