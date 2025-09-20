import { registerAs } from '@nestjs/config';

type HealthIndicatorConfig = {
  database: boolean;
  redis: boolean;
};

type HealthConfig = {
  livenessKey: string;
  readinessKey: string;
  indicators: HealthIndicatorConfig;
};

export const healthConfig = registerAs<HealthConfig>('health', () => ({
  livenessKey: process.env.HEALTH_LIVENESS_KEY ?? 'covenant-connect:liveness',
  readinessKey: process.env.HEALTH_READINESS_KEY ?? 'covenant-connect:readiness',
  indicators: {
    database: process.env.HEALTH_DATABASE_ENABLED !== 'false',
    redis: process.env.HEALTH_REDIS_ENABLED !== 'false'
  }
}));
