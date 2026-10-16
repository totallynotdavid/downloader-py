"""Imgur images, videos and animations.

A direct i.imgur.com link names its file, so it needs no request. A post page is
resolved by yt-dlp, which reads only videos and animations from it.
"""

from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlparse

from yt_dlp import YoutubeDL
from yt_dlp.utils import YoutubeDLError

from media_url_extractor.media import ExtractionError, Media, reading

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
_VIDEO_SUFFIXES = {".gifv", ".mp4"}


def get_media(url: str) -> list[Media]:
    parsed = urlparse(url)
    path = PurePosixPath(parsed.path)
    if parsed.hostname == "i.imgur.com":
        suffix = path.suffix.lower()
        if suffix in _IMAGE_SUFFIXES:
            return [Media("image", f"https://i.imgur.com{path}")]
        if suffix in _VIDEO_SUFFIXES:
            return [Media("video", f"https://i.imgur.com{path.with_suffix('.mp4')}")]
    return _resolve_post(url)


def _resolve_post(url: str) -> list[Media]:
    options = {"quiet": True, "no_warnings": True, "skip_download": True}
    try:
        with YoutubeDL(options) as ydl:
            info: dict[str, Any] = ydl.sanitize_info(ydl.extract_info(url, download=False))
    except YoutubeDLError as exc:
        raise ExtractionError(str(exc)) from exc

    with reading("Imgur"):
        entries = info.get("entries") or [info]
        return [Media("video", entry["url"]) for entry in entries]
