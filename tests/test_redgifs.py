import pytest
import responses
from conftest import load
from responses import matchers

from media_url_extractor import ExtractionError, Media, extract
from media_url_extractor.platforms.redgifs import API


def serve(http: responses.RequestsMock, gif: dict | None = None, status: int = 200) -> None:
    http.get(f"{API}/auth/temporary", json=load("redgifs_auth.json"))
    http.get(
        f"{API}/gifs/selfishawareladybug",
        json=gif or load("redgifs_gif.json"),
        status=status,
        match=[matchers.header_matcher({"authorization": "Bearer recorded-temporary-token"})],
    )


def test_watch_url_returns_the_hd_file(http):
    serve(http)

    media = extract("https://www.redgifs.com/watch/SelfishAwareLadybug")

    assert media == [Media("video", "https://media.redgifs.com/SelfishAwareLadybug.mp4")]


def test_sd_file_is_used_when_there_is_no_hd_file(http):
    gif = load("redgifs_gif.json")
    del gif["gif"]["urls"]["hd"]
    serve(http, gif)

    media = extract("https://www.redgifs.com/watch/selfishawareladybug")

    assert media == [Media("video", "https://media.redgifs.com/SelfishAwareLadybug-mobile.mp4")]


def test_gif_without_a_video_file_is_an_extraction_error(http):
    gif = {"gif": {"urls": {"poster": "https://media.redgifs.com/x-poster.jpg"}}}
    serve(http, gif)

    with pytest.raises(ExtractionError, match="no video file"):
        extract("https://www.redgifs.com/watch/selfishawareladybug")


def test_response_without_a_gif_is_an_extraction_error(http):
    serve(http, {"unexpected": True})

    with pytest.raises(ExtractionError, match="unexpected response"):
        extract("https://www.redgifs.com/watch/selfishawareladybug")


def test_auth_without_a_token_is_an_extraction_error(http):
    http.get(f"{API}/auth/temporary", json={})

    with pytest.raises(ExtractionError, match="unexpected response"):
        extract("https://www.redgifs.com/watch/selfishawareladybug")


def test_url_without_a_gif_id_is_rejected():
    with pytest.raises(ValueError, match="watch URL"):
        extract("https://www.redgifs.com/")
