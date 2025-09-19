"""Internal staff dashboard and church management views."""
from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from models import Church, Donation, Event, PrayerRequest, ServiceIntegration, User

EMAIL_PROVIDER_DEFINITIONS = {
    'aws_ses': {
        'display_name': 'Amazon SES',
        'description': 'Send high-volume transactional mail with Amazon\'s Simple Email Service.',
        'fields': [
            {'name': 'sender_email', 'label': 'Verified sender email', 'type': 'email', 'placeholder': 'notifications@example.com'},
            {'name': 'access_key_id', 'label': 'Access key ID', 'type': 'text', 'sensitive': True},
            {'name': 'secret_access_key', 'label': 'Secret access key', 'type': 'password', 'sensitive': True},
            {'name': 'region', 'label': 'AWS region', 'type': 'text', 'placeholder': 'us-east-1'},
            {'name': 'reply_to', 'label': 'Reply-to email (optional)', 'type': 'email'},
            {'name': 'configuration_set', 'label': 'Configuration set (optional)', 'type': 'text'},
        ],
    },
    'mailgun': {
        'display_name': 'Mailgun',
        'description': 'Connect to Mailgun\'s REST API for marketing or transactional campaigns.',
        'fields': [
            {'name': 'sender_email', 'label': 'From email', 'type': 'email', 'placeholder': 'notifications@example.com'},
            {'name': 'domain', 'label': 'Mailgun domain', 'type': 'text', 'placeholder': 'mg.example.com'},
            {'name': 'api_key', 'label': 'API key', 'type': 'password', 'sensitive': True},
            {'name': 'base_url', 'label': 'Base URL', 'type': 'text', 'placeholder': 'https://api.mailgun.net/v3'},
        ],
    },
    'smtp': {
        'display_name': 'Custom SMTP',
        'description': 'Use Gmail, Outlook, or any SMTP gateway by storing credentials securely.',
        'fields': [
            {'name': 'sender_email', 'label': 'Default sender email', 'type': 'email', 'placeholder': 'notifications@example.com'},
            {'name': 'server', 'label': 'SMTP server host', 'type': 'text', 'placeholder': 'smtp.gmail.com'},
            {'name': 'port', 'label': 'SMTP port', 'type': 'number', 'placeholder': '587'},
            {'name': 'username', 'label': 'SMTP username', 'type': 'text'},
            {'name': 'password', 'label': 'SMTP password', 'type': 'password', 'sensitive': True},
            {'name': 'use_tls', 'label': 'Use TLS', 'type': 'checkbox'},
        ],
    },
}

EMAIL_PROVIDER_ORDER = ['aws_ses', 'mailgun', 'smtp']


internal_bp = Blueprint('internal', __name__)


def _ensure_email_integrations() -> dict[str, ServiceIntegration]:
    """Ensure integration rows exist for each supported email provider."""

    existing = {
        integration.provider: integration
        for integration in ServiceIntegration.query.filter_by(service='email').all()
    }

    created = False
    for provider, definition in EMAIL_PROVIDER_DEFINITIONS.items():
        integration = existing.get(provider)
        if integration is None:
            integration = ServiceIntegration(
                service='email',
                provider=provider,
                display_name=definition['display_name'],
                config={},
                is_active=False,
            )
            db.session.add(integration)
            existing[provider] = integration
            created = True
        elif integration.display_name != definition['display_name']:
            integration.display_name = definition['display_name']
            created = True

    if created:
        db.session.commit()
        existing = {
            integration.provider: integration
            for integration in ServiceIntegration.query.filter_by(service='email').all()
        }

    return existing


@internal_bp.route('/dashboard')
@login_required
def dashboard():
    stats = {
        'users': User.query.count(),
        'donations': Donation.query.count(),
        'prayers': PrayerRequest.query.count(),
        'events': Event.query.count(),
    }
    return render_template('internal/dashboard.html', stats=stats)


@internal_bp.route('/churches')
@login_required
def list_churches():
    churches = Church.query.order_by(Church.name.asc()).all()
    return render_template('internal/churches.html', churches=churches)


@internal_bp.route('/churches/add', methods=['GET', 'POST'])
@login_required
def add_church():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        address = (request.form.get('address') or '').strip()
        if not name:
            flash('Name is required.', 'danger')
            return redirect(url_for('internal.add_church'))
        church = Church(name=name, address=address)
        db.session.add(church)
        db.session.commit()
        flash('Church added successfully.', 'success')
        return redirect(url_for('internal.list_churches'))
    return render_template('internal/church_form.html')


@internal_bp.route('/churches/<int:church_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_church(church_id: int):
    church = Church.query.get_or_404(church_id)
    if request.method == 'POST':
        church.name = (request.form.get('name') or '').strip() or church.name
        church.address = (request.form.get('address') or '').strip()
        db.session.commit()
        flash('Church updated successfully.', 'success')
        return redirect(url_for('internal.list_churches'))
    return render_template('internal/church_form.html', church=church)


@internal_bp.route('/churches/<int:church_id>/delete', methods=['POST'])
@login_required
def delete_church(church_id: int):
    church = Church.query.get_or_404(church_id)
    db.session.delete(church)
    db.session.commit()
    flash('Church deleted.', 'success')
    return redirect(url_for('internal.list_churches'))


@internal_bp.route('/integrations', methods=['GET', 'POST'])
@login_required
def manage_integrations():
    if not current_user.is_admin:
        abort(403)

    integration_map = _ensure_email_integrations()

    if request.method == 'POST':
        provider = (request.form.get('provider') or '').strip()
        definition = EMAIL_PROVIDER_DEFINITIONS.get(provider)
        integration = integration_map.get(provider)

        if not definition or integration is None:
            abort(400)

        updated_config = dict(integration.config or {})
        for field in definition['fields']:
            field_name = field['name']
            field_type = field.get('type', 'text').lower()
            if field_type == 'checkbox':
                updated_config[field_name] = request.form.get(field_name) == 'on'
            else:
                value = (request.form.get(field_name) or '').strip()
                if field.get('sensitive'):
                    if value:
                        updated_config[field_name] = value
                else:
                    updated_config[field_name] = value

        integration.config = updated_config
        integration.is_active = bool(request.form.get('is_active'))
        integration.display_name = definition['display_name']

        if integration.is_active:
            for other_key, other in integration_map.items():
                if other_key != provider and other.is_active:
                    other.is_active = False

        db.session.commit()
        flash(f"{integration.display_name} settings saved.", 'success')
        return redirect(url_for('internal.manage_integrations'))

    email_integrations = []
    # Refresh after any creation inside _ensure_email_integrations
    integration_map = _ensure_email_integrations()

    for provider in EMAIL_PROVIDER_ORDER:
        definition = EMAIL_PROVIDER_DEFINITIONS[provider]
        integration = integration_map.get(provider)
        config = integration.config or {} if integration else {}
        fields = []
        for field in definition['fields']:
            field_type = field.get('type', 'text').lower()
            stored_value = config.get(field['name'])
            field_info = {
                'name': field['name'],
                'label': field['label'],
                'type': field_type,
                'placeholder': field.get('placeholder'),
                'description': field.get('description'),
                'sensitive': field.get('sensitive', False),
                'value': '',
                'checked': False,
                'has_value': False,
            }
            if field_type == 'checkbox':
                field_info['checked'] = bool(stored_value)
            else:
                if field_info['sensitive']:
                    field_info['has_value'] = bool(stored_value)
                else:
                    field_info['value'] = stored_value or ''
                    field_info['has_value'] = bool(stored_value)
            fields.append(field_info)

        email_integrations.append(
            {
                'provider': provider,
                'definition': definition,
                'integration': integration,
                'fields': fields,
            }
        )

    return render_template(
        'internal/integrations.html',
        email_integrations=email_integrations,
    )
