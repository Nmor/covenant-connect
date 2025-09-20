import { Injectable } from '@nestjs/common';

import type { IntegrationSettings } from '@covenant-connect/shared';

@Injectable()
export class IntegrationsService {
  private settings: IntegrationSettings = {};

  async get(): Promise<IntegrationSettings> {
    return this.settings;
  }

  async update(settings: IntegrationSettings): Promise<IntegrationSettings> {
    this.settings = { ...this.settings, ...settings };
    return this.settings;
  }
}
