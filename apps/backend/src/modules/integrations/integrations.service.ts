import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common';
import type { IntegrationSetting } from '@covenant-connect/shared';
import { IntegrationSetting as PrismaIntegrationSetting, Prisma } from '@prisma/client';

import { PrismaService } from '../../prisma/prisma.service';

type IntegrationConfig = Record<string, unknown>;

@Injectable()
export class IntegrationsService {
  constructor(private readonly prisma: PrismaService) {}

  async create(data: { provider: string; config: IntegrationConfig }): Promise<IntegrationSetting> {
    const config = this.ensureStringRecord(data.config);

    const created = await this.prisma.integrationSetting.create({
      data: {
        provider: data.provider,
        config: config as Prisma.JsonObject
      }
    });

    return this.toShared(created);
  }

  async findAll(): Promise<IntegrationSetting[]> {
    const settings = await this.prisma.integrationSetting.findMany({
      orderBy: { provider: 'asc' }
    });

    return settings.map((setting) => this.toShared(setting));
  }

  async findOne(provider: string): Promise<IntegrationSetting> {
    const setting = await this.getByProvider(provider);
    return this.toShared(setting);
  }

  async update(
    provider: string,
    data: { provider?: string; config?: IntegrationConfig }
  ): Promise<IntegrationSetting> {
    if (data.provider === undefined && data.config === undefined) {
      throw new BadRequestException('No fields provided to update integration settings');
    }

    await this.getByProvider(provider);

    const updated = await this.prisma.integrationSetting.update({
      where: { provider },
      data: {
        provider: data.provider,
        config:
          data.config !== undefined
            ? (this.ensureStringRecord(data.config) as Prisma.JsonObject)
            : undefined
      }
    });

    return this.toShared(updated);
  }

  async remove(provider: string): Promise<void> {
    await this.getByProvider(provider);
    await this.prisma.integrationSetting.delete({ where: { provider } });
  }

  private async getByProvider(provider: string): Promise<PrismaIntegrationSetting> {
    const setting = await this.prisma.integrationSetting.findUnique({ where: { provider } });

    if (!setting) {
      throw new NotFoundException(`Integration settings for provider "${provider}" not found`);
    }

    return setting;
  }

  private ensureStringRecord(config: IntegrationConfig): Record<string, string> {
    if (config === null || typeof config !== 'object' || Array.isArray(config)) {
      throw new BadRequestException('Integration configuration must be an object of string values');
    }

    const entries = Object.entries(config);
    const sanitized: Record<string, string> = {};

    for (const [key, value] of entries) {
      if (typeof value !== 'string') {
        throw new BadRequestException('Integration configuration values must be strings');
      }

      sanitized[key] = value;
    }

    return sanitized;
  }

  private toShared(setting: PrismaIntegrationSetting): IntegrationSetting {
    return {
      id: setting.id,
      provider: setting.provider,
      config: (setting.config ?? {}) as Record<string, string>,
      createdAt: setting.createdAt,
      updatedAt: setting.updatedAt
    };
  }
}
