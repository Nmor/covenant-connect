"""Tests covering security-related configuration defaults."""
from __future__ import annotations

import importlib
import os
from collections.abc import Callable
from types import ModuleType

import pytest

import config as config_module


@pytest.fixture
def reload_config() -> Callable[..., ModuleType]:
    """Reload the :mod:`config` module with temporary environment overrides."""

    saved_env = os.environ.copy()

    def _reload(**env_overrides: str | None) -> ModuleType:
        os.environ.clear()
        os.environ.update(saved_env)
        for key, value in env_overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        return importlib.reload(config_module)

    yield _reload

    os.environ.clear()
    os.environ.update(saved_env)
    importlib.reload(config_module)


def test_production_enables_secure_defaults(reload_config: Callable[..., ModuleType]) -> None:
    module = reload_config(
        ENVIRONMENT='production',
        FLASK_ENV=None,
        SERVER_NAME=None,
        CORS_ORIGINS=None,
        SESSION_COOKIE_SECURE=None,
        REMEMBER_COOKIE_SECURE=None,
        SESSION_COOKIE_HTTPONLY=None,
        SESSION_COOKIE_SAMESITE=None,
        PREFERRED_URL_SCHEME=None,
    )

    cfg = module.Config
    assert cfg.IS_PRODUCTION is True
    assert cfg.SESSION_COOKIE_SECURE is True
    assert cfg.REMEMBER_COOKIE_SECURE is True
    assert cfg.SESSION_COOKIE_HTTPONLY is True
    assert cfg.PREFERRED_URL_SCHEME == 'https'
    assert cfg.SESSION_COOKIE_SAMESITE == 'Lax'
    assert cfg.CORS_ORIGINS == []


def test_production_with_server_name_populates_cors_default(
    reload_config: Callable[..., ModuleType],
) -> None:
    module = reload_config(
        ENVIRONMENT='production',
        SERVER_NAME='api.example.com',
        FLASK_ENV=None,
        CORS_ORIGINS=None,
    )

    assert module.Config.CORS_ORIGINS == ['https://api.example.com']


def test_custom_cors_list_parses_csv(reload_config: Callable[..., ModuleType]) -> None:
    module = reload_config(
        ENVIRONMENT='production',
        CORS_ORIGINS='https://foo.example, https://bar.example',
        FLASK_ENV=None,
    )

    assert module.Config.CORS_ORIGINS == [
        'https://foo.example',
        'https://bar.example',
    ]


def test_development_allows_wildcard_cors(reload_config: Callable[..., ModuleType]) -> None:
    module = reload_config(
        ENVIRONMENT='development',
        FLASK_ENV=None,
        CORS_ORIGINS=None,
        SESSION_COOKIE_SECURE=None,
        REMEMBER_COOKIE_SECURE=None,
        PREFERRED_URL_SCHEME=None,
    )

    cfg = module.Config
    assert cfg.IS_PRODUCTION is False
    assert cfg.SESSION_COOKIE_SECURE is False
    assert cfg.REMEMBER_COOKIE_SECURE is False
    assert cfg.PREFERRED_URL_SCHEME == 'http'
    assert cfg.CORS_ORIGINS == '*'
