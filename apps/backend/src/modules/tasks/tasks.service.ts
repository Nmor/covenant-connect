import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import type { QueueJob } from '@covenant-connect/shared';
import { Queue, Job, JobsOptions, RepeatOptions } from 'bullmq';
import type { Redis } from 'ioredis';
import IORedis from 'ioredis';

import { TASK_QUEUE_NAME } from './task.constants';

type QueueConfiguration = {
  driver: 'redis' | 'memory';
  redisUrl: string | null;
  defaultAttempts: number;
};

type RepeatScheduleOptions = RepeatOptions & { jobId: string };

const createQueueStub = (): Queue =>
  ({
    add: async () => ({}) as Job,
    getJobs: async () => [],
    getRepeatableJobs: async () => [],
    removeRepeatableByKey: async () => undefined,
    waitUntilReady: async () => undefined,
    close: async () => undefined
  }) as unknown as Queue;

@Injectable()
export class TasksService {
  private readonly logger = new Logger(TasksService.name);
  private readonly queue: Queue;
  private readonly ready: Promise<void>;
  private readonly queueConfig: { redisUrl: string; defaultAttempts: number };

  constructor(private readonly configService: ConfigService) {
    const queueConfig = this.resolveQueueConfig();
    if (process.env.SKIP_TASKS_QUEUE === 'true') {
      this.queueConfig = {
        redisUrl: queueConfig.redisUrl ?? '',
        defaultAttempts: queueConfig.defaultAttempts ?? 3
      };

      this.queue = createQueueStub();
      this.ready = Promise.resolve();
      return;
    }

    if (queueConfig.driver !== 'redis' || !queueConfig.redisUrl) {
      throw new Error('Redis queue configuration is required for automation tasks');
    }

    this.queueConfig = {
      redisUrl: queueConfig.redisUrl,
      defaultAttempts: queueConfig.defaultAttempts ?? 3
    };

    this.queue = new Queue(TASK_QUEUE_NAME, {
      connection: this.createClient(),
      defaultJobOptions: {
        attempts: this.queueConfig.defaultAttempts,
        removeOnComplete: {
          age: 60 * 60, // keep successful jobs for at most an hour
          count: 500
        },
        backoff: {
          type: 'exponential',
          delay: 5_000
        }
      }
    });

    this.ready = this.queue
      .waitUntilReady()
      .catch((error) => {
        this.logger.error('Failed to initialise task queue connection', error as Error);
        throw error;
      });
  }

  async enqueue(
    name: string,
    payload: Record<string, unknown>,
    options: JobsOptions = {}
  ): Promise<QueueJob> {
    await this.waitUntilReady();
    const job = await this.queue.add(name, payload, options);
    return this.mapJob(job);
  }

  async list(): Promise<QueueJob[]> {
    await this.waitUntilReady();
    const jobs = await this.queue.getJobs(['waiting', 'delayed', 'active']);
    return jobs.map((job) => this.mapJob(job));
  }

  async scheduleRepeatable(
    name: string,
    payload: Record<string, unknown>,
    options: RepeatScheduleOptions
  ): Promise<void> {
    await this.waitUntilReady();

    const repeatableJobs = await this.queue.getRepeatableJobs();
    const existing = repeatableJobs.find((job) => job.id === options.jobId);

    if (existing && existing.pattern === options.pattern) {
      return;
    }

    if (existing?.key) {
      await this.queue.removeRepeatableByKey(existing.key);
    }

    const { jobId, ...repeat } = options;

    await this.queue.add(name, payload, {
      jobId,
      repeat,
      removeOnComplete: true,
      removeOnFail: false
    });
  }

  async waitUntilReady(): Promise<void> {
    await this.ready;
  }

  createClient(): Redis {
    return new IORedis(this.queueConfig.redisUrl, {
      maxRetriesPerRequest: null,
      enableReadyCheck: false
    });
  }

  async onModuleDestroy(): Promise<void> {
    await this.queue.close();
  }

  private mapJob(job: Job): QueueJob {
    const baseTimestamp = job.timestamp ?? Date.now();
    const scheduledAt = new Date(baseTimestamp + (job.delay ?? 0));
    const identifier = job.id ?? job.jobId ?? `${job.name}-${baseTimestamp}`;
    return {
      id: identifier.toString(),
      name: job.name,
      payload: (job.data ?? {}) as Record<string, unknown>,
      scheduledAt
    };
  }

  private resolveQueueConfig(): QueueConfiguration {
    const fromConfig = this.configService?.get<QueueConfiguration>('automation.queue');
    if (fromConfig?.redisUrl) {
      return fromConfig;
    }

    const driver = (process.env.QUEUE_DRIVER as QueueConfiguration['driver']) ?? 'memory';
    const redisUrl = process.env.REDIS_URL ?? null;
    const defaultAttempts = Number.parseInt(process.env.QUEUE_MAX_ATTEMPTS ?? '3', 10);

    return {
      driver,
      redisUrl,
      defaultAttempts: Number.isFinite(defaultAttempts) ? defaultAttempts : 3
    };
  }


}
