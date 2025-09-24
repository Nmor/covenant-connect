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

  await prisma.sermon.upsert({
    where: { id: 1 },
    update: {},
    create: {
      id: 1,
      title: 'Welcome Home Sunday',
      preacher: 'Pastor Alicia Turner',
      description: 'Kick off the new season with a message of belonging and mission.',
      date: new Date('2024-01-07T15:00:00Z'),
      mediaUrl: 'https://media.covenantconnect.example/sermons/welcome-home',
      mediaType: 'video'
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
