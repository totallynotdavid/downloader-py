import logging
import re
from collections.abc import Callable, Iterator
from dataclasses import asdict

import requests
from flask import Flask, Response, jsonify, request, stream_with_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from media_url_extractor.extractors import extract
from media_url_extractor.media import ExtractionError
from media_url_extractor.platforms import instagram, redgifs

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 64 * 1024
_INSTAGRAM_MEDIA_ID = re.compile(r"\d+(_\d+)?")
_REDGIFS_ID = re.compile(r"[A-Za-z0-9]+")


def create_app() -> Flask:
    app = Flask(__name__)
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["1000/day", "100/hour", "50/minute"],
        storage_uri="memory://",
    )

    @app.post("/api/get_media_url")
    def get_media_url() -> tuple[Response, int] | Response:
        body = request.get_json(silent=True)
        url = body.get("url") if isinstance(body, dict) else None
        if not isinstance(url, str) or not url:
            return jsonify(error="No URL provided"), 400
        try:
            media = extract(url)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except ExtractionError as exc:
            logger.warning("Could not extract %s: %s", url, exc)
            return jsonify(error=str(exc)), 502
        return jsonify(media=[asdict(item) for item in media])

    @app.get("/api/health")
    @limiter.exempt
    def health() -> Response:
        return jsonify(status="healthy")

    @app.get("/api/instagram/<media_id>")
    def stream_instagram(media_id: str) -> Response | tuple[Response, int]:
        if not _INSTAGRAM_MEDIA_ID.fullmatch(media_id):
            return jsonify(error="Invalid media id"), 400
        return _stream(lambda: instagram.get_video_url(media_id))

    @app.get("/api/redgifs/<gif_id>")
    def stream_redgifs(gif_id: str) -> Response | tuple[Response, int]:
        if not _REDGIFS_ID.fullmatch(gif_id):
            return jsonify(error="Invalid gif id"), 400
        return _stream(lambda: redgifs.get_video_url(gif_id))

    return app


def _stream(resolve_url: Callable[[], str]) -> Response | tuple[Response, int]:
    try:
        upstream = requests.get(resolve_url(), stream=True, timeout=10)
        upstream.raise_for_status()
    except (ExtractionError, requests.RequestException) as exc:
        logger.warning("Could not stream: %s", exc)
        return jsonify(error=str(exc)), 502

    def chunks() -> Iterator[bytes]:
        with upstream:
            yield from upstream.iter_content(chunk_size=_CHUNK_SIZE)

    return Response(
        stream_with_context(chunks()),
        content_type=upstream.headers.get("content-type", "application/octet-stream"),
    )


def main() -> None:
    create_app().run()
