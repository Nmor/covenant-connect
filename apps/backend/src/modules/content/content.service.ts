import { BadRequestException, Injectable } from '@nestjs/common';
import type { HomeContent, PaginatedResult, Pagination, Sermon } from '@covenant-connect/shared';

import { PrismaService } from '../../prisma/prisma.service';

type CreateSermonInput = {
  title: string;
  description?: string | null;
  preacher?: string | null;
  date?: Date | null;
  mediaUrl?: string | null;
  mediaType?: string | null;
};

@Injectable()
export class ContentService {
  constructor(private readonly prisma: PrismaService) {}

  private homeContent: HomeContent = {
    heroTitle: 'Plan services and care pathways with ease',
    heroSubtitle:
      'The TypeScript rewrite ships with modular services for worship planning, assimilation, and giving.',
    highlights: [
      'Blueprint new gatherings with volunteer roles in minutes',
      'Automate next steps for guests and returning members',
      'Connect giving, pastoral care, and communications in one place'
    ],
    nextSteps: [
      { label: 'Launch admin console', url: '/dashboard' },
      { label: 'Browse events calendar', url: '/events' },
      { label: 'Review giving activity', url: '/donations' },
      { label: 'Manage prayer follow-up', url: '/prayer' },
      { label: 'Review API docs', url: '/docs' },
      { label: 'Explore product updates', url: '/changelog' }
    ]
  };

  async getHome(): Promise<HomeContent> {
    return this.homeContent;
  }

  async updateHome(content: Partial<HomeContent>): Promise<HomeContent> {
    this.homeContent = { ...this.homeContent, ...content };
    return this.homeContent;
  }

  async listSermons(pagination: Pagination = { page: 1, pageSize: 25 }): Promise<PaginatedResult<Sermon>> {
    const page = this.normalizePage(pagination.page);
    const pageSize = this.normalizePageSize(pagination.pageSize);
    const skip = (page - 1) * pageSize;

    const [records, total] = await Promise.all([
      this.prisma.sermon.findMany({
        skip,
        take: pageSize,
        orderBy: { date: 'desc' }
      }),
      this.prisma.sermon.count()
    ]);

    return {
      data: records,
      total,
      page,
      pageSize
    };
  }

  async addSermon(input: CreateSermonInput): Promise<Sermon> {
    const created = await this.prisma.sermon.create({
      data: {
        title: this.requireTitle(input.title),
        description: this.optionalString(input.description),
        preacher: this.optionalString(input.preacher),
        date: this.normalizeDate(input.date),
        mediaUrl: this.optionalString(input.mediaUrl),
        mediaType: this.optionalString(input.mediaType)
      }
    });

    return created;
  }

  private requireTitle(title: string): string {
    const normalized = this.optionalString(title);
    if (!normalized) {
      throw new BadRequestException('Title is required');
    }

    return normalized;
  }

  private optionalString(value: string | null | undefined): string | null {
    if (value === undefined || value === null) {
      return null;
    }

    const trimmed = value.trim();
    return trimmed.length === 0 ? null : trimmed;
  }

  private normalizeDate(value: Date | null | undefined): Date {
    if (value instanceof Date && !Number.isNaN(value.getTime())) {
      return value;
    }

    return new Date();
  }

  private normalizePage(page: number | undefined): number {
    if (typeof page !== 'number' || !Number.isFinite(page)) {
      return 1;
    }

    const normalized = Math.trunc(page);
    return normalized > 0 ? normalized : 1;
  }

  private normalizePageSize(pageSize: number | undefined): number {
    if (typeof pageSize !== 'number' || !Number.isFinite(pageSize)) {
      return 25;
    }

    const normalized = Math.trunc(pageSize);
    if (normalized <= 0) {
      return 25;
    }

    return Math.min(normalized, 100);
  }
}
