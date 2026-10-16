import json
import re
from typing import Any
from urllib.parse import urlparse

import requests

from media_url_extractor.media import ExtractionError, Media, reading

ENDPOINT = "https://cdn.syndication.twimg.com/tweet-result"
# The endpoint returns an empty object for an empty token. Use any nonempty token.
TOKEN = "1"

_STATUS_PATH = re.compile(r"/status(?:es)?/(\d+)")


def get_media(url: str) -> list[Media]:
    """Return the photos and videos of a post, its quoted posts and its card."""
    match = _STATUS_PATH.search(urlparse(url).path)
    if not match:
        raise ValueError(f"Not a Twitter status URL: {url}")

    response = requests.get(
        ENDPOINT,
        params={"id": match.group(1), "lang": "en", "token": TOKEN},
        timeout=10,
    )
    response.raise_for_status()
    with reading("Twitter"):
        tweet: dict[str, Any] = response.json()
        if not tweet or tweet.get("__typename") == "TweetTombstone":
            raise ExtractionError("The post is deleted, private or age-restricted")

        media: list[Media] = []
        while True:
            media += _media_details(tweet.get("mediaDetails", []))
            media += _card_media(tweet.get("card", {}))
            if "quoted_tweet" not in tweet:
                return media
            tweet = tweet["quoted_tweet"]


def _media_details(details: list[dict[str, Any]]) -> list[Media]:
    media: list[Media] = []
    for detail in details:
        if detail["type"] in ("video", "animated_gif"):
            mp4s = [
                variant
                for variant in detail["video_info"]["variants"]
                if variant["content_type"] == "video/mp4"
            ]
            if not mp4s:
                raise ExtractionError("The video has no MP4 file")
            best = max(mp4s, key=lambda variant: variant["bitrate"])
            media.append(Media("video", best["url"]))
        else:
            media.append(Media("image", detail["media_url_https"]))
    return media


def _card_media(card: dict[str, Any]) -> list[Media]:
    values = card.get("binding_values", {})
    if "unified_card" in values:
        unified = json.loads(values["unified_card"]["string_value"])
        return _media_details(list(unified["media_entities"].values()))
    image = values.get("thumbnail_image_original", {}).get("image_value", {})
    if "url" in image:
        return [Media("image", image["url"])]
    return []
