import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import {
  HealthIndicator,
  type HealthIndicatorFunction,
  type HealthIndicatorResult
} from '@nestjs/terminus';
import Redis from 'ioredis';

import { PrismaService } from '../../prisma/prisma.service';

type QueueConfig = {
  driver: 'redis' | 'memory';
  redisUrl: string | null;
};

type RedisConnection = {
  connect(): Promise<void>;
  ping(): Promise<string>;
  quit(): Promise<unknown>;
  disconnect?(reconnect?: boolean): void;
};

@Injectable()
export class HealthIndicatorService extends HealthIndicator {
  constructor(
    private readonly prisma: PrismaService,
    private readonly configService: ConfigService
  ) {
    super();
  }

  isAlive: HealthIndicatorFunction = async () => {
    return this.getStatus('api', true);
  };

  isReady: HealthIndicatorFunction = async () => {
    const [database, queue] = await Promise.all([this.checkDatabase(), this.checkQueue()]);
    return { ...database, ...queue };
  };

  private async checkDatabase(): Promise<HealthIndicatorResult> {
    try {
      await this.prisma.$queryRaw`SELECT 1`;
    } catch (error) {
      return this.getStatus('database', false, {
        message: (error as Error).message ?? 'Unable to connect to PostgreSQL'
      });
    }

    try {
      const result = await this.prisma.$queryRaw<{ pending: bigint }[]>`
        SELECT COUNT(*)::bigint AS pending
        FROM "_prisma_migrations"
        WHERE finished_at IS NULL
      `;

      const pendingMigrations = this.parseCount(result[0]?.pending);
      const isHealthy = pendingMigrations === 0;

      return this.getStatus('database', isHealthy, {
        pendingMigrations
      });
    } catch (error) {
      return this.getStatus('database', false, {
        message: 'Failed to inspect Prisma migration metadata',
        detail: (error as Error).message ?? String(error)
      });
    }
  }

  private async checkQueue(): Promise<HealthIndicatorResult> {
    const queueConfig = this.resolveQueueConfig();
    const driver = queueConfig.driver;

    if (driver !== 'redis') {
      return this.getStatus('queue', true, { driver });
    }

    if (!queueConfig.redisUrl) {
      return this.getStatus('queue', false, {
        driver,
        message: 'Redis URL missing from configuration'
      });
    }

    const client = new Redis(queueConfig.redisUrl, {
      lazyConnect: true,
      maxRetriesPerRequest: 1
    }) as unknown as RedisConnection;

    let isConnected = false;

    try {
      await client.connect();
      isConnected = true;
      const startedAt = Date.now();
      await client.ping();
      const latencyMs = Date.now() - startedAt;

      return this.getStatus('queue', true, { driver, latencyMs });
    } catch (error) {
      return this.getStatus('queue', false, {
        driver,
        message: (error as Error).message ?? 'Unable to connect to Redis'
      });
    } finally {
      if (isConnected) {
        await client.quit().catch(() => undefined);
      } else {
        const disconnect = client.disconnect;
        if (typeof disconnect === 'function') {
          disconnect.call(client);
        }
      }
    }
  }

  private resolveQueueConfig(): QueueConfig {
    const config = this.configService.get<QueueConfig>('automation.queue');
    const driver = config?.driver ?? 'memory';
    const redisUrl =
      config?.redisUrl ??
      this.configService.get<string>('application.redisUrl') ??
      process.env.REDIS_URL ??
      null;

    return { driver, redisUrl };
  }

  private parseCount(value: unknown): number {
    if (typeof value === 'bigint') {
      return Number(value);
    }

    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }
}
