from datetime import datetime
from urllib.parse import parse_qs, urlparse

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import Sermon


sermons_bp = Blueprint('sermons', __name__)

VIDEO_HOSTS = (
    'youtube.com',
    'youtu.be',
    'vimeo.com',
    'player.vimeo.com',
)

VIDEO_EXTENSIONS = (
    '.mp4',
    '.mov',
    '.m4v',
    '.webm',
)

AUDIO_EXTENSIONS = (
    '.mp3',
    '.wav',
    '.aac',
    '.m4a',
    '.ogg',
)


def _infer_media_type(media_url: str) -> str | None:
    parsed = urlparse(media_url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    if any(domain in host for domain in VIDEO_HOSTS):
        return 'video'
    if any(path.endswith(ext) for ext in VIDEO_EXTENSIONS):
        return 'video'
    if any(path.endswith(ext) for ext in AUDIO_EXTENSIONS):
        return 'audio'
    return None


def _resolve_video_embed(media_url: str) -> str:
    parsed = urlparse(media_url)
    host = parsed.netloc.lower()

    if 'youtube.com' in host:
        if parsed.path.startswith('/embed/'):
            return media_url
        if parsed.path == '/watch':
            video_id = parse_qs(parsed.query).get('v', [''])[0]
            if video_id:
                return f'https://www.youtube.com/embed/{video_id}'
    if 'youtu.be' in host:
        video_id = parsed.path.lstrip('/')
        if video_id:
            return f'https://www.youtube.com/embed/{video_id}'
    if 'vimeo.com' in host:
        if 'player.vimeo.com' in host:
            return media_url
        video_id = parsed.path.strip('/').split('/')[-1]
        if video_id:
            return f'https://player.vimeo.com/video/{video_id}'

    return media_url


def _build_media_context(sermon: Sermon) -> dict[str, str | None]:
    media_url = (sermon.media_url or '').strip()
    if not media_url:
        return {'type': None, 'embed_url': None, 'source_url': None}

    explicit_type = (sermon.media_type or '').strip().lower()
    detected_type = explicit_type or (_infer_media_type(media_url) or '')

    if detected_type == 'video':
        return {
            'type': 'video',
            'embed_url': _resolve_video_embed(media_url),
            'source_url': media_url,
        }

    if detected_type == 'audio':
        return {
            'type': 'audio',
            'embed_url': media_url,
            'source_url': media_url,
        }

    return {'type': 'link', 'embed_url': None, 'source_url': media_url}


@sermons_bp.route('/sermons')
def sermons():
    try:
        title = request.args.get('title', '').strip()
        preacher = request.args.get('preacher', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        media_type = request.args.get('media_type', '').strip()

        query = Sermon.query

        if title:
            query = query.filter(Sermon.title.ilike(f'%{title}%'))
        if preacher:
            query = query.filter(Sermon.preacher.ilike(f'%{preacher}%'))
        if start_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Sermon.date >= start)
            except ValueError:
                current_app.logger.warning('Invalid start_date format: %s', start_date)
        if end_date:
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d')
                query = query.filter(Sermon.date <= end)
            except ValueError:
                current_app.logger.warning('Invalid end_date format: %s', end_date)
        if media_type:
            query = query.filter(Sermon.media_type == media_type)

        sermons_list = query.order_by(Sermon.date.desc()).all()
        return render_template('sermons.html', sermons=sermons_list)
    except SQLAlchemyError as exc:
        current_app.logger.error('Database error while fetching sermons: %s', exc)
        flash('Unable to load sermons at this time.', 'danger')
        return render_template('sermons.html', sermons=[])
    except Exception as exc:  # noqa: BLE001
        current_app.logger.error('Unexpected error in sermons route: %s', exc)
        return render_template('sermons.html', sermons=[])


@sermons_bp.route('/sermons/search')
def search_sermons():
    return sermons()


@sermons_bp.route('/sermons/<int:sermon_id>')
def sermon_detail(sermon_id: int):
    try:
        sermon = db.session.get(Sermon, sermon_id)
        if not sermon:
            flash('Sermon not found.', 'warning')
            return redirect(url_for('sermons.sermons'))

        related_sermons = (
            Sermon.query
            .filter(Sermon.id != sermon_id)
            .order_by(Sermon.date.desc())
            .limit(3)
            .all()
        )

        media_context = _build_media_context(sermon)

        return render_template(
            'sermon_detail.html',
            sermon=sermon,
            media_context=media_context,
            related_sermons=related_sermons,
        )
    except SQLAlchemyError as exc:
        current_app.logger.error('Database error loading sermon %s: %s', sermon_id, exc)
        flash('Unable to load the sermon right now.', 'danger')
        return redirect(url_for('sermons.sermons'))
    except Exception as exc:  # noqa: BLE001
        current_app.logger.error('Unexpected error in sermon_detail: %s', exc)
        return redirect(url_for('sermons.sermons'))


__all__ = ['_build_media_context', '_resolve_video_embed', 'sermons_bp']
