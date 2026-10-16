import pytest

from media_url_extractor import platform_of


@pytest.mark.parametrize(
    ("url", "platform"),
    [
        ("https://twitter.com/a/status/1", "twitter"),
        ("https://x.com/a/status/1", "twitter"),
        ("https://www.instagram.com/p/abc/", "instagram"),
        ("https://old.reddit.com/r/a/comments/1/b/", "reddit"),
        ("https://www.redgifs.com/watch/abc", "redgifs"),
        ("https://i.imgur.com/abc.gifv", "imgur"),
        ("https://example.com/twitter.com/a/status/1", None),
        ("https://nottwitter.com/a/status/1", None),
        ("not a url", None),
    ],
)
def test_platform_is_read_from_the_host(url, platform):
    assert platform_of(url) == platform
