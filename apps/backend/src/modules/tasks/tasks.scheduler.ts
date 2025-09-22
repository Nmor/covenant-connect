import { Inject, Injectable, Logger, OnModuleInit, Optional } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

import { TasksService } from './tasks.service';
import { TaskJobNames } from './task.constants';

type ScheduleConfig = {
  kpiDigestCron: string;
  followUpCron: string;
};

@Injectable()
export class TaskSchedulerService implements OnModuleInit {
  private readonly logger = new Logger(TaskSchedulerService.name);

  constructor(
    @Optional() @Inject(TasksService) private readonly tasks: TasksService | null,
    @Optional() @Inject(ConfigService) private readonly configService: ConfigService
  ) {}

  async onModuleInit(): Promise<void> {
    if (typeof this.tasks?.waitUntilReady === 'function') {
      await this.tasks.waitUntilReady();
    }

    const schedules = this.configService?.get<ScheduleConfig>('automation.schedules');
    const kpiDigestCron = schedules?.kpiDigestCron ?? '0 7 * * 1';
    const followUpCron = schedules?.followUpCron ?? '0 */6 * * *';

    await Promise.all([
      this.ensureRepeatableJob(
        TaskJobNames.ExecutiveKpiDigest,
        'executive-kpi-digest',
        kpiDigestCron,
        { rangeDays: 30 }
      ),
      this.ensureRepeatableJob(
        TaskJobNames.DepartmentKpiDigest,
        'department-kpi-digest',
        kpiDigestCron,
        { rangeDays: 30 }
      ),
      this.ensureRepeatableJob(TaskJobNames.FollowUpScan, 'automation-follow-up', followUpCron, {})
    ]);
  }

  private async ensureRepeatableJob(
    name: string,
    jobId: string,
    pattern: string,
    payload: Record<string, unknown>
  ): Promise<void> {
    const tasks = this.tasks;
    if (!tasks || typeof tasks.scheduleRepeatable !== 'function') {
      this.logger.warn(
        `TasksService is not available; skipping scheduling for repeatable job '${name}'.`
      );
      return;
    }

    try {
      await tasks.scheduleRepeatable(name, payload, { jobId, pattern });
      this.logger.debug(`Repeatable job '${name}' scheduled using pattern '${pattern}'`);
    } catch (error) {
      this.logger.error(`Failed to schedule repeatable job '${name}': ${(error as Error).message}`);
      throw error;
    }
  }
}
