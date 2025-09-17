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
from app import db
from models import Sermon
from sqlalchemy.exc import SQLAlchemyError


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
    """Guess the media type from known host names or file extensions."""
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


def _build_media_context(sermon: Sermon) -> dict[str, str | None]:
    """Return template context for sermon media, inferring type when missing."""
    media_type = (sermon.media_type or '').strip().lower()
    media_url = (sermon.media_url or '').strip()

    if not media_url:
        return {"type": None, "embed_url": None, "source_url": None}

    detected_media_type = media_type or (_infer_media_type(media_url) or '')

    if detected_media_type == 'video':
        embed_url = _resolve_video_embed(media_url)

        return {
            "type": 'video',
            "embed_url": embed_url,
            "source_url": media_url,
        }

    if detected_media_type == 'audio':
        return {
            "type": 'audio',
            "embed_url": media_url,
            "source_url": media_url,
        }

    return {
        "type": 'link',
        "embed_url": None,
        "source_url": media_url,
    }


def _resolve_video_embed(media_url: str) -> str:
    """Convert known video providers into embeddable URLs when possible."""
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


@sermons_bp.route('/sermons')
def sermons():
    """Display all sermons with optional search parameters."""
    try:
        # Get search parameters
        title = request.args.get('title', '').strip()
        preacher = request.args.get('preacher', '').strip()
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        media_type = request.args.get('media_type', '').strip()

        # Build query
        query = Sermon.query

        # Apply filters
        if title:
            query = query.filter(Sermon.title.ilike(f'%{title}%'))
        if preacher:
            query = query.filter(Sermon.preacher.ilike(f'%{preacher}%'))
        if start_date:
            try:
                start_date_parsed = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Sermon.date >= start_date_parsed)
            except ValueError:
                current_app.logger.warning(
                    f"Invalid start_date format: {start_date}"
                )
        if end_date:
            try:
                end_date_parsed = datetime.strptime(end_date, '%Y-%m-%d')
                query = query.filter(Sermon.date <= end_date_parsed)
            except ValueError:
                current_app.logger.warning(
                    f"Invalid end_date format: {end_date}"
                )
        if media_type:
            query = query.filter(Sermon.media_type == media_type)

        # Execute query with sorting
        sermons_list = query.order_by(Sermon.date.desc()).all()
        return render_template('sermons.html', sermons=sermons_list)

    except Exception as exc:
        current_app.logger.error(f"Error in sermons route: {exc}")
        return render_template('sermons.html', sermons=[])


@sermons_bp.route('/sermons/search')
def search_sermons():
    """Advanced search endpoint for sermons."""
    return sermons()  # Reuse the main sermons route as it already handles search


@sermons_bp.route('/sermons/<int:sermon_id>')
def sermon_detail(sermon_id: int):
    """Render the detail page for a specific sermon with related content."""
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
            related_sermons=related_sermons,
            media_context=media_context,
        )

    except SQLAlchemyError as exc:
        current_app.logger.error(
            f"Database error while fetching sermon {sermon_id}: {exc}"
        )
        flash('Unable to load the sermon right now. Please try again later.', 'danger')
        return redirect(url_for('sermons.sermons'))
    except Exception as exc:
        current_app.logger.error(
            f"Unexpected error in sermon_detail route: {exc}"
        )
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return redirect(url_for('sermons.sermons'))
