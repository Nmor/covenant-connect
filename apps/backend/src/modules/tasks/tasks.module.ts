import { Module } from '@nestjs/common';

import { PrismaModule } from '../../prisma/prisma.module';
import { EmailModule } from '../email/email.module';

import { TasksController } from './tasks.controller';
import { TasksService } from './tasks.service';
import { TaskWorkerService } from './tasks.worker';
import { PrayerNotificationService } from './workers/prayer-notification.service';
import { KpiDigestService } from './workers/kpi-digest.service';
import { AutomationService } from './workers/automation.service';
import { TaskSchedulerService } from './tasks.scheduler';

@Module({
  imports: [PrismaModule, EmailModule],
  controllers: [TasksController],
  providers: [
    TasksService,
    TaskWorkerService,
    PrayerNotificationService,
    KpiDigestService,
    AutomationService,
    TaskSchedulerService
  ],
  exports: [TasksService, AutomationService]
})
export class TasksModule {}
