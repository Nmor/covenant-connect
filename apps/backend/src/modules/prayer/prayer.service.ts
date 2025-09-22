import { Injectable, NotFoundException } from '@nestjs/common';
import type { PrayerRequest as PrayerRequestModel } from '@prisma/client';
import type { PaginatedResult, PrayerRequest } from '@covenant-connect/shared';

import { PrismaService } from '../../prisma/prisma.service';

type CreatePrayerRequestInput = {
  requesterName: string;
  requesterEmail?: string;
  requesterPhone?: string;
  message: string;
  memberId?: string;
};

type UpdatePrayerRequestInput = Partial<Pick<PrayerRequest, 'status' | 'followUpAt'>>;

@Injectable()
export class PrayerService {
  constructor(private readonly prisma: PrismaService) {}

  async create(input: CreatePrayerRequestInput): Promise<PrayerRequest> {
    const created = await this.prisma.prayerRequest.create({
      data: {
        requesterName: input.requesterName,
        requesterEmail: input.requesterEmail,
        requesterPhone: input.requesterPhone,
        message: input.message,
        memberId: input.memberId ?? null
      }
    });

    return this.toDomain(created);
  }

  async list(): Promise<PaginatedResult<PrayerRequest>> {
    const [requests, total] = await this.prisma.$transaction([
      this.prisma.prayerRequest.findMany({ orderBy: { createdAt: 'desc' } }),
      this.prisma.prayerRequest.count()
    ]);

    return {
      data: requests.map((request) => this.toDomain(request)),
      total,
      page: 1,
      pageSize: total || 1
    };
  }

  async update(requestId: string, input: UpdatePrayerRequestInput): Promise<PrayerRequest> {
    const existing = await this.prisma.prayerRequest.findUnique({
      where: { id: this.parseId(requestId) }
    });
    if (!existing) {
      throw new NotFoundException('Prayer request not found');
    }

    const updated = await this.prisma.prayerRequest.update({
      where: { id: existing.id },
      data: {
        status: input.status ?? existing.status,
        followUpAt: input.followUpAt ?? existing.followUpAt
      }
    });

    return this.toDomain(updated);
  }

  private toDomain(model: PrayerRequestModel): PrayerRequest {
    return {
      id: model.id.toString(),
      requesterName: model.requesterName,
      requesterEmail: model.requesterEmail ?? undefined,
      requesterPhone: model.requesterPhone ?? undefined,
      message: model.message,
      memberId: model.memberId ?? undefined,
      status: model.status as PrayerRequest['status'],
      followUpAt: model.followUpAt ?? undefined,
      createdAt: model.createdAt,
      updatedAt: model.updatedAt
    };
  }

  private parseId(id: string): number {
    const parsed = Number.parseInt(id, 10);
    if (Number.isNaN(parsed)) {
      throw new NotFoundException('Prayer request not found');
    }

    return parsed;
  }
}
