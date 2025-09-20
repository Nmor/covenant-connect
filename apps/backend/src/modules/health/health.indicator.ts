import { Injectable } from '@nestjs/common';
import { HealthIndicator, HealthIndicatorFunction } from '@nestjs/terminus';

@Injectable()
export class HealthIndicatorService extends HealthIndicator {
  isAlive: HealthIndicatorFunction = async () => {
    return this.getStatus('api', true);
  };

  isReady: HealthIndicatorFunction = async () => {
    // TODO: add datastore and queue probes when wiring infrastructure.
    return this.getStatus('dependencies', true);
  };
}
