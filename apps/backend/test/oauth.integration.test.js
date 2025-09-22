const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

require('reflect-metadata');

const { ConfigService } = require('@nestjs/config');

const { AccountsService } = require('../src/modules/accounts/accounts.service');
const { AuthController } = require('../src/modules/auth/auth.controller');
const { AuthService } = require('../src/modules/auth/auth.service');
const { SessionStore } = require('../src/modules/auth/session.store');
const { AppleOAuthProvider, FacebookOAuthProvider, GoogleOAuthProvider } = require('../src/modules/auth/providers');
const { PrismaService } = require('../src/prisma/prisma.service');

const backendRoot = path.resolve(__dirname, '..');
const migrationsDir = path.join(backendRoot, 'prisma/migrations');

const POSTGRES_HOST = process.env.PGHOST ?? 'localhost';
const POSTGRES_PORT = process.env.PGPORT ?? '5432';
const POSTGRES_USER = process.env.POSTGRES_USER ?? 'postgres';
const POSTGRES_PASSWORD = process.env.POSTGRES_PASSWORD ?? 'postgres';

const databaseName = `covenant_oauth_test_${Date.now()}`;
const databaseUrl = `postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${databaseName}`;

const psqlEnv = {
  ...process.env,
  PGPASSWORD: POSTGRES_PASSWORD
};

const APPLE_PRIVATE_KEY = `-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgVeNDNxMtkr+Bc74T\nzMPCeDXmDtepU43qrAPy9nMBYX+hRANCAASkXWJMFa7XhffY/av0z07gG6ThuDky\nnxQ33IBcKeI/pwd8kNxXyuUN86hYKM3plAtlYWUO2Yw80gi8C8J2U0Yi\n-----END PRIVATE KEY-----`;

function execPsql(args) {
  execFileSync('psql', ['-q', ...args], { stdio: 'inherit', env: psqlEnv });
}

function applyMigrations() {
  const migrations = fs
    .readdirSync(migrationsDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(migrationsDir, entry.name, 'migration.sql'))
    .filter((migrationPath) => fs.existsSync(migrationPath))
    .sort();

  if (migrations.length === 0) {
    throw new Error('No Prisma migration files found');
  }

  execPsql(['-h', POSTGRES_HOST, '-p', POSTGRES_PORT, '-U', POSTGRES_USER, '-c', `DROP DATABASE IF EXISTS "${databaseName}"`]);
  execPsql(['-h', POSTGRES_HOST, '-p', POSTGRES_PORT, '-U', POSTGRES_USER, '-c', `CREATE DATABASE "${databaseName}"`]);

  for (const migrationFile of migrations) {
    execPsql([
      '-v',
      'ON_ERROR_STOP=1',
      '-h',
      POSTGRES_HOST,
      '-p',
      POSTGRES_PORT,
      '-U',
      POSTGRES_USER,
      '-d',
      databaseName,
      '-f',
      migrationFile
    ]);
  }
}

function makeIdToken(payload) {
  const header = Buffer.from(JSON.stringify({ alg: 'ES256', kid: 'APPLE_KEY' })).toString('base64url');
  const body = Buffer.from(JSON.stringify(payload)).toString('base64url');
  return `${header}.${body}.signature`;
}

describe('OAuth provider flows', () => {
  let configService;
  let prisma;
  let accounts;
  let sessions;
  let authService;
  let controller;

  beforeAll(async () => {
    process.env.DATABASE_URL = databaseUrl;

    applyMigrations();

    configService = new ConfigService({
      database: { url: databaseUrl },
      application: {
        databaseUrl,
        http: { cors: ['https://app.local'] },
        integrations: {
          googleClientId: 'google-client-id',
          googleClientSecret: 'google-client-secret',
          facebookClientId: 'facebook-client-id',
          facebookClientSecret: 'facebook-client-secret',
          appleClientId: 'apple.service.id',
          appleTeamId: 'APPLE_TEAM',
          appleKeyId: 'APPLE_KEY',
          applePrivateKey: APPLE_PRIVATE_KEY
        }
      }
    });

    prisma = new PrismaService(configService);
    await prisma.onModuleInit();

    accounts = new AccountsService(prisma);
    sessions = new SessionStore(prisma);

    const google = new GoogleOAuthProvider(configService);
    const facebook = new FacebookOAuthProvider(configService);
    const apple = new AppleOAuthProvider(configService);

    authService = new AuthService(accounts, sessions, configService, [google, facebook, apple]);
    controller = new AuthController(authService);
  }, 120000);

  beforeEach(async () => {
    await prisma.session.deleteMany();
    await prisma.accountProvider.deleteMany();
    await prisma.user.deleteMany();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  afterAll(async () => {
    if (prisma?.onModuleDestroy) {
      await prisma.onModuleDestroy();
    }
    execPsql(['-h', POSTGRES_HOST, '-p', POSTGRES_PORT, '-U', POSTGRES_USER, '-c', `DROP DATABASE IF EXISTS "${databaseName}"`]);
  });

  it('signs in new accounts with Google and stores tokens', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    const start = await controller.startProviderLogin('google', {
      redirectUri: 'https://app.local/oauth/callback',
      state: 'client-state'
    });

    expect(start.authorizationUrl).toContain('google-client-id');

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        access_token: 'google-access-token',
        refresh_token: 'google-refresh-token',
        expires_in: 3600
      })
    });

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 'google-user-123',
        email: 'google.user@example.com',
        given_name: 'Google',
        family_name: 'Tester',
        picture: 'https://images.example.com/google-user.png'
      })
    });

    const result = await controller.providerCallback('google', {
      code: 'google-auth-code',
      state: start.state
    });

    expect(result.account.email).toBe('google.user@example.com');
    const googleIdentity = result.account.providers.find((provider) => provider.provider === 'google');
    expect(googleIdentity?.accessToken).toBe('google-access-token');
    expect(googleIdentity?.refreshToken).toBe('google-refresh-token');
    expect(googleIdentity?.expiresAt).toBeInstanceOf(Date);
    expect(result.redirectUri).toBe('https://app.local/oauth/callback');

    const stored = await accounts.getAccountById(result.account.id);
    expect(stored?.providers[0]?.accessToken).toBe('google-access-token');
  });

  it('refreshes Facebook tokens on repeated logins', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    const start = await controller.startProviderLogin('facebook', {
      redirectUri: 'https://app.local/oauth/callback'
    });

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        access_token: 'facebook-access-token-1',
        token_type: 'bearer',
        expires_in: 3600
      })
    });

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 'facebook-user-1',
        email: 'facebook.user@example.com',
        first_name: 'Face',
        last_name: 'Book'
      })
    });

    const firstLogin = await controller.providerCallback('facebook', {
      code: 'facebook-auth-code',
      state: start.state
    });

    const firstIdentity = firstLogin.account.providers.find((provider) => provider.provider === 'facebook');
    expect(firstIdentity?.accessToken).toBe('facebook-access-token-1');

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        access_token: 'facebook-access-token-2',
        token_type: 'bearer',
        expires_in: 7200
      })
    });

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 'facebook-user-1',
        email: 'facebook.user@example.com',
        first_name: 'Face',
        last_name: 'Book'
      })
    });

    const nextStart = await controller.startProviderLogin('facebook', {
      redirectUri: 'https://app.local/oauth/callback'
    });

    const secondLogin = await controller.providerCallback('facebook', {
      code: 'facebook-auth-code-2',
      state: nextStart.state
    });

    const secondIdentity = secondLogin.account.providers.find((provider) => provider.provider === 'facebook');
    expect(secondIdentity?.accessToken).toBe('facebook-access-token-2');
    expect(secondIdentity?.expiresAt).toBeInstanceOf(Date);

    const stored = await accounts.getAccountById(secondLogin.account.id);
    const storedFacebook = stored?.providers.find((provider) => provider.provider === 'facebook');
    expect(storedFacebook?.accessToken).toBe('facebook-access-token-2');
  });

  it('authenticates with Apple and persists refresh tokens', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    const start = await controller.startProviderLogin('apple', {
      redirectUri: 'https://app.local/oauth/callback'
    });

    const idToken = makeIdToken({
      sub: 'apple-user-1',
      email: 'apple.user@example.com',
      given_name: 'Apple',
      family_name: 'Tester'
    });

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        access_token: 'apple-access-token',
        refresh_token: 'apple-refresh-token',
        expires_in: 600,
        id_token: idToken
      })
    });

    const result = await controller.providerCallback('apple', {
      code: 'apple-auth-code',
      state: start.state
    });

    const appleIdentity = result.account.providers.find((provider) => provider.provider === 'apple');
    expect(appleIdentity?.accessToken).toBe('apple-access-token');
    expect(appleIdentity?.refreshToken).toBe('apple-refresh-token');
    expect(appleIdentity?.expiresAt).toBeInstanceOf(Date);
    expect(result.redirectUri).toBe('https://app.local/oauth/callback');

    const stored = await accounts.getAccountById(result.account.id);
    const storedApple = stored?.providers.find((provider) => provider.provider === 'apple');
    expect(storedApple?.refreshToken).toBe('apple-refresh-token');
  });
});
