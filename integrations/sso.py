"""OAuth2 helpers and provider integrations for social sign-in."""
from __future__ import annotations

import base64
import json
import logging
import secrets
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10


class OAuthError(RuntimeError):
    """Raised when an OAuth provider interaction fails."""


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    """Public metadata describing an SSO provider."""

    name: str
    label: str


@dataclass(frozen=True, slots=True)
class OAuthProfile:
    """Normalized profile information returned from a provider."""

    provider: str
    provider_user_id: str
    email: str | None
    full_name: str | None = None


class OAuthProvider:
    """Base class for OAuth2 providers supported by the application."""

    name: str
    label: str
    client_id_key: str
    client_secret_key: str | None
    authorize_url: str
    token_url: str
    scope: str

    def __init__(self, client_id: str, client_secret: str | None = None) -> None:
        self.client_id = client_id
        self.client_secret = client_secret

    @classmethod
    def is_configured(cls, config: Mapping[str, Any]) -> bool:
        if not config.get(cls.client_id_key):
            return False
        if cls.client_secret_key and not config.get(cls.client_secret_key):
            return False
        return True

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> 'OAuthProvider':
        if not cls.is_configured(config):
            raise OAuthError(f"{cls.label} sign-in is not configured")
        client_id = config.get(cls.client_id_key)
        client_secret = config.get(cls.client_secret_key) if cls.client_secret_key else None
        assert isinstance(client_id, str) and client_id
        if cls.client_secret_key:
            assert isinstance(client_secret, str) and client_secret
        return cls(client_id, client_secret)

    @staticmethod
    def build_state() -> str:
        return secrets.token_urlsafe(32)

    def authorization_url(self, redirect_uri: str, state: str) -> str:
        params = self._authorization_parameters(redirect_uri, state)
        return f"{self.authorize_url}?{urlencode(params)}"

    def _authorization_parameters(self, redirect_uri: str, state: str) -> dict[str, Any]:
        return {
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': self.scope,
            'state': state,
        }

    def fetch_user(self, code: str, redirect_uri: str) -> OAuthProfile:
        raise NotImplementedError

    @staticmethod
    def _check_http_response(response: requests.Response, context: str) -> None:
        if response.status_code >= 400:
            logger.warning('%s failed with status %s: %s', context, response.status_code, response.text)
            raise OAuthError(f'{context} failed with status {response.status_code}')


class GoogleOAuthProvider(OAuthProvider):
    name = 'google'
    label = 'Google'
    client_id_key = 'GOOGLE_CLIENT_ID'
    client_secret_key = 'GOOGLE_CLIENT_SECRET'
    authorize_url = 'https://accounts.google.com/o/oauth2/v2/auth'
    token_url = 'https://oauth2.googleapis.com/token'
    scope = 'openid email profile'
    userinfo_url = 'https://openidconnect.googleapis.com/v1/userinfo'

    def _authorization_parameters(self, redirect_uri: str, state: str) -> dict[str, Any]:
        params = super()._authorization_parameters(redirect_uri, state)
        params['access_type'] = 'offline'
        params['prompt'] = 'consent'
        return params

    def fetch_user(self, code: str, redirect_uri: str) -> OAuthProfile:
        data = {
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }
        response = requests.post(self.token_url, data=data, timeout=DEFAULT_TIMEOUT)
        self._check_http_response(response, 'Google token exchange')
        payload = response.json()
        access_token = payload.get('access_token')
        if not access_token:
            raise OAuthError('Google token exchange did not return an access token')
        userinfo_response = requests.get(
            self.userinfo_url,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=DEFAULT_TIMEOUT,
        )
        self._check_http_response(userinfo_response, 'Google userinfo request')
        info = userinfo_response.json()
        email = info.get('email')
        provider_user_id = info.get('sub')
        if not provider_user_id:
            raise OAuthError('Google userinfo response did not include an id')
        return OAuthProfile(
            provider=self.name,
            provider_user_id=str(provider_user_id),
            email=email,
            full_name=info.get('name'),
        )


class FacebookOAuthProvider(OAuthProvider):
    name = 'facebook'
    label = 'Facebook'
    client_id_key = 'FACEBOOK_CLIENT_ID'
    client_secret_key = 'FACEBOOK_CLIENT_SECRET'
    authorize_url = 'https://www.facebook.com/v19.0/dialog/oauth'
    token_url = 'https://graph.facebook.com/v19.0/oauth/access_token'
    scope = 'email public_profile'
    userinfo_url = 'https://graph.facebook.com/me'

    def fetch_user(self, code: str, redirect_uri: str) -> OAuthProfile:
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': redirect_uri,
            'code': code,
        }
        response = requests.get(self.token_url, params=params, timeout=DEFAULT_TIMEOUT)
        self._check_http_response(response, 'Facebook token exchange')
        payload = response.json()
        access_token = payload.get('access_token')
        if not access_token:
            raise OAuthError('Facebook token exchange did not return an access token')
        userinfo_response = requests.get(
            self.userinfo_url,
            params={'access_token': access_token, 'fields': 'id,name,email'},
            timeout=DEFAULT_TIMEOUT,
        )
        self._check_http_response(userinfo_response, 'Facebook userinfo request')
        info = userinfo_response.json()
        email = info.get('email')
        provider_user_id = info.get('id')
        if not provider_user_id:
            raise OAuthError('Facebook userinfo response did not include an id')
        return OAuthProfile(
            provider=self.name,
            provider_user_id=str(provider_user_id),
            email=email,
            full_name=info.get('name'),
        )


class AppleOAuthProvider(OAuthProvider):
    name = 'apple'
    label = 'Apple'
    client_id_key = 'APPLE_CLIENT_ID'
    client_secret_key = 'APPLE_CLIENT_SECRET'
    authorize_url = 'https://appleid.apple.com/auth/authorize'
    token_url = 'https://appleid.apple.com/auth/token'
    scope = 'email name'

    def _authorization_parameters(self, redirect_uri: str, state: str) -> dict[str, Any]:
        params = super()._authorization_parameters(redirect_uri, state)
        params['response_mode'] = 'query'
        return params

    def fetch_user(self, code: str, redirect_uri: str) -> OAuthProfile:
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
        }
        response = requests.post(
            self.token_url,
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=DEFAULT_TIMEOUT,
        )
        self._check_http_response(response, 'Apple token exchange')
        payload = response.json()
        id_token = payload.get('id_token')
        if not id_token:
            raise OAuthError('Apple token response did not include an id_token')
        info = _decode_jwt_payload(id_token)
        email = info.get('email')
        if not email:
            raise OAuthError('Apple account did not provide an email address')
        provider_user_id = info.get('sub')
        if not provider_user_id:
            raise OAuthError('Apple identity token did not include a subject claim')
        return OAuthProfile(
            provider=self.name,
            provider_user_id=str(provider_user_id),
            email=email,
            full_name=None,
        )


_PROVIDER_REGISTRY: dict[str, type[OAuthProvider]] = {
    GoogleOAuthProvider.name: GoogleOAuthProvider,
    FacebookOAuthProvider.name: FacebookOAuthProvider,
    AppleOAuthProvider.name: AppleOAuthProvider,
}

_PROVIDER_INFO = {
    name: ProviderInfo(name=name, label=provider.label)
    for name, provider in _PROVIDER_REGISTRY.items()
}


def get_enabled_sso_providers(config: Mapping[str, Any]) -> list[ProviderInfo]:
    """Return metadata for all providers configured in the environment."""

    providers: list[ProviderInfo] = []
    for name, provider_cls in _PROVIDER_REGISTRY.items():
        if provider_cls.is_configured(config):
            providers.append(_PROVIDER_INFO[name])
    return providers


def get_oauth_provider(name: str, config: Mapping[str, Any]) -> OAuthProvider:
    """Instantiate the configured provider by name."""

    provider_cls = _PROVIDER_REGISTRY.get(name)
    if not provider_cls:
        raise OAuthError(f'Unknown OAuth provider: {name}')
    return provider_cls.from_config(config)


def _decode_jwt_payload(token: str) -> Mapping[str, Any]:
    """Decode the payload portion of a JWT without verifying signatures."""

    parts = token.split('.')
    if len(parts) < 2:
        raise OAuthError('Invalid identity token returned by provider')
    payload = parts[1]
    padding = '=' * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload + padding)
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as exc:  # pragma: no cover - defensive
        raise OAuthError('Unable to decode identity token payload') from exc


__all__ = [
    'OAuthError',
    'OAuthProfile',
    'OAuthProvider',
    'ProviderInfo',
    'get_enabled_sso_providers',
    'get_oauth_provider',
]
