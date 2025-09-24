import { Injectable, NotFoundException } from '@nestjs/common';
import type { Church } from '@covenant-connect/shared';
import { Prisma } from '@prisma/client';
import type { Church as ChurchModel } from '@prisma/client';

import { PrismaService } from '../../prisma/prisma.service';

type CreateChurchInput = {
  name: string;
  timezone: string;
  address?: string | null;
  country?: string | null;
  state?: string | null;
  city?: string | null;
  settings?: Record<string, unknown> | null;
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
        address: this.toNullableString(input.address),
        country: this.toNullableString(input.country),
        state: this.toNullableString(input.state),
        city: this.toNullableString(input.city),
        settings: this.normalizeIncomingSettings(input.settings) as Prisma.InputJsonValue
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
    const church = await this.prisma.church.findUnique({ where: { id } });

    if (!church) {
      throw new NotFoundException('Church not found');
    }

    return this.toDomain(church);
  }

  async update(churchId: string, input: UpdateChurchInput): Promise<Church> {
    const id = this.parseId(churchId);
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

    if (input.address !== undefined) {
      data.address = this.toNullableString(input.address);
    }

    if (input.country !== undefined) {
      data.country = this.toNullableString(input.country);
    }

    if (input.state !== undefined) {
      data.state = this.toNullableString(input.state);
    }

    if (input.city !== undefined) {
      data.city = this.toNullableString(input.city);
    }

    if (input.settings !== undefined) {
      const mergedSettings = this.mergeSettings(existing.settings, input.settings);
      if (mergedSettings !== null) {
        data.settings = mergedSettings as Prisma.InputJsonValue;
      }
    }

    if (Object.keys(data).length === 0) {
      return this.toDomain(existing);
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
      address: this.toOptionalString(church.address),
      country: this.toOptionalString(church.country),
      state: this.toOptionalString(church.state),
      city: this.toOptionalString(church.city),
      settings: this.normalizeSettings(church.settings),
      createdAt: church.createdAt,
      updatedAt: church.updatedAt
    };
  }

  private mergeSettings(
    existing: Prisma.JsonValue | null | undefined,
    updates: unknown
  ): Record<string, unknown> | null {
    const current = this.normalizeSettings(existing);
    const incoming = this.normalizeIncomingSettings(updates);

    if (Object.keys(incoming).length === 0) {
      return null;
    }

    const merged = { ...current, ...incoming };
    return this.areSettingsEqual(current, merged) ? null : merged;
  }

  private normalizeSettings(settings: Prisma.JsonValue | null | undefined): Record<string, unknown> {
    if (!this.isPlainObject(settings)) {
      return {};
    }

    return Object.fromEntries(Object.entries(settings as Record<string, unknown>));
  }

  private normalizeIncomingSettings(settings: unknown): Record<string, unknown> {
    if (!this.isPlainObject(settings)) {
      return {};
    }

    return Object.fromEntries(Object.entries(settings as Record<string, unknown>));
  }

  private areSettingsEqual(a: Record<string, unknown>, b: Record<string, unknown>): boolean {
    const aKeys = Object.keys(a);
    const bKeys = Object.keys(b);

    if (aKeys.length !== bKeys.length) {
      return false;
    }

    return aKeys.every((key) => Object.is(a[key], b[key]));
  }

  private isPlainObject(value: unknown): value is Record<string, unknown> {
    return (
      typeof value === 'object' &&
      value !== null &&
      !Array.isArray(value) &&
      Object.prototype.toString.call(value) === '[object Object]'
    );
  }

  private toNullableString(value: string | null | undefined): string | null {
    if (value === undefined || value === null) {
      return null;
    }

    const trimmed = value.trim();
    return trimmed.length === 0 ? null : trimmed;
  }

  private toOptionalString(value: string | null | undefined): string | undefined {
    const normalized = this.toNullableString(value);
    return normalized ?? undefined;
  }

  private parseId(id: string): number {
    if (typeof id !== 'string') {
      throw new NotFoundException('Church not found');
    }

    const normalized = id.trim();
    if (normalized.length === 0 || !/^[0-9]+$/.test(normalized)) {
      throw new NotFoundException('Church not found');
    }

    const parsed = Number.parseInt(normalized, 10);
    if (!Number.isSafeInteger(parsed) || parsed <= 0) {
      throw new NotFoundException('Church not found');
    }

    return parsed;
  }
}
