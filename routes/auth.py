import logging
import re
from urllib.parse import urljoin, urlparse

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import SQLAlchemyError

from app import db
from integrations.sso import OAuthError, OAuthProfile, get_enabled_sso_providers, get_oauth_provider
from models import User

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger('covenant_connect')

_USERNAME_SANITIZER = re.compile(r'[^a-z0-9._-]')


def _is_safe_url(target: str | None) -> bool:
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return (
        test_url.scheme in {'http', 'https'} and ref_url.netloc == test_url.netloc
    )


def _get_next_target() -> str | None:
    target = request.form.get('next') or request.args.get('next')
    if target and _is_safe_url(target):
        return target
    return None


def _generate_unique_username(email: str) -> str:
    base = email.split('@', 1)[0].lower()
    base = _USERNAME_SANITIZER.sub('', base) or 'user'
    candidate = base
    suffix = 1
    while User.query.filter_by(username=candidate).first():
        candidate = f"{base}{suffix}"
        suffix += 1
    return candidate


def _create_or_update_user_from_profile(profile: OAuthProfile) -> User:
    user: User | None = None
    if profile.provider_user_id:
        user = User.query.filter_by(
            auth_provider=profile.provider,
            auth_provider_id=profile.provider_user_id,
        ).first()

    if not user and profile.email:
        user = User.query.filter_by(email=profile.email).first()

    if user:
        updated = False
        if not user.auth_provider:
            user.auth_provider = profile.provider
            updated = True
        if not user.auth_provider_id and profile.provider_user_id:
            user.auth_provider_id = profile.provider_user_id
            updated = True
        if updated:
            db.session.add(user)
        return user

    if not profile.email:
        raise OAuthError('The provider did not supply an email address.')

    username = _generate_unique_username(profile.email)
    user = User(
        username=username,
        email=profile.email,
        is_admin=False,
        notification_preferences={},
        auth_provider=profile.provider,
        auth_provider_id=profile.provider_user_id,
    )
    db.session.add(user)
    return user


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next')
    if next_url and not _is_safe_url(next_url):
        next_url = None
    sso_providers = get_enabled_sso_providers(current_app.config)

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        logger.info(f"Login attempt for email: {email}")

        try:
            user = User.query.filter_by(email=email).first()

            if user:
                logger.info(f"User found with email: {email}")
                if user.check_password(password):
                    login_user(user)
                    logger.info(f"Successful login for user: {email}")
                    flash('Successfully logged in!', 'success')
                    next_target = _get_next_target()
                    if next_target:
                        return redirect(next_target)
                    return redirect(url_for('home.home'))
                else:
                    logger.warning(f"Invalid password for user: {email}")
                    flash('Invalid email or password.', 'danger')
            else:
                logger.warning(f"No user found with email: {email}")
                flash('Invalid email or password.', 'danger')

        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            flash('An error occurred during login.', 'danger')

        submitted_next = _get_next_target()
        if submitted_next:
            next_url = submitted_next

    return render_template('auth/login.html', sso_providers=sso_providers, next_url=next_url)


@auth_bp.route('/login/<provider>/start')
def oauth_start(provider: str):
    enabled = {info.name for info in get_enabled_sso_providers(current_app.config)}
    if provider not in enabled:
        abort(404)

    try:
        oauth_provider = get_oauth_provider(provider, current_app.config)
    except OAuthError as exc:
        current_app.logger.warning('OAuth configuration error for %s: %s', provider, exc)
        flash('Single sign-on is not available for this provider.', 'danger')
        return redirect(url_for('auth.login'))

    state = oauth_provider.build_state()
    session['oauth_state'] = {'provider': provider, 'value': state}

    next_target = request.args.get('next')
    if next_target and _is_safe_url(next_target):
        session['oauth_next'] = next_target
    else:
        session.pop('oauth_next', None)

    redirect_uri = url_for('auth.oauth_callback', provider=provider, _external=True)
    authorization_url = oauth_provider.authorization_url(redirect_uri, state)
    return redirect(authorization_url)


@auth_bp.route('/oauth/<provider>/callback')
def oauth_callback(provider: str):
    state_data = session.get('oauth_state') or {}
    if state_data.get('provider') != provider:
        session.pop('oauth_state', None)
        session.pop('oauth_next', None)
        flash('Invalid sign-in request. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

    expected_state = state_data.get('value')
    if not expected_state or request.args.get('state') != expected_state:
        session.pop('oauth_state', None)
        session.pop('oauth_next', None)
        flash('Invalid sign-in request. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

    code = request.args.get('code')
    if not code:
        session.pop('oauth_state', None)
        session.pop('oauth_next', None)
        flash('Authorization code missing from provider response.', 'danger')
        return redirect(url_for('auth.login'))

    try:
        oauth_provider = get_oauth_provider(provider, current_app.config)
        profile = oauth_provider.fetch_user(
            code, url_for('auth.oauth_callback', provider=provider, _external=True)
        )
        user = _create_or_update_user_from_profile(profile)
        db.session.commit()
    except OAuthError as exc:
        db.session.rollback()
        session.pop('oauth_state', None)
        session.pop('oauth_next', None)
        current_app.logger.warning('OAuth callback failed for %s: %s', provider, exc)
        flash('We could not complete the sign-in request.', 'danger')
        return redirect(url_for('auth.login'))
    except SQLAlchemyError as exc:
        db.session.rollback()
        session.pop('oauth_state', None)
        session.pop('oauth_next', None)
        current_app.logger.error('Database error while handling %s sign-in: %s', provider, exc)
        flash('We could not complete the sign-in request.', 'danger')
        return redirect(url_for('auth.login'))

    login_user(user)
    session.pop('oauth_state', None)
    next_target = session.pop('oauth_next', None)
    flash('Successfully logged in!', 'success')
    if next_target and _is_safe_url(next_target):
        return redirect(next_target)
    return redirect(url_for('home.home'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        try:
            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return redirect(url_for('auth.register'))
                
            if User.query.filter_by(username=username).first():
                flash('Username already exists.', 'danger')
                return redirect(url_for('auth.register'))
                
            if User.query.filter_by(email=email).first():
                flash('Email already registered.', 'danger')
                return redirect(url_for('auth.register'))
            
            user = User(
                username=username,
                email=email,
                is_admin=False,
                notification_preferences={}
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"New user registered: {email}")
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            logger.error(f"Error during registration: {str(e)}")
            flash('An error occurred during registration.', 'danger')
            db.session.rollback()
            
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    email = current_user.email
    logout_user()
    logger.info(f"User logged out: {email}")
    flash('Successfully logged out.', 'success')
    return redirect(url_for('home.home'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')
