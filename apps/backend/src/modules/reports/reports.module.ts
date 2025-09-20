import { Module } from '@nestjs/common';

import { DonationsModule } from '../donations/donations.module';
import { EventsModule } from '../events/events.module';
import { PrayerModule } from '../prayer/prayer.module';
import { ReportsController } from './reports.controller';
import { ReportsService } from './reports.service';

@Module({
  imports: [DonationsModule, EventsModule, PrayerModule],
  controllers: [ReportsController],
  providers: [ReportsService]
})
export class ReportsModule {}
