import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { SignJWT, decodeJwt, importPKCS8 } from 'jose';

import type {
  AuthorizationUrlParams,
  CodeExchangeParams,
  OAuthExchangeResult,
  OAuthProviderStrategy
} from './oauth-provider.interface';

const APPLE_TOKEN_URL = 'https://appleid.apple.com/auth/token';
const APPLE_AUTHORIZE_URL = 'https://appleid.apple.com/auth/authorize';
const APPLE_AUDIENCE = 'https://appleid.apple.com';
const APPLE_ALGORITHM = 'ES256';

@Injectable()
export class AppleOAuthProvider implements OAuthProviderStrategy {
  readonly provider = 'apple' as const;

  constructor(private readonly configService: ConfigService) {}

  createAuthorizationUrl({ state, redirectUri }: AuthorizationUrlParams): string {
    const clientId = this.getClientId();
    const params = new URLSearchParams({
      response_type: 'code',
      response_mode: 'form_post',
      scope: 'name email',
      client_id: clientId,
      state
    });

    if (redirectUri) {
      params.set('redirect_uri', redirectUri);
    }

    return `${APPLE_AUTHORIZE_URL}?${params.toString()}`;
  }

  async exchangeCode({ code, redirectUri }: CodeExchangeParams): Promise<OAuthExchangeResult> {
    const clientId = this.getClientId();
    const clientSecret = await this.generateClientSecret(clientId);

    const body = new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      code,
      grant_type: 'authorization_code'
    });

    if (redirectUri) {
      body.set('redirect_uri', redirectUri);
    }

    const tokenResponse = await fetch(APPLE_TOKEN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString()
    });

    if (!tokenResponse.ok) {
      throw new Error('Failed to exchange Apple authorization code for tokens');
    }

    const tokenJson = (await tokenResponse.json()) as {
      access_token?: string;
      refresh_token?: string;
      expires_in?: number;
      id_token?: string;
    };

    const accessToken = tokenJson.access_token;
    if (!accessToken || !tokenJson.id_token) {
      throw new Error('Apple token response did not contain the expected fields');
    }

    const payload = decodeJwt(tokenJson.id_token) as {
      sub?: string;
      email?: string;
      given_name?: string;
      family_name?: string;
    };

    if (!payload.sub || !payload.email) {
      throw new Error('Apple identity token did not contain the expected fields');
    }

    return {
      provider: this.provider,
      providerId: payload.sub,
      email: payload.email,
      firstName: payload.given_name ?? 'Apple',
      lastName: payload.family_name ?? 'User',
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
    const clientId = this.configService.get<string>('application.integrations.appleClientId');
    if (!clientId) {
      throw new Error('Apple Sign In client ID is not configured');
    }

    return clientId;
  }

  private async generateClientSecret(clientId: string): Promise<string> {
    const teamId = this.configService.get<string>('application.integrations.appleTeamId');
    const keyId = this.configService.get<string>('application.integrations.appleKeyId');
    const privateKey = this.configService.get<string>('application.integrations.applePrivateKey');

    if (!teamId || !keyId || !privateKey) {
      throw new Error('Apple Sign In credentials are not fully configured');
    }

    const sanitizedKey = (privateKey.includes('-----BEGIN')
      ? privateKey
      : privateKey.replace(/\\n/g, '\n'))
      .trim();

    const key = await importPKCS8(sanitizedKey, APPLE_ALGORITHM);

    return new SignJWT({})
      .setProtectedHeader({ kid: keyId, alg: APPLE_ALGORITHM })
      .setIssuer(teamId)
      .setAudience(APPLE_AUDIENCE)
      .setSubject(clientId)
      .setIssuedAt()
      .setExpirationTime('5m')
      .sign(key);
  }
}
