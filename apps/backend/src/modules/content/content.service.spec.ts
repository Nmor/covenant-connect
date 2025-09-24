import { BadRequestException } from '@nestjs/common';
import type { Sermon as PrismaSermon } from '@prisma/client';

import { ContentService } from './content.service';
import type { PrismaService } from '../../prisma/prisma.service';

class InMemoryPrismaService {
  private sequence = 1;
  private readonly sermons: SermonRecord[] = [];

  public readonly sermon = {
    findMany: jest.fn(
      async (
        params: {
          skip?: number;
          take?: number;
          orderBy?: { date?: 'asc' | 'desc' };
        } = {}
      ) => this.findMany(params)
    ),
    count: jest.fn(async () => this.sermons.length),
    create: jest.fn(async ({ data }: { data: Record<string, unknown> }) => this.create(data))
  };

  private async findMany(params: {
    skip?: number;
    take?: number;
    orderBy?: { date?: 'asc' | 'desc' };
  }): Promise<PrismaSermon[]> {
    const skip = params.skip ?? 0;
    const take = params.take ?? this.sermons.length;
    const orderBy = params.orderBy;

    const sorted = [...this.sermons];
    if (orderBy?.date === 'asc') {
      sorted.sort((a, b) => a.date.getTime() - b.date.getTime());
    } else if (orderBy?.date === 'desc') {
      sorted.sort((a, b) => b.date.getTime() - a.date.getTime());
    }

    const slice = sorted.slice(skip, take ? skip + take : undefined);
    return slice.map((record) => this.toModel(this.cloneRecord(record)));
  }

  private async create(data: Record<string, unknown>): Promise<PrismaSermon> {
    const record: SermonRecord = {
      id: this.sequence++,
      title: (data.title as string) ?? 'Untitled Sermon',
      description: (data.description as string | null | undefined) ?? null,
      preacher: (data.preacher as string | null | undefined) ?? null,
      date: this.normalizeDate(data.date),
      mediaUrl: (data.mediaUrl as string | null | undefined) ?? null,
      mediaType: (data.mediaType as string | null | undefined) ?? null
    };

    this.sermons.push(record);
    return this.toModel(this.cloneRecord(record));
  }

  private normalizeDate(value: unknown): Date {
    if (value instanceof Date && !Number.isNaN(value.getTime())) {
      return new Date(value.getTime());
    }

    const parsed = typeof value === 'string' ? new Date(value) : null;
    if (parsed && !Number.isNaN(parsed.getTime())) {
      return parsed;
    }

    return new Date();
  }

  private toModel(record: SermonRecord): PrismaSermon {
    return {
      id: record.id,
      title: record.title,
      description: record.description,
      preacher: record.preacher,
      date: record.date,
      mediaUrl: record.mediaUrl,
      mediaType: record.mediaType
    };
  }

  private cloneRecord(record: SermonRecord): SermonRecord {
    return {
      ...record,
      date: new Date(record.date.getTime())
    };
  }
}

type SermonRecord = {
  id: number;
  title: string;
  description: string | null;
  preacher: string | null;
  date: Date;
  mediaUrl: string | null;
  mediaType: string | null;
};

describe('ContentService', () => {
  let prisma: InMemoryPrismaService;
  let service: ContentService;

  beforeEach(() => {
    prisma = new InMemoryPrismaService();
    service = new ContentService(prisma as unknown as PrismaService);
  });

  it('returns paginated sermons sorted by most recent date', async () => {
    const older = await service.addSermon({
      title: 'Legacy Faithfulness',
      date: new Date('2023-01-01T10:00:00Z'),
      preacher: 'Rev. Grace',
      mediaType: 'video',
      mediaUrl: 'https://example.com/legacy'
    });

    const newer = await service.addSermon({
      title: 'Renewed Hope',
      date: new Date('2024-05-10T09:30:00Z'),
      preacher: 'Pastor Daniel'
    });

    const result = await service.listSermons({ page: 1, pageSize: 1 });

    expect(result.total).toBe(2);
    expect(result.page).toBe(1);
    expect(result.pageSize).toBe(1);
    expect(result.data).toHaveLength(1);
    expect(result.data[0].id).toBe(newer.id);
    expect(result.data[0].title).toBe('Renewed Hope');

    const secondPage = await service.listSermons({ page: 2, pageSize: 1 });
    expect(secondPage.data[0].id).toBe(older.id);
  });

  it('trims optional strings and defaults missing values when creating sermons', async () => {
    const created = await service.addSermon({
      title: '  Hope Restored  ',
      preacher: '  Pastor Micah  ',
      description: '\nA message of renewal.\n',
      mediaUrl: '   ',
      mediaType: undefined,
      date: undefined
    });

    expect(created.title).toBe('Hope Restored');
    expect(created.preacher).toBe('Pastor Micah');
    expect(created.description).toBe('A message of renewal.');
    expect(created.mediaUrl).toBeNull();
    expect(created.mediaType).toBeNull();
    expect(created.date instanceof Date).toBe(true);
  });

  it('sanitizes invalid pagination input', async () => {
    await service.addSermon({ title: 'First Sermon' });

    const result = await service.listSermons({
      page: Number.NaN,
      pageSize: 500
    });

    expect(result.page).toBe(1);
    expect(result.pageSize).toBe(100);
    expect(result.total).toBe(1);
  });

  it('rejects attempts to create sermons without a valid title', async () => {
    await expect(
      service.addSermon({
        title: '   ',
        preacher: 'Pastor Lee'
      })
    ).rejects.toBeInstanceOf(BadRequestException);
  });
});
