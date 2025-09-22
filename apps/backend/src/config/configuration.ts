import { registerAs } from '@nestjs/config';

type HttpConfig = {
  port: number;
  cors: string[];
  cookieDomain: string | null;
};

type PaymentsConfig = {
  stripeKey: string | null;
  paystackKey: string | null;
  flutterwaveKey: string | null;
  fincraKey: string | null;
};

type IntegrationsConfig = {
  googleClientId: string | null;
  googleClientSecret: string | null;
  facebookClientId: string | null;
  facebookClientSecret: string | null;
  appleClientId: string | null;
  appleTeamId: string | null;
  appleKeyId: string | null;
  applePrivateKey: string | null;
};

export type ApplicationConfig = {
  name: string;
  environment: string;
  version: string;
  http: HttpConfig;
  databaseUrl: string | null;
  redisUrl: string | null;
  payments: PaymentsConfig;
  integrations: IntegrationsConfig;
  assetBaseUrl: string | null;
};

const FALLBACK_CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000'];

const parseCorsOrigins = (value: string | undefined): string[] => {
  const parsed = value
    ?.split(',')
    .map((origin) => origin.trim())
    .filter(Boolean);

  if (parsed && parsed.length > 0) {
    return parsed;
  }

  return FALLBACK_CORS_ORIGINS;
};

export default registerAs<ApplicationConfig>('application', () => ({
  name: process.env.APP_NAME ?? 'Covenant Connect',
  environment: process.env.NODE_ENV ?? 'development',
  version: process.env.APP_VERSION ?? '0.0.1',
  http: {
    port: Number.parseInt(process.env.PORT ?? '8000', 10),
    cors: parseCorsOrigins(process.env.CORS_ORIGINS),
    cookieDomain: process.env.COOKIE_DOMAIN ?? null
  },
  databaseUrl:
    process.env.DATABASE_URL ?? 'postgresql://postgres:postgres@localhost:5432/covenant_dev?schema=public',
  redisUrl: process.env.REDIS_URL ?? null,
  payments: {
    stripeKey: process.env.STRIPE_SECRET_KEY ?? null,
    paystackKey: process.env.PAYSTACK_SECRET_KEY ?? null,
    flutterwaveKey: process.env.FLUTTERWAVE_SECRET_KEY ?? null,
    fincraKey: process.env.FINCRA_SECRET_KEY ?? null
  },
  integrations: {
    googleClientId: process.env.GOOGLE_CLIENT_ID ?? null,
    googleClientSecret: process.env.GOOGLE_CLIENT_SECRET ?? null,
    facebookClientId: process.env.FACEBOOK_CLIENT_ID ?? null,
    facebookClientSecret: process.env.FACEBOOK_CLIENT_SECRET ?? null,
    appleClientId: process.env.APPLE_CLIENT_ID ?? null,
    appleTeamId: process.env.APPLE_TEAM_ID ?? null,
    appleKeyId: process.env.APPLE_KEY_ID ?? null,
    applePrivateKey: process.env.APPLE_PRIVATE_KEY ?? null
  },
  assetBaseUrl: process.env.ASSET_BASE_URL ?? null
}));
