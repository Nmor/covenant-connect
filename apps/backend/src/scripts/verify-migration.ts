import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

type TableCheck = {
  label: string;
  query: () => Promise<number>;
};

async function ensureConnection(): Promise<void> {
  await prisma.$queryRaw`SELECT 1`;
}

async function getPendingMigrationCount(): Promise<number> {
  const result = await prisma.$queryRaw<{ pending: bigint }[]>`
    SELECT COUNT(*)::bigint AS pending
    FROM "_prisma_migrations"
    WHERE finished_at IS NULL
  `;

  const [row] = result;
  if (!row) {
    return 0;
  }

  const value = typeof row.pending === 'bigint' ? Number(row.pending) : Number(row.pending ?? 0);
  return Number.isFinite(value) ? value : 0;
}

async function runTableChecks(): Promise<boolean> {
  const tables: TableCheck[] = [
    { label: 'users', query: () => prisma.user.count() },
    { label: 'members', query: () => prisma.member.count() },
    { label: 'donations', query: () => prisma.donation.count() },
    { label: 'events', query: () => prisma.event.count() },
    { label: 'prayerRequests', query: () => prisma.prayerRequest.count() },
    { label: 'volunteerAssignments', query: () => prisma.volunteerAssignment.count() }
  ];

  let hasError = false;

  for (const table of tables) {
    try {
      const count = await table.query();
      console.info(`✔ ${table.label}: ${count} record(s)`);
    } catch (error) {
      console.error(`✖ Failed to query ${table.label}: ${(error as Error).message}`);
      hasError = true;
    }
  }

  return hasError;
}

async function main(): Promise<void> {
  console.info('Running Prisma migration verification...');
  let hasFailures = false;

  try {
    await ensureConnection();
    console.info('✔ Database connection established');
  } catch (error) {
    console.error('✖ Unable to connect to database via Prisma:', (error as Error).message);
    hasFailures = true;
  }

  if (!hasFailures) {
    try {
      const pendingMigrations = await getPendingMigrationCount();
      if (pendingMigrations === 0) {
        console.info('✔ No pending Prisma migrations detected');
      } else {
        console.warn(`⚠️ ${pendingMigrations} pending Prisma migration(s) detected`);
        hasFailures = true;
      }
    } catch (error) {
      console.error('✖ Unable to inspect Prisma migration metadata:', (error as Error).message);
      hasFailures = true;
    }
  }

  const tableFailures = await runTableChecks();
  if (tableFailures) {
    hasFailures = true;
  }

  if (hasFailures) {
    process.exitCode = 1;
  }
}

main()
  .catch((error) => {
    console.error('Unexpected error while verifying Prisma migration state:', error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
