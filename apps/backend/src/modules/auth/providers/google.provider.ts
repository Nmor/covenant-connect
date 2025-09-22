import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import type {
  AuthorizationUrlParams,
  CodeExchangeParams,
  OAuthExchangeResult,
  OAuthProviderStrategy
} from './oauth-provider.interface';

@Injectable()
export class GoogleOAuthProvider implements OAuthProviderStrategy {
  readonly provider = 'google' as const;

  constructor(private readonly configService: ConfigService) {}

  createAuthorizationUrl({ state, redirectUri }: AuthorizationUrlParams): string {
    const clientId = this.getClientId();
    const params = new URLSearchParams({
      client_id: clientId,
      response_type: 'code',
      scope: 'openid email profile',
      access_type: 'offline',
      prompt: 'consent',
      state
    });

    if (redirectUri) {
      params.set('redirect_uri', redirectUri);
    }

    return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
  }

  async exchangeCode({ code, redirectUri }: CodeExchangeParams): Promise<OAuthExchangeResult> {
    const clientId = this.getClientId();
    const clientSecret = this.getClientSecret();

    const body = new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      code,
      grant_type: 'authorization_code'
    });

    if (redirectUri) {
      body.set('redirect_uri', redirectUri);
    }

    const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString()
    });

    if (!tokenResponse.ok) {
      throw new Error('Failed to exchange Google authorization code for tokens');
    }

    const tokenJson = (await tokenResponse.json()) as {
      access_token?: string;
      refresh_token?: string;
      expires_in?: number;
    };

    const accessToken = tokenJson.access_token;
    if (!accessToken) {
      throw new Error('Google token response did not contain an access token');
    }

    const profileResponse = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
      headers: { Authorization: `Bearer ${accessToken}` }
    });

    if (!profileResponse.ok) {
      throw new Error('Failed to load Google profile information');
    }

    const profileJson = (await profileResponse.json()) as {
      id?: string;
      email?: string;
      given_name?: string;
      family_name?: string;
      name?: string;
      picture?: string;
    };

    const providerId = profileJson.id;
    const email = profileJson.email;

    if (!providerId || !email) {
      throw new Error('Google profile response did not contain the expected fields');
    }

    const [firstName, lastName] = this.extractNames(profileJson);

    return {
      provider: this.provider,
      providerId,
      email,
      firstName,
      lastName,
      avatarUrl: profileJson.picture ?? undefined,
      tokens: {
        accessToken,
        refreshToken: tokenJson.refresh_token ?? undefined,
        expiresAt:
          typeof tokenJson.expires_in === 'number'
            ? new Date(Date.now() + tokenJson.expires_in * 1000)
            : undefined
      }
    };
  }

  private getClientId(): string {
    const clientId = this.configService.get<string>('application.integrations.googleClientId');
    if (!clientId) {
      throw new Error('Google OAuth client ID is not configured');
    }

    return clientId;
  }

  private getClientSecret(): string {
    const clientSecret = this.configService.get<string>('application.integrations.googleClientSecret');
    if (!clientSecret) {
      throw new Error('Google OAuth client secret is not configured');
    }

    return clientSecret;
  }

  private extractNames(profile: { given_name?: string; family_name?: string; name?: string }): [string, string] {
    if (profile.given_name || profile.family_name) {
      return [profile.given_name ?? '', profile.family_name ?? ''];
    }

    if (profile.name) {
      const parts = profile.name.split(' ');
      const [first, ...rest] = parts;
      return [first ?? '', rest.join(' ')];
    }

    return ['Google', 'User'];
  }
}
