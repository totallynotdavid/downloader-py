import pytest
from conftest import FIXTURES, load

from media_url_extractor import ExtractionError, Media, extract

API = "https://api.imgur.com/post/v1/media/A61SaA1"


@pytest.mark.parametrize("name", ["A61SaA1.gifv", "A61SaA1.mp4"])
def test_direct_video_link_needs_no_request(http, name):
    assert extract(f"https://i.imgur.com/{name}") == [
        Media("video", "https://i.imgur.com/A61SaA1.mp4")
    ]


def test_direct_image_link_is_returned_as_it_is(http):
    assert extract("https://i.imgur.com/Fi5VmFN.jpg") == [
        Media("image", "https://i.imgur.com/Fi5VmFN.jpg")
    ]


def test_post_page_of_an_animation_resolves_to_its_mp4(http):
    http.get(API, json=load("imgur_media_api.json"))
    http.get(
        "https://i.imgur.com/A61SaA1.gifv",
        status=302,
        headers={"Location": "https://imgur.com/A61SaA1"},
    )
    http.get(
        "https://imgur.com/A61SaA1",
        body=(FIXTURES / "imgur_page.html").read_text(),
        content_type="text/html",
    )

    assert extract("https://imgur.com/A61SaA1") == [
        Media("video", "https://i.imgur.com/A61SaA1.mp4")
    ]


def test_post_page_of_a_still_image_is_an_extraction_error(http):
    still = load("imgur_media_api.json")
    still["media"][0]["metadata"]["is_animated"] = False
    http.get(API, json=still)

    with pytest.raises(ExtractionError, match="not a video"):
        extract("https://imgur.com/A61SaA1")


def test_unknown_post_is_an_extraction_error(http):
    http.get(API, json={"errors": []}, status=404)

    with pytest.raises(ExtractionError):
        extract("https://imgur.com/A61SaA1")
