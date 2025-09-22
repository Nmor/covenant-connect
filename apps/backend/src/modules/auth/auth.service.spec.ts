import { UnauthorizedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import type { Provider, UserAccount } from '@covenant-connect/shared';

import { AuthService } from './auth.service';
import type { AccountsService } from '../accounts/accounts.service';
import type { OAuthProviderStrategy } from './providers';
import type { Session, SessionStore } from './session.store';

type AccountsServiceMock = Pick<
  AccountsService,
  | 'createAccount'
  | 'getAccountByEmail'
  | 'verifyPassword'
  | 'getAccountById'
  | 'getAccountByProvider'
  | 'linkProvider'
>;

type SessionStoreMock = Pick<SessionStore, 'create' | 'get' | 'revoke'>;

describe('AuthService', () => {
  let accounts: jest.Mocked<AccountsServiceMock>;
  let sessions: jest.Mocked<SessionStoreMock>;
  let providerStrategy: jest.Mocked<OAuthProviderStrategy>;
  let config: ConfigService;
  let service: AuthService;

  const createAccount = (overrides: Partial<UserAccount> = {}): UserAccount => ({
    id: overrides.id ?? 'user-1',
    email: overrides.email ?? 'user@example.com',
    passwordHash: overrides.passwordHash,
    firstName: overrides.firstName ?? 'Test',
    lastName: overrides.lastName ?? 'User',
    avatarUrl: overrides.avatarUrl,
    createdAt: overrides.createdAt ?? new Date('2024-01-01T00:00:00.000Z'),
    updatedAt: overrides.updatedAt ?? new Date('2024-01-01T00:00:00.000Z'),
    roles: overrides.roles ?? ['member'],
    providers: overrides.providers ?? [],
  });

  const createSession = (overrides: Partial<Session> = {}): Session => ({
    token: overrides.token ?? 'session-token',
    userId: overrides.userId ?? 'user-1',
    createdAt: overrides.createdAt ?? new Date('2024-01-01T00:00:00.000Z'),
    expiresAt: overrides.expiresAt ?? new Date('2024-01-08T00:00:00.000Z'),
  });

  beforeEach(() => {
    accounts = {
      createAccount: jest.fn(),
      getAccountByEmail: jest.fn(),
      verifyPassword: jest.fn(),
      getAccountById: jest.fn(),
      getAccountByProvider: jest.fn(),
      linkProvider: jest.fn(),
    } as unknown as jest.Mocked<AccountsServiceMock>;

    sessions = {
      create: jest.fn(),
      get: jest.fn(),
      revoke: jest.fn(),
    } as unknown as jest.Mocked<SessionStoreMock>;

    providerStrategy = {
      provider: 'google',
      createAuthorizationUrl: jest.fn(),
      exchangeCode: jest.fn(),
    } as unknown as jest.Mocked<OAuthProviderStrategy>;

    config = new ConfigService({
      security: { session: { ttlSeconds: 7200 } },
      application: {
        http: { cors: ['https://app.local'] },
      },
    });

    service = new AuthService(
      accounts as unknown as AccountsService,
      sessions as unknown as SessionStore,
      config,
      [providerStrategy]
    );
  });

  it('registers a new account and issues a session', async () => {
    const account = createAccount();
    const session = createSession();

    accounts.createAccount.mockResolvedValue(account);
    sessions.create.mockResolvedValue(session);

    const result = await service.register({
      email: 'user@example.com',
      password: 'pa55w0rd!',
      firstName: 'Test',
      lastName: 'User',
      roles: ['member'],
    });

    expect(accounts.createAccount).toHaveBeenCalledWith({
      email: 'user@example.com',
      password: 'pa55w0rd!',
      firstName: 'Test',
      lastName: 'User',
      roles: ['member'],
    });
    expect(sessions.create).toHaveBeenCalledWith('user-1', 7200);
    expect(result).toEqual({ account, session });
  });

  it('authenticates an existing account with valid credentials', async () => {
    const account = createAccount({ id: 'account-42' });
    const session = createSession({ userId: 'account-42' });

    accounts.getAccountByEmail.mockResolvedValue(account);
    accounts.verifyPassword.mockResolvedValue(true);
    sessions.create.mockResolvedValue(session);

    const result = await service.login('login@example.com', 'password123');

    expect(accounts.getAccountByEmail).toHaveBeenCalledWith('login@example.com');
    expect(accounts.verifyPassword).toHaveBeenCalledWith(account, 'password123');
    expect(sessions.create).toHaveBeenCalledWith('account-42', 7200);
    expect(result.session.token).toBe(session.token);
  });

  it('rejects invalid login attempts', async () => {
    const account = createAccount();
    accounts.getAccountByEmail.mockResolvedValue(account);
    accounts.verifyPassword.mockResolvedValue(false);

    await expect(service.login('user@example.com', 'wrong-pass')).rejects.toBeInstanceOf(
      UnauthorizedException
    );
  });

  it('creates provider authorization URLs with encoded state', async () => {
    providerStrategy.createAuthorizationUrl.mockReturnValue('https://accounts.google.test/auth');

    const result = await service.startProviderLogin('google' as Provider, 'https://app.local/return', 'client-state');

    expect(providerStrategy.createAuthorizationUrl).toHaveBeenCalledWith({
      state: result.state,
      redirectUri: 'https://app.local/return',
    });

    const decoded = JSON.parse(Buffer.from(result.state, 'base64url').toString());
    expect(decoded).toEqual({ redirectUri: 'https://app.local/return', state: 'client-state' });
    expect(result.authorizationUrl).toBe('https://accounts.google.test/auth');
  });

  it('completes provider logins for existing accounts and links identities', async () => {
    const account = createAccount({ id: 'account-7' });
    const linked = createAccount({ id: 'account-7', providers: [{ provider: 'google', providerId: 'google-123' }] });
    const session = createSession({ userId: 'account-7', token: 'linked-session' });

    providerStrategy.exchangeCode.mockResolvedValue({
      provider: 'google',
      providerId: 'google-123',
      email: 'account@example.com',
      firstName: 'Linked',
      lastName: 'User',
      tokens: {
        accessToken: 'access-token',
        refreshToken: 'refresh-token',
        expiresAt: new Date('2024-01-05T00:00:00.000Z'),
      },
    });
    accounts.getAccountByProvider.mockResolvedValue(account);
    accounts.linkProvider.mockResolvedValue(linked);
    sessions.create.mockResolvedValue(session);

    const state = Buffer.from(
      JSON.stringify({ redirectUri: 'https://app.local/dashboard', state: 'persist-me' })
    ).toString('base64url');

    const result = await service.completeProviderLogin('google', 'auth-code', state);

    expect(providerStrategy.exchangeCode).toHaveBeenCalledWith({ code: 'auth-code', redirectUri: 'https://app.local/dashboard' });
    expect(accounts.getAccountByProvider).toHaveBeenCalledWith('google', 'google-123');
    expect(accounts.linkProvider).toHaveBeenCalledWith('account-7', expect.objectContaining({
      provider: 'google',
      providerId: 'google-123',
    }));
    expect(sessions.create).toHaveBeenCalledWith('account-7', 7200);
    expect(result.session.token).toBe('linked-session');
    expect(result.redirectUri).toBe('https://app.local/dashboard');
  });

  it('resolves active sessions to user accounts', async () => {
    const account = createAccount({ id: 'account-9' });
    const session = createSession({ userId: 'account-9', token: 'active-session' });

    sessions.get.mockResolvedValue(session);
    accounts.getAccountById.mockResolvedValue(account);

    const resolved = await service.resolveSession('active-session');

    expect(sessions.get).toHaveBeenCalledWith('active-session');
    expect(accounts.getAccountById).toHaveBeenCalledWith('account-9');
    expect(resolved).toEqual(account);
  });

  it('throws unauthorized when provider exchanges fail', async () => {
    providerStrategy.exchangeCode.mockRejectedValue(new Error('OAuth exchange failed'));

    await expect(service.completeProviderLogin('google', 'bad-code')).rejects.toBeInstanceOf(
      UnauthorizedException
    );
  });
});
