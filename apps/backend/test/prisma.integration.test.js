const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const { ConfigService } = require('@nestjs/config');

const { AccountsService } = require('../src/modules/accounts/accounts.service');
const { DonationsService } = require('../src/modules/donations/donations.service');
const { EventsService } = require('../src/modules/events/events.service');
const { PrayerService } = require('../src/modules/prayer/prayer.service');
const { PrismaService } = require('../src/prisma/prisma.service');
const { IntegrationsService } = require('../src/modules/integrations/integrations.service');

const backendRoot = path.resolve(__dirname, '..');
const migrationsDir = path.join(backendRoot, 'prisma/migrations');

const POSTGRES_HOST = process.env.PGHOST ?? 'localhost';
const POSTGRES_PORT = process.env.PGPORT ?? '5432';
const POSTGRES_USER = process.env.POSTGRES_USER ?? 'postgres';
const POSTGRES_PASSWORD = process.env.POSTGRES_PASSWORD ?? 'postgres';

const databaseName = `covenant_test_${Date.now()}`;
const databaseUrl = `postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${databaseName}`;

const psqlEnv = {
  ...process.env,
  PGPASSWORD: POSTGRES_PASSWORD
};

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

describe('Prisma-backed services', () => {
  let prisma;
  let accounts;
  let donations;
  let events;
  let prayer;
  let integrations;

  beforeAll(async () => {
    process.env.DATABASE_URL = databaseUrl;

    applyMigrations();

    const configService = new ConfigService({
      database: { url: databaseUrl },
      application: { databaseUrl }
    });

    prisma = new PrismaService(configService);
    await prisma.onModuleInit();

    accounts = new AccountsService(prisma);
    donations = new DonationsService(prisma);
    events = new EventsService(prisma);
    prayer = new PrayerService(prisma);
    integrations = new IntegrationsService(prisma);
  }, 120000);

  beforeEach(async () => {
    await prisma.session.deleteMany();
    await prisma.accountProvider.deleteMany();
    await prisma.user.deleteMany();
    await prisma.donation.deleteMany();
    await prisma.event.deleteMany();
    await prisma.prayerRequest.deleteMany();
    await prisma.integrationSetting.deleteMany();
  });

  afterAll(async () => {
    if (prisma) {
      await prisma.onModuleDestroy();
    }

    execPsql(['-h', POSTGRES_HOST, '-p', POSTGRES_PORT, '-U', POSTGRES_USER, '-c', `DROP DATABASE IF EXISTS "${databaseName}"`]);
  });

  it('creates and verifies user accounts with hashed passwords', async () => {
    const account = await accounts.createAccount({
      email: 'integration@example.com',
      password: 'strongPassword!',
      firstName: 'Integration',
      lastName: 'Tester'
    });

    expect(account.id).toBeDefined();
    expect(account.roles).toContain('member');

    const stored = await accounts.getAccountByEmail('integration@example.com');
    expect(stored).not.toBeNull();
    expect(await accounts.verifyPassword(stored, 'strongPassword!')).toBe(true);
  });

  it('persists donations and updates their status', async () => {
    const donation = await donations.create({
      memberId: null,
      amount: 125.5,
      currency: 'USD',
      provider: 'stripe',
      metadata: { fund: 'General' }
    });

    expect(donation.status).toBe('pending');

    const updated = await donations.updateStatus(donation.id, {
      status: 'completed',
      metadata: { receipt: 'ABC123' }
    });

    expect(updated.status).toBe('completed');
    expect(updated.metadata.receipt).toBe('ABC123');
  });

  it('stores events with structured segments', async () => {
    const startsAt = new Date();
    const endsAt = new Date(startsAt.getTime() + 60 * 60 * 1000);

    const event = await events.create({
      title: 'Integration Event',
      description: 'Testing persistence',
      startsAt,
      endsAt,
      timezone: 'UTC',
      location: 'Main Hall',
      tags: ['integration'],
      segments: [
        { name: 'Setup', startOffsetMinutes: -30, durationMinutes: 30, ownerId: null },
        { name: 'Main', startOffsetMinutes: 0, durationMinutes: 60, ownerId: null }
      ]
    });

    expect(event.segments).toHaveLength(2);

    const list = await events.list({ page: 1, pageSize: 10 });
    expect(list.total).toBe(1);
    expect(list.data[0].title).toBe('Integration Event');
  });

  it('tracks prayer requests lifecycle', async () => {
    const request = await prayer.create({
      requesterName: 'Integration Tester',
      requesterEmail: 'prayer@example.com',
      message: 'Please pray for our launch.',
      memberId: null
    });

    expect(request.status).toBe('new');

    const updated = await prayer.update(request.id, {
      status: 'praying'
    });

    expect(updated.status).toBe('praying');

    const list = await prayer.list();
    expect(list.total).toBe(1);
    expect(list.data[0].requesterName).toBe('Integration Tester');
  });

  it('persists integration settings across service instances', async () => {
    const created = await integrations.create({
      provider: 'stripe',
      config: { apiKey: 'sk_test_123' }
    });

    expect(created.id).toBeGreaterThan(0);
    expect(created.config.apiKey).toBe('sk_test_123');

    const fetched = await integrations.findOne('stripe');
    expect(fetched.config.apiKey).toBe('sk_test_123');

    const anotherInstance = new IntegrationsService(prisma);
    const updated = await anotherInstance.update('stripe', {
      config: { apiKey: 'sk_live_456', accountId: 'acct_123' }
    });

    expect(updated.config.apiKey).toBe('sk_live_456');
    expect(updated.config.accountId).toBe('acct_123');

    const list = await integrations.findAll();
    expect(list).toHaveLength(1);
    expect(list[0].config.apiKey).toBe('sk_live_456');

    await anotherInstance.remove('stripe');

    const emptyList = await integrations.findAll();
    expect(emptyList).toHaveLength(0);
  });
});
