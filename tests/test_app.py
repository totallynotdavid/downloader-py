import pytest
from conftest import load
from flask.testing import FlaskClient
from instagrapi.exceptions import MediaNotFound

from media_url_extractor.app import create_app
from media_url_extractor.platforms import instagram
from media_url_extractor.platforms.redgifs import API
from media_url_extractor.platforms.twitter import ENDPOINT


@pytest.fixture
def client() -> FlaskClient:
    return create_app().test_client()


def test_get_media_url_returns_typed_media(client, http):
    http.get(ENDPOINT, json=load("twitter_photo.json"))

    response = client.post(
        "/api/get_media_url",
        json={"url": "https://twitter.com/berthofmanecon/status/1643051849682157569"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "media": [
            {
                "type": "image",
                "url": load("twitter_photo.json")["mediaDetails"][0]["media_url_https"],
            }
        ]
    }


@pytest.mark.parametrize("body", [None, {}, {"url": ""}, {"url": 7}, [1]])
def test_missing_url_is_a_client_error(client, body):
    response = client.post("/api/get_media_url", json=body)

    assert response.status_code == 400
    assert response.get_json() == {"error": "No URL provided"}


def test_unsupported_platform_is_a_client_error(client):
    response = client.post("/api/get_media_url", json={"url": "https://example.com/post/1"})

    assert response.status_code == 400
    assert "Unsupported platform" in response.get_json()["error"]


def test_failed_extraction_is_a_bad_gateway(client, http):
    http.get(ENDPOINT, json=load("twitter_tombstone.json"))

    response = client.post(
        "/api/get_media_url",
        json={"url": "https://twitter.com/trbrtc/status/1646592080293122067"},
    )

    assert response.status_code == 502
    assert "deleted" in response.get_json()["error"]


def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "healthy"}


def test_redgifs_stream_proxies_the_hd_file(client, http):
    http.get(f"{API}/auth/temporary", json=load("redgifs_auth.json"))
    http.get(f"{API}/gifs/selfishawareladybug", json=load("redgifs_gif.json"))
    http.get(
        "https://media.redgifs.com/SelfishAwareLadybug.mp4",
        body=b"mp4-bytes",
        content_type="video/mp4",
    )

    response = client.get("/api/redgifs/selfishawareladybug")

    assert response.status_code == 200
    assert response.content_type == "video/mp4"
    assert response.data == b"mp4-bytes"


def test_redgifs_stream_reports_a_missing_gif(client, http):
    http.get(f"{API}/auth/temporary", json=load("redgifs_auth.json"))
    http.get(f"{API}/gifs/missing", status=404, json={})

    assert client.get("/api/redgifs/missing").status_code == 502


def test_instagram_stream_refusal_is_a_bad_gateway(client, monkeypatch):
    class Refusing:
        def media_pk_from_url(self, url):
            return "1"

        def media_info(self, media_pk):
            raise MediaNotFound("Media not found")

    monkeypatch.setattr(instagram, "default_client", lambda: Refusing())

    assert client.get("/api/instagram/3000000000000000001").status_code == 502


def test_instagram_stream_proxies_the_video(client, http, monkeypatch):
    monkeypatch.setattr(instagram, "get_video_url", lambda media_id: "https://cdn.example/reel.mp4")
    http.get("https://cdn.example/reel.mp4", body=b"reel-bytes", content_type="video/mp4")

    response = client.get("/api/instagram/3000000000000000001")

    assert response.status_code == 200
    assert response.data == b"reel-bytes"


@pytest.mark.parametrize("path", ["/api/instagram/not-a-number", "/api/redgifs/a-b"])
def test_stream_rejects_malformed_ids(client, path):
    assert client.get(path).status_code == 400


def test_requests_are_rate_limited(client, http):
    http.get(ENDPOINT, json=load("twitter_photo.json"))
    url = {"url": "https://twitter.com/a/status/1643051849682157569"}

    statuses = [client.post("/api/get_media_url", json=url).status_code for _ in range(51)]

    assert statuses[:50] == [200] * 50
    assert statuses[50] == 429
    assert client.get("/api/health").status_code == 200
