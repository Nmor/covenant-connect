import { Inject, Injectable, UnauthorizedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import type { Provider, ProviderIdentity, UserAccount } from '@covenant-connect/shared';

import { AccountsService } from '../accounts/accounts.service';
import { RegisterDto } from './dto/register.dto';
import {
  AUTH_PROVIDER_STRATEGIES,
  type OAuthExchangeResult,
  type OAuthProvider,
  type OAuthProviderStrategy
} from './providers';
import { Session, SessionStore } from './session.store';

type LoginResult = {
  account: UserAccount;
  session: Session;
};

@Injectable()
export class AuthService {
  private readonly providerMap: Map<OAuthProvider, OAuthProviderStrategy>;

  constructor(
    private readonly accounts: AccountsService,
    private readonly sessions: SessionStore,
    private readonly configService: ConfigService,
    @Inject(AUTH_PROVIDER_STRATEGIES) providerStrategies: OAuthProviderStrategy[]
  ) {
    this.providerMap = new Map(providerStrategies.map((strategy) => [strategy.provider, strategy]));
  }

  async register(payload: RegisterDto): Promise<LoginResult> {
    const account = await this.accounts.createAccount({
      email: payload.email,
      password: payload.password,
      firstName: payload.firstName,
      lastName: payload.lastName,
      roles: payload.roles
    });

    const session = await this.issueSession(account.id);
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

    const session = await this.issueSession(account.id);
    return { account, session };
  }

  async resolveSession(token: string): Promise<UserAccount | null> {
    const session = await this.sessions.get(token);
    if (!session) {
      return null;
    }

    return this.accounts.getAccountById(session.userId);
  }

  async startProviderLogin(provider: Provider, redirectUri?: string, state?: string): Promise<{
    authorizationUrl: string;
    state: string;
  }> {
    const strategy = this.requireStrategy(provider);
    const stateToken = this.encodeState(redirectUri, state);
    const authorizationUrl = strategy.createAuthorizationUrl({ state: stateToken, redirectUri });

    return {
      authorizationUrl,
      state: stateToken
    };
  }

  async completeProviderLogin(
    provider: Provider,
    code: string,
    stateToken?: string
  ): Promise<{ account: UserAccount; session: Session; redirectUri?: string }> {
    const strategy = this.requireStrategy(provider);
    const decodedState = this.decodeState(stateToken);
    let exchange: OAuthExchangeResult;

    try {
      exchange = await strategy.exchangeCode({ code, redirectUri: decodedState?.redirectUri });
    } catch (error) {
      throw new UnauthorizedException('Failed to authenticate with provider');
    }

    const identity: ProviderIdentity = {
      provider,
      providerId: exchange.providerId,
      accessToken: exchange.tokens.accessToken,
      refreshToken: exchange.tokens.refreshToken,
      expiresAt: exchange.tokens.expiresAt
    };

    let account = await this.accounts.getAccountByProvider(provider, identity.providerId);

    if (!account) {
      account = await this.accounts.createAccount({
        email: exchange.email,
        firstName: exchange.firstName || provider,
        lastName: exchange.lastName || 'User',
        provider: identity,
        roles: ['member']
      });
    } else {
      account = await this.accounts.linkProvider(account.id, identity);
    }

    const session = await this.issueSession(account.id);
    const redirectUri = this.resolveRedirect(decodedState?.redirectUri);

    return { account, session, redirectUri };
  }

  async logout(token: string): Promise<void> {
    await this.sessions.revoke(token);
  }

  private issueSession(accountId: string): Promise<Session> {
    const ttl = this.configService.get<number>('security.session.ttlSeconds', 60 * 60 * 24 * 7);
    return this.sessions.create(accountId, ttl);
  }

  private requireStrategy(provider: Provider): OAuthProviderStrategy {
    if (provider === 'password') {
      throw new UnauthorizedException('Password authentication does not support OAuth flows');
    }

    const strategy = this.providerMap.get(provider as OAuthProvider);
    if (!strategy) {
      throw new UnauthorizedException(`Unsupported authentication provider: ${provider}`);
    }

    return strategy;
  }

  private encodeState(redirectUri?: string, state?: string): string {
    return Buffer.from(JSON.stringify({ redirectUri, state })).toString('base64url');
  }

  private decodeState(stateToken?: string): { redirectUri?: string; state?: string } | undefined {
    if (!stateToken) {
      return undefined;
    }

    try {
      const decoded = JSON.parse(Buffer.from(stateToken, 'base64url').toString());
      if (decoded && typeof decoded === 'object') {
        const redirectUri = typeof decoded.redirectUri === 'string' ? decoded.redirectUri : undefined;
        const state = typeof decoded.state === 'string' ? decoded.state : undefined;
        return { redirectUri, state };
      }
    } catch (error) {
      return undefined;
    }

    return undefined;
  }

  private resolveRedirect(redirectUri?: string): string | undefined {
    if (!redirectUri) {
      return undefined;
    }

    try {
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
