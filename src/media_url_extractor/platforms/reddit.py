from typing import Any
from urllib.parse import urlparse, urlunparse

import requests

from media_url_extractor.media import ExtractionError, Media, reading

USER_AGENT = "media-url-extractor/1.0"


def get_media(url: str) -> list[Media]:
    parsed = urlparse(url)
    json_url = urlunparse(
        parsed._replace(
            scheme="https",
            path=parsed.path.rstrip("/") + ".json",
            query="raw_json=1",
            fragment="",
        )
    )
    response = requests.get(json_url, headers={"User-Agent": USER_AGENT}, timeout=10)
    if response.status_code in (403, 429):
        raise ExtractionError(f"Reddit refused the request (HTTP {response.status_code})")
    response.raise_for_status()

    with reading("Reddit"):
        post = response.json()[0]["data"]["children"][0]["data"]
        return _post_media(post)


def _post_media(post: dict[str, Any]) -> list[Media]:
    if parents := post.get("crosspost_parent_list"):
        post = parents[0]

    metadata = post.get("media_metadata")
    if metadata:
        return _gallery_media(post, metadata)

    hint = post.get("post_hint")
    if hint == "image":
        return [Media("image", post["url"])]
    if hint == "hosted:video":
        return [Media("video", post["media"]["reddit_video"]["fallback_url"])]
    if hint in ("rich:video", "link"):
        return [
            Media("image", image["source"]["url"])
            for image in post.get("preview", {}).get("images", [])
        ]
    return []


def _gallery_media(post: dict[str, Any], metadata: dict[str, Any]) -> list[Media]:
    # Read gallery_data because media_metadata does not preserve gallery order.
    order = [item["media_id"] for item in post.get("gallery_data", {}).get("items", [])]
    media: list[Media] = []
    for media_id in order or metadata:
        source = metadata.get(media_id, {}).get("s", {})
        if "mp4" in source:
            media.append(Media("video", source["mp4"]))
        elif "gif" in source:
            media.append(Media("image", source["gif"]))
        elif "u" in source:
            media.append(Media("image", source["u"]))
    return media
