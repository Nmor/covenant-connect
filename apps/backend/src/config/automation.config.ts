import { registerAs } from '@nestjs/config';

type AutomationConfig = {
  queue: {
    driver: 'redis' | 'memory';
    redisUrl: string | null;
    defaultAttempts: number;
  };
  schedules: {
    kpiDigestCron: string;
    followUpCron: string;
  };
};

export const automationConfig = registerAs<AutomationConfig>('automation', () => ({
  queue: {
    driver: (process.env.QUEUE_DRIVER as 'redis' | 'memory') ?? 'memory',
    redisUrl: process.env.REDIS_URL ?? null,
    defaultAttempts: Number.parseInt(process.env.QUEUE_MAX_ATTEMPTS ?? '3', 10)
  },
  schedules: {
    kpiDigestCron: process.env.KPI_DIGEST_CRON ?? '0 7 * * 1',
    followUpCron: process.env.FOLLOW_UP_CRON ?? '0 */6 * * *'
  }
}));
