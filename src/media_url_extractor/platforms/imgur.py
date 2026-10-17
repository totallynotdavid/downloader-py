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
    try:
        with YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            extracted = ydl.extract_info(url, download=False)
            sanitized = ydl.sanitize_info(extracted) if extracted else None
    except YoutubeDLError as exc:
        raise ExtractionError(str(exc)) from exc

    if sanitized is None:
        raise ExtractionError("Imgur returned no media")

    with reading("Imgur"):
        info: dict[str, Any] = dict(sanitized)
        entries = info.get("entries") or [info]
        return [Media("video", entry["url"]) for entry in entries]
