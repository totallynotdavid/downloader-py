import pytest
import responses
from conftest import load
from responses import matchers

from media_url_extractor import ExtractionError, Media, extract

POST = "https://www.reddit.com/r/example/comments/abc123/a_title"


def serve(http: responses.RequestsMock, body: object, status: int = 200) -> None:
    http.get(
        f"{POST}.json",
        json=body,
        status=status,
        match=[
            matchers.query_param_matcher({"raw_json": "1"}),
            matchers.header_matcher({"User-Agent": "media-url-extractor/1.0"}),
        ],
    )


def test_image_post_returns_the_image(http):
    serve(http, load("reddit_image.json"))

    assert extract(f"{POST}/") == [Media("image", "https://i.redd.it/example.png")]


def test_hosted_video_returns_the_fallback_file(http):
    serve(http, load("reddit_video.json"))

    assert extract(POST) == [
        Media("video", "https://v.redd.it/example/DASH_720.mp4?source=fallback")
    ]


def test_gallery_keeps_the_authors_order_and_marks_animations_as_video(http):
    serve(http, load("reddit_gallery.json"))

    assert extract(POST) == [
        Media("video", "https://preview.redd.it/bbb.gif?format=mp4&s=def"),
        Media("image", "https://i.redd.it/aaa.jpg?width=1080&format=pjpg&s=abc"),
        Media("image", "https://i.redd.it/ccc.png"),
    ]


def test_link_post_returns_its_preview_image(http):
    serve(http, load("reddit_link.json"))

    assert extract(POST) == [
        Media("image", "https://external-preview.redd.it/example.jpg?auto=webp&s=abc")
    ]


def test_crosspost_returns_the_original_posts_media(http):
    listing = load("reddit_image.json")
    listing[0]["data"]["children"][0]["data"] = {
        "crosspost_parent_list": [load("reddit_video.json")[0]["data"]["children"][0]["data"]]
    }
    serve(http, listing)

    assert [item.type for item in extract(POST)] == ["video"]


def test_text_post_returns_nothing(http):
    listing = load("reddit_image.json")
    listing[0]["data"]["children"][0]["data"] = {"title": "just words", "selftext": "hello"}
    serve(http, listing)

    assert extract(POST) == []


@pytest.mark.parametrize("status", [403, 429])
def test_refusal_is_an_extraction_error(http, status):
    serve(http, "<html>Blocked</html>", status=status)

    with pytest.raises(ExtractionError, match=f"HTTP {status}"):
        extract(POST)


def test_response_without_a_post_is_an_extraction_error(http):
    serve(http, [{"data": {"children": []}}])

    with pytest.raises(ExtractionError, match="unexpected response"):
        extract(POST)


def test_hosted_video_without_a_file_is_an_extraction_error(http):
    post = load("reddit_video.json")
    del post[0]["data"]["children"][0]["data"]["media"]["reddit_video"]
    serve(http, post)

    with pytest.raises(ExtractionError, match="unexpected response"):
        extract(POST)
