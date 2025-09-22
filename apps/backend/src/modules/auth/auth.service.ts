import { Injectable, UnauthorizedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import type { Provider, ProviderIdentity, UserAccount } from '@covenant-connect/shared';

import { AccountsService } from '../accounts/accounts.service';
import { RegisterDto } from './dto/register.dto';
import { Session, SessionStore } from './session.store';

type LoginResult = {
  account: UserAccount;
  session: Session;
};

type ProviderProfile = {
  providerId: string;
  email: string;
  firstName: string;
  lastName: string;
  avatarUrl?: string;
};

@Injectable()
export class AuthService {
  constructor(
    private readonly accounts: AccountsService,
    private readonly sessions: SessionStore,
    private readonly configService: ConfigService
  ) {}

  async register(payload: RegisterDto): Promise<LoginResult> {
    const account = await this.accounts.createAccount({
      email: payload.email,
      password: payload.password,
      firstName: payload.firstName,
      lastName: payload.lastName,
      roles: payload.roles
    });

    const session = this.issueSession(account.id);
    return { account, session };
  }

  async login(email: string, password: string): Promise<LoginResult> {
    const account = await this.accounts.getAccountByEmail(email);
    if (!account) {
      throw new UnauthorizedException('Invalid email or password');
    }

    const isValid = await this.accounts.verifyPassword(account, password);
    if (!isValid) {
      throw new UnauthorizedException('Invalid email or password');
    }

    const session = this.issueSession(account.id);
    return { account, session };
  }

  async resolveSession(token: string): Promise<UserAccount | null> {
    const session = this.sessions.get(token);
    if (!session) {
      return null;
    }

    return this.accounts.getAccountById(session.userId);
  }

  async startProviderLogin(provider: Provider, redirectUri?: string, state?: string): Promise<{
    authorizationUrl: string;
    state: string;
  }> {
    const stateToken = Buffer.from(JSON.stringify({ redirectUri, state })).toString('base64url');
    const baseUrl = this.providerBaseUrl(provider);
    const authorizationUrl = `${baseUrl}?state=${stateToken}`;

    return {
      authorizationUrl,
      state: stateToken
    };
  }

  async completeProviderLogin(
    provider: Provider,
    profile: ProviderProfile,
    stateToken?: string
  ): Promise<{ account: UserAccount; session: Session; redirectUri?: string }> {
    let account = await this.accounts.getAccountByProvider(provider, profile.providerId);

    if (!account) {
      const providerIdentity: ProviderIdentity = {
        provider,
        providerId: profile.providerId,
        accessToken: 'mock-access-token'
      };

      account = await this.accounts.createAccount({
        email: profile.email,
        firstName: profile.firstName,
        lastName: profile.lastName,
        provider: providerIdentity,
        roles: ['member']
      });
    } else {
      await this.accounts.linkProvider(account.id, {
        provider,
        providerId: profile.providerId,
        accessToken: 'mock-access-token'
      });
    }

    const session = this.issueSession(account.id);
    const redirectUri = this.extractRedirect(stateToken);

    return { account, session, redirectUri };
  }

  async logout(token: string): Promise<void> {
    this.sessions.revoke(token);
  }

  private issueSession(accountId: string): Session {
    const ttl = this.configService.get<number>('security.session.ttlSeconds', 60 * 60 * 24 * 7);
    return this.sessions.create(accountId, ttl);
  }

  private providerBaseUrl(provider: Provider): string {
    const overrides: Record<Provider, string> = {
      google: 'https://accounts.google.com/o/oauth2/v2/auth',
      facebook: 'https://www.facebook.com/v14.0/dialog/oauth',
      apple: 'https://appleid.apple.com/auth/authorize',
      password: ''
    };

    return overrides[provider];
  }

  private extractRedirect(stateToken?: string): string | undefined {
    if (!stateToken) {
      return undefined;
    }

    try {
      const decoded = JSON.parse(Buffer.from(stateToken, 'base64url').toString());
      const redirectUri: string | undefined = decoded.redirectUri;
      if (!redirectUri) {
        return undefined;
      }

      const allowedOrigins = this.configService.get<string[]>('application.http.cors', []);
      const parsed = new URL(redirectUri);
      if (allowedOrigins.length > 0 && !allowedOrigins.includes(parsed.origin)) {
        return undefined;
      }

      return redirectUri;
    } catch (error) {
      return undefined;
    }
  }
}
