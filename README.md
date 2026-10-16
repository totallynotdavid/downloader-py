# Media URL Extractor

An HTTP API and Python library that turns the URL of a social media post into
direct links to its images and videos. It reads Twitter/X, Instagram, Reddit,
RedGifs and Imgur. It returns links; it does not download files.

## Install

You need [uv](https://docs.astral.sh/uv/). `mise install` installs the uv
version pinned in `mise.toml` and the Python in `.python-version`, which uv
reads too.

```sh
uv sync
```

## Use

Start the API on http://127.0.0.1:5000:

```sh
uv run media-url-extractor
```

Post a URL:

```sh
curl -X POST localhost:5000/api/get_media_url \
  -H 'content-type: application/json' \
  -d '{"url": "https://x.com/vocodehq/status/1642935433276555265"}'
```

```json
{
  "media": [
    {
      "type": "video",
      "url": "https://video.twimg.com/ext_tw_video/1642935259934363654/pu/vid/1280x720/kR-GGd3QBhceS6Bi.mp4?tag=12"
    }
  ]
}
```

`type` is `image` or `video`. A post without media returns an empty list.

| Status | Meaning                                                                    |
| ------ | -------------------------------------------------------------------------- |
| 400    | No `url`, a platform that is not supported, or a malformed post URL        |
| 429    | More than 50 requests a minute, 100 an hour or 1000 a day from one address |
| 502    | The platform refused the request or the post could not be read             |

Limits are counted in memory, per process. The body of an error is
`{"error": "..."}`.

Other routes:

- `GET /api/health` returns `{"status": "healthy"}` and has no rate limit.
- `GET /api/redgifs/<gif id>` streams the HD file of a RedGifs gif.
- `GET /api/instagram/<media id>` streams the video of an Instagram post.

The same extraction is available in Python:

```python
from media_url_extractor import extract

extract("https://i.imgur.com/A61SaA1.gifv")
```

`extract` raises `ValueError` for an unsupported or malformed URL and
`ExtractionError` when the platform gives no media.

## Platforms

| Platform  | URLs                                  | Returns                                                                   |
| --------- | ------------------------------------- | ------------------------------------------------------------------------- |
| Twitter/X | `twitter.com` and `x.com` status URLs | Photos, the best MP4 of videos and GIFs, link card images, quoted posts   |
| Instagram | Posts, reels and albums               | Images and videos                                                         |
| Reddit    | Post URLs on `reddit.com`             | Images, hosted videos, gallery items in the author's order, link previews |
| RedGifs   | `redgifs.com/watch/<id>`              | The HD MP4, or the SD MP4 when there is no HD file                        |
| Imgur     | `i.imgur.com` files and post pages    | Images and MP4 files of animations                                        |

- Reddit refuses requests from some server addresses with HTTP 403. The API then
  answers 502.
- Imgur post pages resolve through [yt-dlp](https://github.com/yt-dlp/yt-dlp),
  which reads only videos and animations from them.

### Instagram login

Instagram shows anonymous visitors a login wall, so the API needs an account.
Set these variables before you start it, for example in a `.env` file:

| Variable                 | Default                  |                                 |
| ------------------------ | ------------------------ | ------------------------------- |
| `INSTAGRAM_USERNAME`     |                          | Required                        |
| `INSTAGRAM_PASSWORD`     |                          | Required                        |
| `INSTAGRAM_SESSION_FILE` | `instagram_session.json` | Where the login session is kept |

```sh
uv run --env-file .env media-url-extractor
```

Without credentials, Instagram URLs answer 502 and the other platforms work.

## Develop

```sh
mise run check
```

`check` runs `lint` (`ruff check` and `ruff format --check`), `typecheck`
(`mypy`) and `test` (`pytest`). Each also runs alone, for example
`mise run test`.

The tests replay recorded responses from `tests/fixtures`, so they need no
network or account. CI runs `mise run check`.
