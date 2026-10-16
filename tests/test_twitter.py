import pytest
import responses
from conftest import load
from responses import matchers

from media_url_extractor import ExtractionError, Media, extract
from media_url_extractor.platforms.twitter import ENDPOINT


def serve(http: responses.RequestsMock, tweet_id: str, body: dict, status: int = 200) -> None:
    http.get(
        ENDPOINT,
        json=body,
        status=status,
        match=[matchers.query_param_matcher({"id": tweet_id, "lang": "en", "token": "1"})],
    )


def test_video_returns_the_highest_bitrate_mp4(http):
    serve(http, "1642935433276555265", load("twitter_video.json"))

    media = extract("https://twitter.com/vocodehq/status/1642935433276555265")

    assert len(media) == 1
    assert media[0].type == "video"
    assert media[0].url.startswith("https://video.twimg.com/")
    assert "/1280x720/" in media[0].url
    assert ".mp4" in media[0].url


def test_photo_returns_the_image(http):
    tweet = load("twitter_photo.json")
    serve(http, "1643051849682157569", tweet)

    media = extract("https://twitter.com/berthofmanecon/status/1643051849682157569")

    assert media == [Media("image", tweet["mediaDetails"][0]["media_url_https"])]


def test_link_card_returns_its_original_image(http):
    card = load("twitter_card.json")
    serve(http, "1665737367880187906", card)

    media = extract("https://twitter.com/ATabarrok/status/1665737367880187906")

    expected = card["card"]["binding_values"]["thumbnail_image_original"]["image_value"]["url"]
    assert media == [Media("image", expected)]


def test_quoted_post_media_follows_the_post_media(http):
    photo = load("twitter_photo.json")
    photo["quoted_tweet"] = load("twitter_video.json")
    serve(http, "1643051849682157569", photo)

    media = extract("https://x.com/berthofmanecon/status/1643051849682157569")

    assert [item.type for item in media] == ["image", "video"]


def test_post_without_media_returns_nothing(http):
    tweet = load("twitter_photo.json")
    tweet["mediaDetails"] = []
    serve(http, "1643051849682157569", tweet)

    assert extract("https://twitter.com/a/status/1643051849682157569") == []


@pytest.mark.parametrize(
    "url",
    [
        "https://x.com/vocodehq/status/1642935433276555265?s=20",
        "https://mobile.twitter.com/vocodehq/status/1642935433276555265",
        "https://twitter.com/i/web/status/1642935433276555265",
    ],
)
def test_url_forms_resolve_to_the_same_post(http, url):
    serve(http, "1642935433276555265", load("twitter_video.json"))

    assert len(extract(url)) == 1


def test_deleted_post_is_an_extraction_error(http):
    serve(http, "1646592080293122067", load("twitter_tombstone.json"))

    with pytest.raises(ExtractionError, match="deleted"):
        extract("https://twitter.com/trbrtc/status/1646592080293122067")


def test_empty_response_is_an_extraction_error(http):
    serve(http, "1642935433276555265", {})

    with pytest.raises(ExtractionError):
        extract("https://twitter.com/vocodehq/status/1642935433276555265")


def test_video_without_an_mp4_file_is_an_extraction_error(http):
    tweet = load("twitter_video.json")
    for detail in tweet["mediaDetails"]:
        detail["video_info"]["variants"] = [
            variant
            for variant in detail["video_info"]["variants"]
            if variant["content_type"] != "video/mp4"
        ]
    serve(http, "1642935433276555265", tweet)

    with pytest.raises(ExtractionError, match="no MP4"):
        extract("https://twitter.com/vocodehq/status/1642935433276555265")


def test_media_without_its_fields_is_an_extraction_error(http):
    serve(http, "1642935433276555265", {"mediaDetails": [{"type": "photo"}]})

    with pytest.raises(ExtractionError, match="unexpected response"):
        extract("https://twitter.com/vocodehq/status/1642935433276555265")


def test_http_failure_is_an_extraction_error(http):
    serve(http, "1642935433276555265", {}, status=503)

    with pytest.raises(ExtractionError, match="twitter request failed"):
        extract("https://twitter.com/vocodehq/status/1642935433276555265")


def test_profile_url_is_rejected():
    with pytest.raises(ValueError, match="status URL"):
        extract("https://twitter.com/vocodehq")
