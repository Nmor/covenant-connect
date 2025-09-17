from types import SimpleNamespace

import pytest

from routes.sermons import _build_media_context, _resolve_video_embed


def _sermon(media_url: str | None, media_type: str | None = None):
    return SimpleNamespace(media_url=media_url, media_type=media_type)


@pytest.mark.parametrize(
    ("input_url", "expected"),
    [
        (
            "https://www.youtube.com/watch?v=abc123",
            "https://www.youtube.com/embed/abc123",
        ),
        ("https://youtu.be/XYZ789", "https://www.youtube.com/embed/XYZ789"),
        ("https://vimeo.com/4567", "https://player.vimeo.com/video/4567"),
        ("https://example.com/video.mp4", "https://example.com/video.mp4"),
    ],
)
def test_resolve_video_embed_variants(input_url, expected):
    assert _resolve_video_embed(input_url) == expected


def test_media_context_detects_video_without_type():
    context = _build_media_context(
        _sermon("https://www.youtube.com/watch?v=abc123", None)
    )

    assert context["type"] == "video"
    assert context["embed_url"] == "https://www.youtube.com/embed/abc123"
    assert context["source_url"] == "https://www.youtube.com/watch?v=abc123"


def test_media_context_respects_explicit_video_type():
    context = _build_media_context(
        _sermon("https://vimeo.com/987", "Video")
    )

    assert context["type"] == "video"
    assert context["embed_url"] == "https://player.vimeo.com/video/987"


def test_media_context_detects_audio_extension():
    context = _build_media_context(_sermon("https://example.com/audio.MP3", None))

    assert context == {
        "type": "audio",
        "embed_url": "https://example.com/audio.MP3",
        "source_url": "https://example.com/audio.MP3",
    }


def test_media_context_returns_link_when_unknown():
    context = _build_media_context(_sermon("https://example.com/resource", None))

    assert context == {
        "type": "link",
        "embed_url": None,
        "source_url": "https://example.com/resource",
    }


def test_media_context_handles_missing_url():
    context = _build_media_context(_sermon(None, "video"))

    assert context == {"type": None, "embed_url": None, "source_url": None}
