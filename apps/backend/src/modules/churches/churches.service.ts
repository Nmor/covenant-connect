import { Injectable, NotFoundException } from '@nestjs/common';
import type { Church } from '@covenant-connect/shared';
import { Prisma } from '@prisma/client';
import type { Church as ChurchModel } from '@prisma/client';

import { PrismaService } from '../../prisma/prisma.service';

type CreateChurchInput = {
  name: string;
  timezone: string;
  country?: string | null;
  state?: string | null;
  city?: string | null;
  settings?: Record<string, unknown>;
};

type UpdateChurchInput = Partial<CreateChurchInput>;

@Injectable()
export class ChurchesService {
  constructor(private readonly prisma: PrismaService) {}

  async create(input: CreateChurchInput): Promise<Church> {
    const created = await this.prisma.church.create({
      data: {
        name: input.name,
        timezone: input.timezone,
        country: input.country ?? null,
        state: input.state ?? null,
        city: input.city ?? null,
        settings: (input.settings ?? {}) as Prisma.InputJsonValue
      }
    });

    return this.toDomain(created);
  }

  async list(): Promise<Church[]> {
    const churches = await this.prisma.church.findMany({
      orderBy: { createdAt: 'asc' }
    });

    return churches.map((church) => this.toDomain(church));
  }

  async getById(churchId: string): Promise<Church> {
    const id = this.parseId(churchId);
    if (id === null) {
      throw new NotFoundException('Church not found');
    }

    const church = await this.prisma.church.findUnique({ where: { id } });
    if (!church) {
      throw new NotFoundException('Church not found');
    }

    return this.toDomain(church);
  }

  async update(churchId: string, input: UpdateChurchInput): Promise<Church> {
    const id = this.parseId(churchId);
    if (id === null) {
      throw new NotFoundException('Church not found');
    }

    const existing = await this.prisma.church.findUnique({ where: { id } });
    if (!existing) {
      throw new NotFoundException('Church not found');
    }

    const data: Prisma.ChurchUpdateInput = {};

    if (input.name !== undefined) {
      data.name = input.name;
    }

    if (input.timezone !== undefined) {
      data.timezone = input.timezone;
    }

    if (input.country !== undefined) {
      data.country = input.country ?? null;
    }

    if (input.state !== undefined) {
      data.state = input.state ?? null;
    }

    if (input.city !== undefined) {
      data.city = input.city ?? null;
    }

    if (input.settings !== undefined) {
      const mergedSettings = {
        ...this.normalizeSettings(existing.settings),
        ...input.settings
      };

      data.settings = mergedSettings as Prisma.InputJsonValue;
    }

    const updated = await this.prisma.church.update({
      where: { id },
      data
    });

    return this.toDomain(updated);
  }

  private toDomain(church: ChurchModel): Church {
    return {
      id: church.id.toString(),
      name: church.name,
      timezone: church.timezone,
      country: church.country ?? undefined,
      state: church.state ?? undefined,
      city: church.city ?? undefined,
      settings: this.normalizeSettings(church.settings),
      createdAt: church.createdAt,
      updatedAt: church.updatedAt
    };
  }

  private normalizeSettings(settings: Prisma.JsonValue | null | undefined): Record<string, unknown> {
    if (!settings || Array.isArray(settings) || typeof settings !== 'object') {
      return {};
    }

    return settings as Record<string, unknown>;
  }

  private parseId(id: string): number | null {
    const parsed = Number.parseInt(id, 10);
    if (Number.isNaN(parsed)) {
      return null;
    }

    return parsed;
  }
}
