import { Injectable, NotFoundException } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import type { Donation as DonationModel } from '@prisma/client';
import type { Donation, PaginatedResult, Pagination } from '@covenant-connect/shared';

import { PrismaService } from '../../prisma/prisma.service';

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
  constructor(private readonly prisma: PrismaService) {}

  async list(pagination: Pagination): Promise<PaginatedResult<Donation>> {
    const skip = (pagination.page - 1) * pagination.pageSize;
    const take = pagination.pageSize;

    const [records, total] = await this.prisma.$transaction([
      this.prisma.donation.findMany({
        skip,
        take,
        orderBy: { createdAt: 'desc' }
      }),
      this.prisma.donation.count()
    ]);

    return {
      data: records.map((record) => this.toDomain(record)),
      total,
      page: pagination.page,
      pageSize: pagination.pageSize
    };
  }

  async create(input: CreateDonationInput): Promise<Donation> {
    const memberId = this.parseMemberId(input.memberId);
    const created = await this.prisma.donation.create({
      data: {
        memberId,
        amount: new Prisma.Decimal(input.amount),
        currency: input.currency,
        paymentMethod: input.provider,
        metadata: input.metadata ?? {},
        status: 'pending'
      }
    });

    return this.toDomain(created);
  }

  async updateStatus(donationId: string, input: UpdateDonationStatusInput): Promise<Donation> {
    const existing = await this.prisma.donation.findUnique({
      where: { id: this.parseId(donationId) }
    });

    if (!existing) {
      throw new NotFoundException('Donation not found');
    }

    const updated = await this.prisma.donation.update({
      where: { id: existing.id },
      data: {
        status: input.status,
        metadata: {
          ...((existing.metadata as Record<string, unknown>) ?? {}),
          ...(input.metadata ?? {})
        }
      }
    });

    return this.toDomain(updated);
  }

  private toDomain(record: DonationModel): Donation {
    const amount = record.amount instanceof Prisma.Decimal ? record.amount.toNumber() : Number(record.amount);
    return {
      id: record.id.toString(),
      memberId: record.memberId !== null ? record.memberId.toString() : null,
      amount,
      currency: record.currency,
      provider: record.paymentMethod as Donation['provider'],
      status: record.status as Donation['status'],
      metadata: (record.metadata as Record<string, unknown>) ?? {},
      createdAt: record.createdAt,
      updatedAt: record.updatedAt
    };
  }

  private parseMemberId(memberId?: string | null): number | null {
    if (!memberId) {
      return null;
    }

    const parsed = Number.parseInt(memberId, 10);
    return Number.isNaN(parsed) ? null : parsed;
  }

  private parseId(id: string): number {
    const parsed = Number.parseInt(id, 10);
    if (Number.isNaN(parsed)) {
      throw new NotFoundException('Donation not found');
    }

    return parsed;
  }
}
