import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main(): Promise<void> {
  await prisma.settings.upsert({
    where: { id: 1 },
    update: {},
    create: {
      id: 1,
      businessName: 'Covenant Connect',
      themePreference: 'dark'
    }
  });

  await prisma.church.upsert({
    where: { id: 1 },
    update: {},
    create: {
      id: 1,
      name: 'Covenant Connect Church',
      address: '123 Covenant Way',
      timezone: 'America/New_York',
      country: 'USA',
      state: 'NY',
      city: 'New York'
    }
  });
}

main()
  .catch((error) => {
    console.error('Failed to seed database', error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
