import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import type {
  AuthorizationUrlParams,
  CodeExchangeParams,
  OAuthExchangeResult,
  OAuthProviderStrategy
} from './oauth-provider.interface';

@Injectable()
export class FacebookOAuthProvider implements OAuthProviderStrategy {
  readonly provider = 'facebook' as const;

  constructor(private readonly configService: ConfigService) {}

  createAuthorizationUrl({ state, redirectUri }: AuthorizationUrlParams): string {
    const clientId = this.getClientId();
    const params = new URLSearchParams({
      client_id: clientId,
      response_type: 'code',
      scope: 'email,public_profile',
      state
    });

    if (redirectUri) {
      params.set('redirect_uri', redirectUri);
    }

    return `https://www.facebook.com/v14.0/dialog/oauth?${params.toString()}`;
  }

  async exchangeCode({ code, redirectUri }: CodeExchangeParams): Promise<OAuthExchangeResult> {
    const clientId = this.getClientId();
    const clientSecret = this.getClientSecret();

    const tokenParams = new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      code
    });

    if (redirectUri) {
      tokenParams.set('redirect_uri', redirectUri);
    }

    const tokenUrl = `https://graph.facebook.com/v14.0/oauth/access_token?${tokenParams.toString()}`;
    const tokenResponse = await fetch(tokenUrl, { method: 'GET' });

    if (!tokenResponse.ok) {
      throw new Error('Failed to exchange Facebook authorization code for tokens');
    }

    const tokenJson = (await tokenResponse.json()) as {
      access_token?: string;
      token_type?: string;
      expires_in?: number;
    };

    const accessToken = tokenJson.access_token;
    if (!accessToken) {
      throw new Error('Facebook token response did not contain an access token');
    }

    const profileParams = new URLSearchParams({
      fields: 'id,email,first_name,last_name,picture',
      access_token: accessToken
    });

    const profileUrl = `https://graph.facebook.com/me?${profileParams.toString()}`;
    const profileResponse = await fetch(profileUrl, { method: 'GET' });

    if (!profileResponse.ok) {
      throw new Error('Failed to load Facebook profile information');
    }

    const profileJson = (await profileResponse.json()) as {
      id?: string;
      email?: string;
      first_name?: string;
      last_name?: string;
      picture?: { data?: { url?: string } };
    };

    const providerId = profileJson.id;
    const email = profileJson.email;

    if (!providerId || !email) {
      throw new Error('Facebook profile response did not contain the expected fields');
    }

    return {
      provider: this.provider,
      providerId,
      email,
      firstName: profileJson.first_name ?? 'Facebook',
      lastName: profileJson.last_name ?? 'User',
      avatarUrl: profileJson.picture?.data?.url ?? undefined,
      tokens: {
        accessToken,
        expiresAt:
          typeof tokenJson.expires_in === 'number'
            ? new Date(Date.now() + tokenJson.expires_in * 1000)
            : undefined
      }
    };
  }

  private getClientId(): string {
    const clientId = this.configService.get<string>('application.integrations.facebookClientId');
    if (!clientId) {
      throw new Error('Facebook OAuth client ID is not configured');
    }

    return clientId;
  }

  private getClientSecret(): string {
    const clientSecret = this.configService.get<string>('application.integrations.facebookClientSecret');
    if (!clientSecret) {
      throw new Error('Facebook OAuth client secret is not configured');
    }

    return clientSecret;
  }
}
