"""Read Instagram posts through instagrapi with a logged-in account.

Instagram shows anonymous visitors a login wall. Credentials come from
INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD. The session is kept in
INSTAGRAM_SESSION_FILE, which defaults to instagram_session.json.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

from media_url_extractor.media import ExtractionError, Media, reading

if TYPE_CHECKING:
    from instagrapi.types import Media as InstagramMedia

PHOTO, VIDEO, ALBUM = 1, 2, 8


class InstagramApi(Protocol):
    def media_pk_from_url(self, url: str) -> str: ...

    def media_info(self, media_pk: str) -> InstagramMedia: ...


@contextmanager
def _instagram_errors() -> Iterator[None]:
    # Import instagrapi on first use because its import is slow.
    from instagrapi.exceptions import ClientError

    try:
        with reading("Instagram"):
            yield
    except ClientError as exc:
        raise ExtractionError(f"Instagram refused the request: {exc}") from exc


def get_media(url: str, client: InstagramApi | None = None) -> list[Media]:
    with _instagram_errors():
        api = client or default_client()
        post = api.media_info(api.media_pk_from_url(url))

        if post.media_type == ALBUM:
            return [
                item
                for resource in post.resources
                if (item := _item(resource.media_type, resource.video_url, resource.thumbnail_url))
            ]
        item = _item(post.media_type, post.video_url, post.thumbnail_url)
        return [item] if item else []


def get_video_url(media_id: str, client: InstagramApi | None = None) -> str:
    with _instagram_errors():
        api = client or default_client()
        post = api.media_info(media_id)
        if post.media_type != VIDEO or post.video_url is None:
            raise ExtractionError("The post is not a video")
        return str(post.video_url)


def _item(media_type: int, video_url: object, image_url: object) -> Media | None:
    if media_type == VIDEO and video_url:
        return Media("video", str(video_url))
    if media_type == PHOTO and image_url:
        return Media("image", str(image_url))
    return None


@cache
def default_client() -> InstagramApi:
    from instagrapi import Client

    username = os.environ.get("INSTAGRAM_USERNAME")
    password = os.environ.get("INSTAGRAM_PASSWORD")
    if not username or not password:
        raise ExtractionError("Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD to read Instagram")

    session = Path(os.environ.get("INSTAGRAM_SESSION_FILE", "instagram_session.json"))
    client = Client()
    with _instagram_errors():
        if session.exists():
            client.load_settings(session)
        client.login(username, password)
        client.dump_settings(session)
    return cast(InstagramApi, client)
