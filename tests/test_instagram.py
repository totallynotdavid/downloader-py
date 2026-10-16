from datetime import datetime
from typing import ClassVar

import pytest
from instagrapi.exceptions import BadPassword, MediaNotFound
from instagrapi.types import Media as InstagramMedia
from instagrapi.types import Resource, UserShort

from media_url_extractor import ExtractionError, Media, extract
from media_url_extractor.platforms import instagram

PHOTO, VIDEO, ALBUM = 1, 2, 8


def post(media_type: int, **fields) -> InstagramMedia:
    return InstagramMedia(
        pk="3000000000000000001",
        id="3000000000000000001_1",
        code="Cl1Vt4YLrdk",
        taken_at=datetime(2023, 1, 1),
        media_type=media_type,
        user=UserShort(pk="1", username="someone"),
        like_count=0,
        caption_text="",
        usertags=[],
        sponsor_tags=[],
        **fields,
    )


class FakeInstagram:
    def __init__(self, post: InstagramMedia):
        self.post = post
        self.asked: list[str] = []

    def media_pk_from_url(self, url: str) -> str:
        self.asked.append(url)
        return self.post.pk if isinstance(self.post.pk, str) else str(self.post.pk)

    def media_info(self, media_pk: str) -> InstagramMedia:
        self.asked.append(media_pk)
        return self.post


@pytest.fixture
def logged_in(monkeypatch):
    def use(client: FakeInstagram) -> FakeInstagram:
        monkeypatch.setattr(instagram, "default_client", lambda: client)
        return client

    return use


def test_photo_returns_the_image(logged_in):
    client = logged_in(FakeInstagram(post(PHOTO, thumbnail_url="https://cdn.example/photo.jpg")))

    media = extract("https://www.instagram.com/p/CtId5TwAxT_/")

    assert media == [Media("image", "https://cdn.example/photo.jpg")]
    assert client.asked == ["https://www.instagram.com/p/CtId5TwAxT_/", "3000000000000000001"]


def test_reel_returns_the_video(logged_in):
    logged_in(
        FakeInstagram(
            post(
                VIDEO,
                video_url="https://cdn.example/reel.mp4",
                thumbnail_url="https://cdn.example/reel.jpg",
            )
        )
    )

    media = extract("https://www.instagram.com/reels/Crs-ukcAd3h/")

    assert media == [Media("video", "https://cdn.example/reel.mp4")]


def test_album_returns_each_resource_as_its_own_type(logged_in):
    resources = [
        Resource(pk="1", media_type=PHOTO, thumbnail_url="https://cdn.example/1.jpg"),
        Resource(
            pk="2",
            media_type=VIDEO,
            video_url="https://cdn.example/2.mp4",
            thumbnail_url="https://cdn.example/2.jpg",
        ),
    ]
    logged_in(FakeInstagram(post(ALBUM, resources=resources)))

    media = extract("https://www.instagram.com/p/Cqiy3EGuxvn/")

    assert media == [
        Media("image", "https://cdn.example/1.jpg"),
        Media("video", "https://cdn.example/2.mp4"),
    ]


def test_video_url_by_media_id(logged_in):
    client = logged_in(FakeInstagram(post(VIDEO, video_url="https://cdn.example/reel.mp4")))

    assert instagram.get_video_url("3000000000000000001") == "https://cdn.example/reel.mp4"
    assert client.asked == ["3000000000000000001"]


def test_video_url_of_a_photo_is_an_extraction_error(logged_in):
    logged_in(FakeInstagram(post(PHOTO, thumbnail_url="https://cdn.example/photo.jpg")))

    with pytest.raises(ExtractionError, match="not a video"):
        instagram.get_video_url("3000000000000000001")


class RefusingInstagram:
    def media_pk_from_url(self, url: str) -> str:
        return "3000000000000000001"

    def media_info(self, media_pk: str) -> InstagramMedia:
        raise MediaNotFound("Media not found")


def test_missing_post_is_an_extraction_error(logged_in):
    logged_in(RefusingInstagram())

    with pytest.raises(ExtractionError, match="Instagram refused"):
        extract("https://www.instagram.com/p/CtId5TwAxT_/")


def test_missing_video_is_an_extraction_error(logged_in):
    logged_in(RefusingInstagram())

    with pytest.raises(ExtractionError, match="Instagram refused"):
        instagram.get_video_url("3000000000000000001")


def test_unreadable_post_url_is_an_extraction_error(logged_in):
    class Incomplete(FakeInstagram):
        def media_pk_from_url(self, url: str) -> str:
            raise ValueError("not a post URL")

    logged_in(Incomplete(post(PHOTO)))

    with pytest.raises(ExtractionError, match="unexpected response"):
        extract("https://www.instagram.com/p/CtId5TwAxT_/")


def test_rejected_login_is_an_extraction_error(monkeypatch, tmp_path):
    class RejectingClient(FakeInstagrapiClient):
        def login(self, username, password):
            raise BadPassword("wrong password")

    monkeypatch.setattr("instagrapi.Client", RejectingClient)
    monkeypatch.setenv("INSTAGRAM_USERNAME", "someone")
    monkeypatch.setenv("INSTAGRAM_PASSWORD", "wrong")
    monkeypatch.setenv("INSTAGRAM_SESSION_FILE", str(tmp_path / "session.json"))
    instagram.default_client.cache_clear()

    with pytest.raises(ExtractionError, match="Instagram refused"):
        extract("https://www.instagram.com/p/CtId5TwAxT_/")


def test_missing_credentials_are_an_extraction_error(monkeypatch):
    monkeypatch.delenv("INSTAGRAM_USERNAME", raising=False)
    monkeypatch.delenv("INSTAGRAM_PASSWORD", raising=False)
    instagram.default_client.cache_clear()

    with pytest.raises(ExtractionError, match="INSTAGRAM_USERNAME"):
        extract("https://www.instagram.com/p/CtId5TwAxT_/")


class FakeInstagrapiClient:
    calls: ClassVar[list[tuple[str, str]]] = []

    def load_settings(self, path):
        self.calls.append(("load", path.read_text()))

    def login(self, username, password):
        self.calls.append(("login", f"{username}:{password}"))

    def dump_settings(self, path):
        self.calls.append(("dump", path.name))
        path.write_text("saved-session")


def test_login_reuses_the_saved_session(monkeypatch, tmp_path):
    monkeypatch.setattr("instagrapi.Client", FakeInstagrapiClient)
    monkeypatch.setenv("INSTAGRAM_USERNAME", "someone")
    monkeypatch.setenv("INSTAGRAM_PASSWORD", "secret")
    monkeypatch.setenv("INSTAGRAM_SESSION_FILE", str(tmp_path / "session.json"))
    FakeInstagrapiClient.calls = []
    instagram.default_client.cache_clear()

    try:
        instagram.default_client()
        instagram.default_client.cache_clear()
        instagram.default_client()
    finally:
        instagram.default_client.cache_clear()

    assert FakeInstagrapiClient.calls == [
        ("login", "someone:secret"),
        ("dump", "session.json"),
        ("load", "saved-session"),
        ("login", "someone:secret"),
        ("dump", "session.json"),
    ]
