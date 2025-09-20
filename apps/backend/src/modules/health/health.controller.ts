import { Controller, Get } from '@nestjs/common';
import {
  HealthCheck,
  HealthCheckResult,
  HealthCheckService
} from '@nestjs/terminus';

import { HealthIndicatorService } from './health.indicator';

@Controller('health')
export class HealthController {
  constructor(
    private readonly health: HealthCheckService,
    private readonly indicatorService: HealthIndicatorService
  ) {}

  @Get('live')
  @HealthCheck()
  checkLiveness(): Promise<HealthCheckResult> {
    return this.health.check([this.indicatorService.isAlive]);
  }

  @Get('ready')
  @HealthCheck()
  checkReadiness(): Promise<HealthCheckResult> {
    return this.health.check([this.indicatorService.isReady]);
  }
}
