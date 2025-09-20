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

const parseCorsOrigins = (value: string | undefined): string[] => {
  if (!value) {
    return [];
  }

  return value
    .split(',')
    .map((origin) => origin.trim())
    .filter(Boolean);
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
  databaseUrl: process.env.DATABASE_URL ?? null,
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
    appleTeamId: process.env.APPLE_TEAM_ID ?? null,
    appleKeyId: process.env.APPLE_KEY_ID ?? null,
    applePrivateKey: process.env.APPLE_PRIVATE_KEY ?? null
  },
  assetBaseUrl: process.env.ASSET_BASE_URL ?? null
}));
