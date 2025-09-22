import { registerAs } from '@nestjs/config';

type DatabaseConfig = {
  url: string;
  shadowUrl: string | null;
};

const DEFAULT_DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/covenant_dev?schema=public';

export const databaseConfig = registerAs<DatabaseConfig>('database', () => {
  const url = process.env.DATABASE_URL ?? DEFAULT_DATABASE_URL;
  const shadowUrl = process.env.SHADOW_DATABASE_URL ?? null;

  return {
    url,
    shadowUrl
  };
});

export type { DatabaseConfig };
