from __future__ import annotations

from flask import Blueprint, render_template

from models import Sermon

sermons_bp = Blueprint('sermons', __name__)


def _resolve_video_embed(media_url: str | None) -> str | None:
    if not media_url:
        return None

    if 'youtube.com/watch' in media_url:
        video_id = media_url.split('v=')[-1]
        video_id = video_id.split('&')[0]
        return f'https://www.youtube.com/embed/{video_id}'

    if 'youtu.be/' in media_url:
        video_id = media_url.rstrip('/').split('/')[-1]
        return f'https://www.youtube.com/embed/{video_id}'

    if 'vimeo.com/' in media_url:
        video_id = media_url.rstrip('/').split('/')[-1]
        return f'https://player.vimeo.com/video/{video_id}'

    return media_url


def _detect_media_type(media_url: str | None) -> str | None:
    if not media_url:
        return None
    lowered = media_url.lower()
    if any(lowered.endswith(ext) for ext in ('.mp3', '.wav', '.aac', '.m4a')):
        return 'audio'
    if any(lowered.endswith(ext) for ext in ('.mp4', '.mov', '.mkv', '.webm')):
        return 'video'
    if 'youtu' in lowered or 'vimeo' in lowered:
        return 'video'
    return 'link'


def _build_media_context(sermon: Sermon) -> dict[str, str | None]:
    media_url = getattr(sermon, 'media_url', None)
    media_type = getattr(sermon, 'media_type', None)

    if not media_url:
        return {'type': None, 'embed_url': None, 'source_url': None}

    resolved_type = media_type.lower() if isinstance(media_type, str) else _detect_media_type(media_url)
    if resolved_type == 'video':
        embed = _resolve_video_embed(media_url)
        return {'type': 'video', 'embed_url': embed, 'source_url': media_url}
    if resolved_type == 'audio':
        return {'type': 'audio', 'embed_url': media_url, 'source_url': media_url}
    return {'type': 'link', 'embed_url': None, 'source_url': media_url}


@sermons_bp.route('/sermons')
def sermons():
    sermons_list = Sermon.query.order_by(Sermon.date.desc()).all()
    media_contexts = {sermon.id: _build_media_context(sermon) for sermon in sermons_list}
    return render_template('sermons.html', sermons=sermons_list, media_contexts=media_contexts)
