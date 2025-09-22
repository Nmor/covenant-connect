import { Injectable, NotFoundException } from '@nestjs/common';
import { randomUUID } from 'node:crypto';
import type { Donation, PaginatedResult, Pagination } from '@covenant-connect/shared';

type CreateDonationInput = {
  memberId?: string | null;
  amount: number;
  currency: string;
  provider: Donation['provider'];
  metadata?: Record<string, unknown>;
};

type UpdateDonationStatusInput = {
  status: Donation['status'];
  metadata?: Record<string, unknown>;
};

@Injectable()
export class DonationsService {
  private readonly donations = new Map<string, Donation>();

  constructor() {
    this.seedSampleDonations();
  }

  async list(pagination: Pagination): Promise<PaginatedResult<Donation>> {
    const data = Array.from(this.donations.values());
    const start = (pagination.page - 1) * pagination.pageSize;
    const end = start + pagination.pageSize;

    return {
      data: data.slice(start, end),
      total: data.length,
      page: pagination.page,
      pageSize: pagination.pageSize
    };
  }

  async create(input: CreateDonationInput): Promise<Donation> {
    const now = new Date();
    const donation: Donation = {
      id: randomUUID(),
      memberId: input.memberId ?? null,
      amount: input.amount,
      currency: input.currency,
      provider: input.provider,
      status: 'pending',
      metadata: input.metadata ?? {},
      createdAt: now,
      updatedAt: now
    };

    this.donations.set(donation.id, donation);
    return donation;
  }

  async updateStatus(donationId: string, input: UpdateDonationStatusInput): Promise<Donation> {
    const existing = this.donations.get(donationId);
    if (!existing) {
      throw new NotFoundException('Donation not found');
    }

    const updated: Donation = {
      ...existing,
      status: input.status,
      metadata: { ...existing.metadata, ...(input.metadata ?? {}) },
      updatedAt: new Date()
    };

    this.donations.set(updated.id, updated);
    return updated;
  }

  private seedSampleDonations(): void {
    if (this.donations.size > 0) {
      return;
    }

    const now = new Date();
    const seeds: Array<{
      amount: number;
      currency: string;
      provider: Donation['provider'];
      status: Donation['status'];
      metadata?: Record<string, unknown>;
      memberId?: string | null;
      occurredHoursAgo: number;
    }> = [
      {
        amount: 250,
        currency: 'USD',
        provider: 'stripe',
        status: 'completed',
        metadata: { fund: 'General Offering' },
        memberId: 'member-johnson',
        occurredHoursAgo: 6
      },
      {
        amount: 125,
        currency: 'USD',
        provider: 'paystack',
        status: 'completed',
        metadata: { fund: 'Building Campaign' },
        memberId: 'member-adeola',
        occurredHoursAgo: 30
      },
      {
        amount: 75,
        currency: 'USD',
        provider: 'flutterwave',
        status: 'pending',
        metadata: { fund: 'Youth Retreat' },
        memberId: 'member-chen',
        occurredHoursAgo: 2
      },
      {
        amount: 50,
        currency: 'USD',
        provider: 'fincra',
        status: 'failed',
        metadata: { fund: 'Compassion' },
        memberId: null,
        occurredHoursAgo: 72
      }
    ];

    for (const seed of seeds) {
      const timestamp = new Date(now.getTime() - seed.occurredHoursAgo * 60 * 60 * 1000);
      const donation: Donation = {
        id: randomUUID(),
        memberId: seed.memberId ?? null,
        amount: seed.amount,
        currency: seed.currency,
        provider: seed.provider,
        status: seed.status,
        metadata: seed.metadata ?? {},
        createdAt: timestamp,
        updatedAt: timestamp
      };

      this.donations.set(donation.id, donation);
    }
  }
}
