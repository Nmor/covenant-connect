import { Injectable, NotFoundException } from '@nestjs/common';
import { randomUUID } from 'node:crypto';

import type { PaginatedResult, PrayerRequest } from '@covenant-connect/shared';

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
  private readonly requests = new Map<string, PrayerRequest>();

  async create(input: CreatePrayerRequestInput): Promise<PrayerRequest> {
    const now = new Date();
    const request: PrayerRequest = {
      id: randomUUID(),
      requesterName: input.requesterName,
      requesterEmail: input.requesterEmail,
      requesterPhone: input.requesterPhone,
      message: input.message,
      memberId: input.memberId,
      status: 'new',
      createdAt: now,
      updatedAt: now
    };

    this.requests.set(request.id, request);
    return request;
  }

  async list(): Promise<PaginatedResult<PrayerRequest>> {
    const data = Array.from(this.requests.values());
    return {
      data,
      total: data.length,
      page: 1,
      pageSize: data.length || 1
    };
  }

  async update(requestId: string, input: UpdatePrayerRequestInput): Promise<PrayerRequest> {
    const existing = this.requests.get(requestId);
    if (!existing) {
      throw new NotFoundException('Prayer request not found');
    }

    const updated: PrayerRequest = {
      ...existing,
      ...input,
      updatedAt: new Date()
    };

    this.requests.set(updated.id, updated);
    return updated;
  }
}
