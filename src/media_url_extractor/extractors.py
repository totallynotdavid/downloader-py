from collections.abc import Callable
from urllib.parse import urlparse

import requests

from media_url_extractor.media import ExtractionError, Media
from media_url_extractor.platforms import imgur, instagram, reddit, redgifs, twitter

_PLATFORMS: dict[str, tuple[tuple[str, ...], Callable[[str], list[Media]]]] = {
    "twitter": (("twitter.com", "x.com"), twitter.get_media),
    "instagram": (("instagram.com",), instagram.get_media),
    "reddit": (("reddit.com",), reddit.get_media),
    "redgifs": (("redgifs.com",), redgifs.get_media),
    "imgur": (("imgur.com",), imgur.get_media),
}


def platform_of(url: str) -> str | None:
    host = urlparse(url).hostname or ""
    for name, (domains, _) in _PLATFORMS.items():
        if any(host == domain or host.endswith(f".{domain}") for domain in domains):
            return name
    return None


def extract(url: str) -> list[Media]:
    platform = platform_of(url)
    if platform is None:
        raise ValueError(f"Unsupported platform: {url}")
    try:
        return _PLATFORMS[platform][1](url)
    except requests.RequestException as exc:
        raise ExtractionError(f"{platform} request failed: {exc}") from exc
