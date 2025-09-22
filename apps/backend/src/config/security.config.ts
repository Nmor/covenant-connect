import { registerAs } from '@nestjs/config';

export const securityConfig = registerAs('security', () => ({
  session: {
    secret: process.env.SESSION_SECRET ?? 'change-me',
    secureCookies: process.env.COOKIE_SECURE === 'true',
    ttlSeconds: Number.parseInt(process.env.SESSION_TTL ?? '604800', 10)
  },
  csrf: {
    enabled: process.env.CSRF_ENABLED !== 'false'
  }
}));
