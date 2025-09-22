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

  constructor() {
    this.seedSampleRequests();
  }

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

  private seedSampleRequests(): void {
    if (this.requests.size > 0) {
      return;
    }

    const now = new Date();
    const seeds: Array<{
      requesterName: string;
      requesterEmail: string;
      message: string;
      status: PrayerRequest['status'];
      submittedHoursAgo: number;
      followUpInHours?: number;
      memberId?: string;
    }> = [
      {
        requesterName: 'Sarah Johnson',
        requesterEmail: 'sarah.j@example.com',
        message: "Please pray for my mother's recovery after surgery this week.",
        status: 'assigned',
        submittedHoursAgo: 20,
        followUpInHours: 28,
        memberId: 'member-johnson'
      },
      {
        requesterName: 'Michael Chen',
        requesterEmail: 'michael.chen@example.com',
        message: 'Seeking wisdom as I make a career transition into ministry leadership.',
        status: 'praying',
        submittedHoursAgo: 48,
        followUpInHours: 12
      },
      {
        requesterName: 'Emily Williams',
        requesterEmail: 'emily.w@example.com',
        message: 'Pray for unity and grace in our family relationships.',
        status: 'new',
        submittedHoursAgo: 5
      },
      {
        requesterName: 'David Thompson',
        requesterEmail: 'david.t@example.com',
        message: 'Praise report: our outreach saw two salvations last weekend!',
        status: 'answered',
        submittedHoursAgo: 96
      }
    ];

    for (const seed of seeds) {
      const createdAt = new Date(now.getTime() - seed.submittedHoursAgo * 60 * 60 * 1000);
      const followUpAt = seed.followUpInHours
        ? new Date(now.getTime() + seed.followUpInHours * 60 * 60 * 1000)
        : undefined;

      const request: PrayerRequest = {
        id: randomUUID(),
        requesterName: seed.requesterName,
        requesterEmail: seed.requesterEmail,
        message: seed.message,
        requesterPhone: undefined,
        memberId: seed.memberId,
        status: seed.status,
        followUpAt,
        createdAt,
        updatedAt: createdAt
      };

      this.requests.set(request.id, request);
    }
  }
}
