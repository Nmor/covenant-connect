"""Routes and helpers for sermon media handling."""
from __future__ import annotations

import re
from typing import Any, Dict

from flask import Blueprint, render_template
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import Sermon


sermons_bp = Blueprint('sermons', __name__)


_YOUTUBE_RE = re.compile(r'(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/))([\w-]+)', re.I)
_VIMEO_RE = re.compile(r'vimeo\.com/(\d+)', re.I)
_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.aac', '.m4a', '.ogg'}


def _resolve_video_embed(url: str | None) -> str | None:
    """Return an embeddable URL for a known video provider."""

    if not url:
        return None

    match = _YOUTUBE_RE.search(url)
    if match:
        return f'https://www.youtube.com/embed/{match.group(1)}'

    match = _VIMEO_RE.search(url)
    if match:
        return f'https://player.vimeo.com/video/{match.group(1)}'

    return url


def _detect_media_type(media_url: str | None, explicit: str | None) -> str | None:
    if explicit:
        normalized = explicit.strip().lower()
        if normalized in {'video', 'audio'}:
            return normalized

    if not media_url:
        return None

    lowered = media_url.lower()
    if lowered.endswith(tuple(_AUDIO_EXTENSIONS)):
        return 'audio'

    if _YOUTUBE_RE.search(lowered) or _VIMEO_RE.search(lowered) or lowered.endswith(('.mp4', '.mov', '.webm')):
        return 'video'

    return 'link'


def _build_media_context(sermon: Any) -> Dict[str, Any]:
    media_url = getattr(sermon, 'media_url', None)
    explicit_type = getattr(sermon, 'media_type', None)

    if not media_url:
        return {'type': None, 'embed_url': None, 'source_url': None}

    media_type = _detect_media_type(media_url, explicit_type)

    if media_type == 'video':
        embed_url = _resolve_video_embed(media_url)
    elif media_type == 'audio':
        embed_url = media_url
    elif media_type == 'link':
        embed_url = None
    else:
        return {'type': None, 'embed_url': None, 'source_url': media_url}

    return {
        'type': media_type,
        'embed_url': embed_url,
        'source_url': media_url,
    }


@sermons_bp.route('/sermons')
def sermons() -> str:
    try:
        sermons_list = Sermon.query.order_by(Sermon.date.desc()).all()
    except SQLAlchemyError as exc:  # pragma: no cover - defensive logging
        db.session.rollback()
        sermons_list = []
        sermons_bp.logger.error('Error loading sermons: {0}'.format(exc))

    entries = [
        {'sermon': sermon, 'media': _build_media_context(sermon)}
        for sermon in sermons_list
    ]
    return render_template('sermons.html', sermons=entries)


@sermons_bp.route('/sermons/<int:sermon_id>')
def sermon_detail(sermon_id: int) -> str:
    sermon = Sermon.query.get_or_404(sermon_id)
    context = _build_media_context(sermon)
    return render_template('sermon_detail.html', sermon=sermon, media=context)


__all__ = ['sermons_bp', '_resolve_video_embed', '_build_media_context']
