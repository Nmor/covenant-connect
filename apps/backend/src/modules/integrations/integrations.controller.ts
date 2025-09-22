import { Body, Controller, Get, Put } from '@nestjs/common';
import type { IntegrationSettings } from '@covenant-connect/shared';

import { IntegrationsService } from './integrations.service';

@Controller('integrations')
export class IntegrationsController {
  constructor(private readonly integrations: IntegrationsService) {}

  @Get()
  get(): Promise<IntegrationSettings> {
    return this.integrations.get();
  }

  @Put()
  update(@Body() body: IntegrationSettings): Promise<IntegrationSettings> {
    return this.integrations.update(body);
  }
}
