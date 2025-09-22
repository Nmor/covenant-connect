import { Inject, Injectable, Logger, OnModuleDestroy, OnModuleInit, Optional } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import type { Job } from 'bullmq';
import { Worker } from 'bullmq';
import type { Redis } from 'ioredis';
import IORedis from 'ioredis';

import { TASK_QUEUE_NAME, TaskJobNames } from './task.constants';
import { TasksService } from './tasks.service';
import { PrayerNotificationService } from './workers/prayer-notification.service';
import { KpiDigestService } from './workers/kpi-digest.service';
import { AutomationService } from './workers/automation.service';

type WorkerJob = Job<Record<string, unknown>>;

@Injectable()
export class TaskWorkerService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(TaskWorkerService.name);
  private worker: Worker | null = null;

  constructor(
    @Inject(TasksService) private readonly tasks: TasksService,
    @Inject(PrayerNotificationService) private readonly prayerNotifications: PrayerNotificationService,
    @Inject(KpiDigestService) private readonly kpiDigests: KpiDigestService,
    @Inject(AutomationService) private readonly automations: AutomationService,
    @Optional() @Inject(ConfigService) private readonly configService: ConfigService
  ) {}

  async onModuleInit(): Promise<void> {
    if (typeof this.tasks?.waitUntilReady === 'function') {
      await this.tasks.waitUntilReady();
    }

    const connection = this.createWorkerConnection();

    this.worker = new Worker(
      TASK_QUEUE_NAME,
      async (job) => this.handleJob(job as WorkerJob),
      {
        connection,
        concurrency: 5
      }
    );

    this.worker.on('completed', (job) => {
      this.logger.debug(`Completed job ${job.id ?? job.name} (${job.name})`);
    });

    this.worker.on('failed', (job, error) => {
      if (!job) {
        this.logger.error('Task worker encountered an error without job context', error as Error);
        return;
      }
      this.logger.error(
        `Job ${job.id ?? job.name} (${job.name}) failed: ${(error as Error)?.message}`,
        error as Error
      );
    });
  }

  async onModuleDestroy(): Promise<void> {
    if (this.worker) {
      await this.worker.close();
      this.worker = null;
    }
  }

  private createWorkerConnection(): Redis {
    if (typeof this.tasks?.createClient === 'function') {
      return this.tasks.createClient();
    }

    const queueConfig = this.configService?.get<{ redisUrl: string | null }>('automation.queue');
    const redisUrl = queueConfig?.redisUrl ?? process.env.REDIS_URL;
    if (!redisUrl) {
      throw new Error('Redis connection configuration is required for task workers');
    }

    return new IORedis(redisUrl, {
      maxRetriesPerRequest: null,
      enableReadyCheck: false
    });
  }

  private async handleJob(job: WorkerJob): Promise<void> {
    switch (job.name) {
      case TaskJobNames.SendPrayerNotification:
        await this.prayerNotifications.notifyAdmins(job.data?.prayerRequestId);
        break;
      case TaskJobNames.DepartmentKpiDigest:
        await this.kpiDigests.sendDepartmentDigest(this.resolveRange(job.data));
        break;
      case TaskJobNames.ExecutiveKpiDigest:
        await this.kpiDigests.sendExecutiveDigest(this.resolveRange(job.data));
        break;
      case TaskJobNames.RunAutomations:
        await this.automations.runAutomationsForIds(
          this.normaliseIdArray(job.data?.automationIds),
          this.normaliseContext(job.data?.context),
          this.normaliseTrigger(job.data?.trigger)
        );
        break;
      case TaskJobNames.ExecuteAutomationStep:
        await this.automations.executeStep(
          this.normaliseId(job.data?.stepId),
          this.normaliseContext(job.data?.context),
          this.normaliseTrigger(job.data?.trigger)
        );
        break;
      case TaskJobNames.FollowUpScan:
        await this.automations.triggerFollowUp(this.normaliseContext(job.data?.context));
        break;
      default:
        this.logger.warn(`Received job for unknown task: ${job.name}`);
    }
  }

  private resolveRange(data: Record<string, unknown> | undefined): number {
    if (!data) {
      return 30;
    }
    const value = data.rangeDays;
    const parsed = typeof value === 'string' ? Number.parseInt(value, 10) : Number(value);
    if (Number.isFinite(parsed) && parsed > 0) {
      return parsed;
    }
    return 30;
  }

  private normaliseId(value: unknown): number {
    const parsed = typeof value === 'string' ? Number.parseInt(value, 10) : Number(value);
    if (!Number.isFinite(parsed)) {
      throw new Error(`Unable to parse identifier from value: ${String(value)}`);
    }
    return parsed;
  }

  private normaliseIdArray(values: unknown): number[] {
    if (!Array.isArray(values)) {
      return [];
    }
    return values
      .map((value) => {
        try {
          return this.normaliseId(value);
        } catch (error) {
          this.logger.warn(`Skipping invalid automation identifier: ${String(value)}`);
          return null;
        }
      })
      .filter((value): value is number => value !== null);
  }

  private normaliseTrigger(value: unknown): string | undefined {
    return typeof value === 'string' && value ? value : undefined;
  }

  private normaliseContext(value: unknown): Record<string, unknown> {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return { ...(value as Record<string, unknown>) };
    }
    return {};
  }
}
