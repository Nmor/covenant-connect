import os
from collections.abc import Sequence

from dotenv import load_dotenv

load_dotenv()


TRUE_VALUES = {'1', 'true', 't', 'yes', 'y', 'on'}


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


def _split_csv(name: str) -> list[str] | None:
    value = os.getenv(name)
    if not value:
        return None
    items = [item.strip() for item in value.split(',') if item.strip()]
    return items


_environment = os.getenv('ENVIRONMENT') or os.getenv('FLASK_ENV') or 'development'
_environment_normalized = _environment.lower()
_is_production = _environment_normalized in {'production', 'prod'}


def _normalize_origins(origins: Sequence[str]) -> Sequence[str] | str:
    if not origins:
        return []
    if len(origins) == 1:
        return origins[0]
    return list(origins)


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError('DATABASE_URL is not set')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')

    ENVIRONMENT = _environment
    IS_PRODUCTION = _is_production

    SESSION_COOKIE_SECURE = _get_bool('SESSION_COOKIE_SECURE', _is_production)
    SESSION_COOKIE_HTTPONLY = _get_bool('SESSION_COOKIE_HTTPONLY', True)
    REMEMBER_COOKIE_SECURE = _get_bool('REMEMBER_COOKIE_SECURE', _is_production)
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    PREFERRED_URL_SCHEME = os.getenv(
        'PREFERRED_URL_SCHEME', 'https' if _is_production else 'http'
    )

    SERVER_NAME = os.getenv('SERVER_NAME') or None

    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = _get_bool('MAIL_USE_TLS', True)
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')

    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    _cors_from_env = _split_csv('CORS_ORIGINS')
    if _cors_from_env is not None:
        CORS_ORIGINS = _normalize_origins(_cors_from_env)
    elif _is_production and SERVER_NAME:
        CORS_ORIGINS = [f"{PREFERRED_URL_SCHEME}://{SERVER_NAME}"]
    elif _is_production:
        CORS_ORIGINS = []
    else:
        CORS_ORIGINS = '*'

    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
    FINCRA_SECRET_KEY = os.getenv('FINCRA_SECRET_KEY')
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    FLUTTERWAVE_SECRET_KEY = os.getenv('FLUTTERWAVE_SECRET_KEY')
