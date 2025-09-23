import { afterEach, beforeEach, describe, expect, it, jest } from '@jest/globals';
import { NotFoundException } from '@nestjs/common';
import type { Church as PrismaChurch } from '@prisma/client';

import { ChurchesService } from './churches.service';
import type { PrismaService } from '../../prisma/prisma.service';

type ChurchRecord = {
  id: number;
  name: string;
  address: string | null;
  timezone: string;
  country: string | null;
  state: string | null;
  city: string | null;
  settings: Record<string, unknown>;
  createdAt: Date;
  updatedAt: Date;
};

class InMemoryPrismaService {
  private sequence = 1;
  private readonly churches: ChurchRecord[] = [];
  private timestamp = 1_000;

  public readonly church = {
    create: jest.fn(async ({ data }: { data: Record<string, unknown> }) => this.createChurch(data)),
    findMany: jest.fn(async ({ orderBy }: { orderBy?: { createdAt?: 'asc' | 'desc' } } = {}) =>
      this.findManyChurches(orderBy)
    ),
    findUnique: jest.fn(async ({ where }: { where: { id: number | string } }) =>
      this.findUniqueChurch(where.id)
    ),
    update: jest.fn(async ({
      where,
      data,
    }: {
      where: { id: number | string };
      data: Record<string, unknown>;
    }) => this.updateChurch(where.id, data)),
  };

  private async createChurch(data: Record<string, unknown>): Promise<PrismaChurch> {
    const now = this.nextTimestamp();

    const record: ChurchRecord = {
      id: this.sequence++,
      name: (data.name as string) ?? 'Unnamed Church',
      address: (data.address as string | null | undefined) ?? null,
      timezone: (data.timezone as string) ?? 'UTC',
      country: (data.country as string | null | undefined) ?? null,
      state: (data.state as string | null | undefined) ?? null,
      city: (data.city as string | null | undefined) ?? null,
      settings: this.cloneSettings(data.settings),
      createdAt: now,
      updatedAt: now,
    };

    this.churches.push(record);
    return this.toModel(this.cloneRecord(record));
  }

  private async findManyChurches(orderBy?: { createdAt?: 'asc' | 'desc' }): Promise<PrismaChurch[]> {
    const sorted = [...this.churches];

    if (orderBy?.createdAt === 'asc') {
      sorted.sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime());
    } else if (orderBy?.createdAt === 'desc') {
      sorted.sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
    }

    return sorted.map((record) => this.toModel(this.cloneRecord(record)));
  }

  private async findUniqueChurch(id: number | string): Promise<PrismaChurch | null> {
    const numericId = typeof id === 'number' ? id : Number.parseInt(id, 10);
    if (!Number.isInteger(numericId)) {
      return null;
    }

    const record = this.churches.find((entry) => entry.id === numericId);
    return record ? this.toModel(this.cloneRecord(record)) : null;
  }

  private async updateChurch(id: number | string, data: Record<string, unknown>): Promise<PrismaChurch> {
    const numericId = typeof id === 'number' ? id : Number.parseInt(id, 10);
    const record = this.churches.find((entry) => entry.id === numericId);

    if (!record) {
      throw new Error('Church not found');
    }

    if (data.name !== undefined) {
      record.name = data.name as string;
    }
    if (data.timezone !== undefined) {
      record.timezone = data.timezone as string;
    }
    if (data.country !== undefined) {
      record.country = (data.country as string | null | undefined) ?? null;
    }
    if (data.state !== undefined) {
      record.state = (data.state as string | null | undefined) ?? null;
    }
    if (data.city !== undefined) {
      record.city = (data.city as string | null | undefined) ?? null;
    }
    if (data.settings !== undefined) {
      record.settings = this.cloneSettings(data.settings);
    }

    record.updatedAt = this.nextTimestamp();
    return this.toModel(this.cloneRecord(record));
  }

  private cloneRecord(record: ChurchRecord): ChurchRecord {
    return {
      ...record,
      settings: { ...record.settings },
      createdAt: new Date(record.createdAt.getTime()),
      updatedAt: new Date(record.updatedAt.getTime()),
    };
  }

  private cloneSettings(value: unknown): Record<string, unknown> {
    if (
      typeof value !== 'object' ||
      value === null ||
      Array.isArray(value) ||
      Object.prototype.toString.call(value) !== '[object Object]'
    ) {
      return {};
    }

    return Object.fromEntries(Object.entries(value as Record<string, unknown>));
  }

  private nextTimestamp(): Date {
    return new Date(this.timestamp++);
  }

  private toModel(record: ChurchRecord): PrismaChurch {
    return {
      id: record.id,
      name: record.name,
      address: record.address,
      timezone: record.timezone,
      country: record.country,
      state: record.state,
      city: record.city,
      settings: record.settings,
      createdAt: record.createdAt,
      updatedAt: record.updatedAt,
    } as PrismaChurch;
  }
}

describe('ChurchesService', () => {
  let prisma: InMemoryPrismaService;
  let service: ChurchesService;

  beforeEach(() => {
    prisma = new InMemoryPrismaService();
    service = new ChurchesService(prisma as unknown as PrismaService);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('creates a church and normalizes optional values', async () => {
    const church = await service.create({
      name: 'Grace Chapel',
      timezone: 'America/New_York',
      country: ' US ',
      state: '',
      city: '  ',
      settings: { theme: 'light' },
    });

    expect(church).toMatchObject({
      id: '1',
      name: 'Grace Chapel',
      timezone: 'America/New_York',
      country: 'US',
      state: undefined,
      city: undefined,
      settings: { theme: 'light' },
    });
  });

  it('coerces non-object settings into an empty record on create', async () => {
    const church = await service.create({
      name: 'Community Church',
      timezone: 'UTC',
      settings: [] as unknown as Record<string, unknown>,
    });

    expect(church.settings).toEqual({});
  });

  it('lists churches ordered by creation time', async () => {
    const first = await service.create({ name: 'First Church', timezone: 'UTC' });
    const second = await service.create({ name: 'Second Church', timezone: 'UTC' });

    const churches = await service.list();

    expect(churches.map((entry) => entry.id)).toEqual([first.id, second.id]);
  });

  it('throws when requesting a church with a non-numeric identifier', async () => {
    await service.create({ name: 'First Church', timezone: 'UTC' });

    await expect(service.getById('abc')).rejects.toThrow(NotFoundException);
    await expect(service.getById('1abc')).rejects.toThrow(NotFoundException);
  });

  it('updates a church and merges settings', async () => {
    const created = await service.create({
      name: 'Hope Church',
      timezone: 'UTC',
      country: 'US',
      settings: { theme: 'light', donations: true },
    });

    const updated = await service.update(created.id, {
      timezone: 'Africa/Lagos',
      country: '  ',
      settings: { theme: 'dark', announcements: true },
    });

    expect(updated).toMatchObject({
      timezone: 'Africa/Lagos',
      country: undefined,
      settings: {
        theme: 'dark',
        donations: true,
        announcements: true,
      },
    });
  });

  it('returns the existing church when no updates are provided', async () => {
    const created = await service.create({ name: 'Stillwater Church', timezone: 'UTC' });

    prisma.church.update.mockClear();

    const result = await service.update(created.id, {});

    expect(result).toEqual(created);
    expect(prisma.church.update).not.toHaveBeenCalled();
  });

  it('ignores settings updates that cannot be merged', async () => {
    const created = await service.create({
      name: 'River Church',
      timezone: 'UTC',
      settings: { theme: 'light' },
    });

    prisma.church.update.mockClear();

    const result = await service.update(created.id, { settings: null });

    expect(result).toEqual(created);
    expect(prisma.church.update).not.toHaveBeenCalled();
  });

  it('throws when attempting to update a missing church', async () => {
    await expect(service.update('999', { name: 'Missing Church' })).rejects.toThrow(NotFoundException);
  });
});
