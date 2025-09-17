from datetime import datetime
 codex/add-generic-workflow-runner-and-ui
from typing import Dict, Optional
 codex/expand-event-model-for-recurrence-and-tags
     main
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
 codex/add-generic-workflow-runner-and-ui
from tasks import trigger_automation
from typing import Optional
from urllib.parse import parse_qs, urlparse

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
     main
from app import db
from models import CareInteraction, Member, Sermon

sermons_bp = Blueprint('sermons', __name__)

 codex/add-generic-workflow-runner-and-ui

 main
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


 codex/add-generic-workflow-runner-and-ui
def _infer_media_type(media_url: str) -> Optional[str]:
    """Guess the media type from known host names or file extensions."""
 codex/expand-event-model-for-recurrence-and-tags
def _infer_media_type(media_url: str) -> str | None:
def _infer_media_type(media_url: str) -> Optional[str]:
     main
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
 codex/add-generic-workflow-runner-and-ui
    """Convert known video providers into embeddable URLs when possible."""
     main
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


 codex/add-generic-workflow-runner-and-ui
def _build_media_context(sermon: Sermon) -> Dict[str, Optional[str]]:
    """Return template-friendly context describing how to render sermon media."""
 codex/expand-event-model-for-recurrence-and-tags
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
def _build_media_context(sermon: Sermon) -> dict[str, Optional[str]]:
     main
    media_type = (sermon.media_type or '').strip().lower()
    media_url = (sermon.media_url or '').strip()

    if not media_url:
        return {"type": None, "embed_url": None, "source_url": None}

    detected_media_type = media_type or (_infer_media_type(media_url) or '')

    if detected_media_type == 'video':
        embed_url = _resolve_video_embed(media_url)
        return {
            'type': 'video',
            'embed_url': embed_url,
            'source_url': media_url,
        }

    if detected_media_type == 'audio':
 codex/add-generic-workflow-runner-and-ui
     main
        return {
            'type': 'audio',
            'embed_url': media_url,
            'source_url': media_url,
        }

 codex/expand-event-model-for-recurrence-and-tags
    return {'type': 'link', 'embed_url': None, 'source_url': media_url}
    return {
        'type': 'link',
        'embed_url': None,
        'source_url': media_url,
    }


 codex/add-generic-workflow-runner-and-ui
def _find_member_by_email(email: Optional[str]) -> Optional[Member]:
    if not email:
        return None
    normalized = email.strip().lower()
    if not normalized:
        return None
    return Member.query.filter(func.lower(Member.email) == normalized).first()


def _resolve_member_for_engagement() -> Optional[Member]:
    email_from_request = request.args.get('email')
    member = _find_member_by_email(email_from_request)
    if member:
        return member

    if current_user.is_authenticated:
        profile = getattr(current_user, 'member_profile', None)
        if profile:
            return profile
        return _find_member_by_email(getattr(current_user, 'email', None))

    return None


def _log_sermon_engagement(member: Member, sermon: Sermon) -> bool:
    today = datetime.utcnow().date()
    start_of_day = datetime(today.year, today.month, today.day)

    recent_interactions = (
        CareInteraction.query.filter(
            CareInteraction.member_id == member.id,
            CareInteraction.interaction_type == 'sermon_engagement',
            CareInteraction.interaction_date >= start_of_day,
        )
        .order_by(CareInteraction.interaction_date.desc())
        .all()
    )

    for interaction in recent_interactions:
        metadata = interaction.metadata or {}
        if metadata.get('sermon_id') == sermon.id:
            return False

    milestone_entry = (member.milestones or {}).get('sermon_engagement')
    if not milestone_entry or not milestone_entry.get('completed'):
        member.record_milestone('sermon_engagement', 'Engaged with a Sermon', completed=True)

    interaction_time = datetime.utcnow()
    interaction = CareInteraction(
        member=member,
        interaction_type='sermon_engagement',
        interaction_date=interaction_time,
        notes=f'Engaged with sermon "{sermon.title}"',
        follow_up_required=False,
        source='sermon_detail',
        metadata={'sermon_id': sermon.id, 'sermon_title': sermon.title},
    )

    member.last_interaction_at = interaction_time
    if not member.assimilation_stage:
        member.assimilation_stage = 'Engaged Online'

    db.session.add(interaction)
    return True
     main


     main
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
 codex/add-generic-workflow-runner-and-ui
                current_app.logger.warning(
                    "Invalid start_date format received: %s",
                    start_date,
                )
 codex/expand-event-model-for-recurrence-and-tags
                current_app.logger.warning('Invalid start_date format: %s', start_date)
                current_app.logger.warning(f"Invalid start_date format: {start_date}")
     main
        if end_date:
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d')
                query = query.filter(Sermon.date <= end)
            except ValueError:
 codex/add-generic-workflow-runner-and-ui
                current_app.logger.warning(
                    "Invalid end_date format received: %s",
                    end_date,
                )
 codex/expand-event-model-for-recurrence-and-tags
                current_app.logger.warning('Invalid end_date format: %s', end_date)
                current_app.logger.warning(f"Invalid end_date format: {end_date}")
     main
        if media_type:
            query = query.filter(Sermon.media_type == media_type)

        sermons_list = query.order_by(Sermon.date.desc()).all()
        return render_template('sermons.html', sermons=sermons_list)
 codex/add-generic-workflow-runner-and-ui

    except Exception as exc:  # pragma: no cover - defensive logging
        current_app.logger.error("Error in sermons route: %s", exc)
 codex/expand-event-model-for-recurrence-and-tags
    except SQLAlchemyError as exc:
        current_app.logger.error('Database error while fetching sermons: %s', exc)
        flash('Unable to load sermons at this time.', 'danger')
        return render_template('sermons.html', sermons=[])
    except Exception as exc:  # noqa: BLE001
        current_app.logger.error('Unexpected error in sermons route: %s', exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        current_app.logger.error(f"Error in sermons route: {exc}")
     main
        return render_template('sermons.html', sermons=[])


@sermons_bp.route('/sermons/search')
def search_sermons():
 codex/add-generic-workflow-runner-and-ui
    """Advanced search endpoint for sermons."""
     main
    return sermons()


@sermons_bp.route('/sermons/<int:sermon_id>')
def sermon_detail(sermon_id: int):
    try:
 codex/add-generic-workflow-runner-and-ui
        sermon = db.session.get(Sermon, sermon_id)
 codex/expand-event-model-for-recurrence-and-tags
        sermon = db.session.get(Sermon, sermon_id)
        sermon = Sermon.query.get(sermon_id)
     main
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

 codex/add-generic-workflow-runner-and-ui
        trigger_automation('sermon_viewed', {'sermon_id': sermon.id})
        member = _resolve_member_for_engagement()
        if member:
            try:
                if _log_sermon_engagement(member, sermon):
                    db.session.commit()
            except SQLAlchemyError as engagement_exc:
                db.session.rollback()
                current_app.logger.error(
                    f"Database error logging sermon engagement for member {member.id}: {engagement_exc}"
                )
            except Exception as engagement_exc:  # pragma: no cover - safety net
                db.session.rollback()
                current_app.logger.error(
                    f"Unexpected error logging sermon engagement for member {member.id}: {engagement_exc}"
                )
     main

        return render_template(
            'sermon_detail.html',
            sermon=sermon,
            media_context=media_context,
            related_sermons=related_sermons,
        )
    except SQLAlchemyError as exc:
 codex/add-generic-workflow-runner-and-ui
        current_app.logger.error(
            "Database error while fetching sermon %s: %s",
            sermon_id,
            exc,
        )
        flash('Unable to load the sermon right now. Please try again later.', 'danger')
        return redirect(url_for('sermons.sermons'))
    except Exception as exc:  # pragma: no cover - defensive logging
        current_app.logger.error(
            "Unexpected error in sermon_detail route: %s",
            exc,
        )
        flash('An unexpected error occurred. Please try again later.', 'danger')
        current_app.logger.error('Database error loading sermon %s: %s', sermon_id, exc)
        flash('Unable to load the sermon right now.', 'danger')
        return redirect(url_for('sermons.sermons'))
    except Exception as exc:  # noqa: BLE001
        current_app.logger.error('Unexpected error in sermon_detail: %s', exc)
     main
        return redirect(url_for('sermons.sermons'))


__all__ = ['_build_media_context', '_resolve_video_embed', 'sermons_bp']
