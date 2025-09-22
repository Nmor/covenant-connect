import { Body, Controller, Delete, Get, Param, Post, Put } from '@nestjs/common';
import type { IntegrationSetting } from '@covenant-connect/shared';

import { IntegrationsService } from './integrations.service';
import { CreateIntegrationSettingDto } from './dto/create-integration-setting.dto';
import { UpdateIntegrationSettingDto } from './dto/update-integration-setting.dto';

@Controller('integrations')
export class IntegrationsController {
  constructor(private readonly integrations: IntegrationsService) {}

  @Get()
  list(): Promise<IntegrationSetting[]> {
    return this.integrations.findAll();
  }

  @Get(':provider')
  get(@Param('provider') provider: string): Promise<IntegrationSetting> {
    return this.integrations.findOne(provider);
  }

  @Post()
  create(@Body() body: CreateIntegrationSettingDto): Promise<IntegrationSetting> {
    return this.integrations.create(body);
  }

  @Put(':provider')
  update(
    @Param('provider') provider: string,
    @Body() body: UpdateIntegrationSettingDto
  ): Promise<IntegrationSetting> {
    return this.integrations.update(provider, body);
  }

  @Delete(':provider')
  remove(@Param('provider') provider: string): Promise<void> {
    return this.integrations.remove(provider);
  }
}
