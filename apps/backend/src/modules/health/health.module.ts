import { Module } from '@nestjs/common';
import { TerminusModule } from '@nestjs/terminus';

import { HealthController } from './health.controller';
import { HealthIndicatorService } from './health.indicator';

@Module({
  imports: [TerminusModule],
  controllers: [HealthController],
  providers: [HealthIndicatorService]
})
export class HealthModule {}
