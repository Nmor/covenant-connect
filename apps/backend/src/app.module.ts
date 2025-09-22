import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { TerminusModule } from '@nestjs/terminus';
import { APP_FILTER } from '@nestjs/core';

import configuration from './config/configuration';
import { automationConfig } from './config/automation.config';
import { databaseConfig } from './config/database.config';
import { healthConfig } from './config/health.config';
import { securityConfig } from './config/security.config';
import { storageConfig } from './config/storage.config';
import { PrismaModule } from './prisma/prisma.module';
import { PrismaExceptionFilter } from './common/filters/prisma-exception.filter';
import { AuthModule } from './modules/auth/auth.module';
import { ChurchesModule } from './modules/churches/churches.module';
import { ContentModule } from './modules/content/content.module';
import { DonationsModule } from './modules/donations/donations.module';
import { EmailModule } from './modules/email/email.module';
import { EventsModule } from './modules/events/events.module';
import { HealthModule } from './modules/health/health.module';
import { IntegrationsModule } from './modules/integrations/integrations.module';
import { PrayerModule } from './modules/prayer/prayer.module';
import { ReportsModule } from './modules/reports/reports.module';
import { TasksModule } from './modules/tasks/tasks.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      load: [configuration, healthConfig, securityConfig, storageConfig, automationConfig, databaseConfig]
    }),
    PrismaModule,
    TerminusModule,
    HealthModule,
    AuthModule,
    DonationsModule,
    PrayerModule,
    EventsModule,
    ReportsModule,
    ContentModule,
    ChurchesModule,
    EmailModule,
    IntegrationsModule,
    TasksModule
  ],
  providers: [
    {
      provide: APP_FILTER,
      useClass: PrismaExceptionFilter
    }
  ]
})
export class AppModule {}
