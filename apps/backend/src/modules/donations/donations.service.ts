import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import type { Donation as DonationModel } from '@prisma/client';
import type { Donation, PaginatedResult, Pagination } from '@covenant-connect/shared';

import { PrismaService } from '../../prisma/prisma.service';
import type { DonationPaymentProvider } from './providers/payment-provider.interface';
import { PaystackPaymentProvider } from './providers/paystack.provider';
import { FincraPaymentProvider } from './providers/fincra.provider';
import { StripePaymentProvider } from './providers/stripe.provider';
import { FlutterwavePaymentProvider } from './providers/flutterwave.provider';

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
  private readonly providers: Record<Donation['provider'], DonationPaymentProvider>;

  constructor(
    private readonly prisma: PrismaService,
    paystackProvider: PaystackPaymentProvider,
    fincraProvider: FincraPaymentProvider,
    stripeProvider: StripePaymentProvider,
    flutterwaveProvider: FlutterwavePaymentProvider
  ) {
    this.providers = {
      paystack: paystackProvider,
      fincra: fincraProvider,
      stripe: stripeProvider,
      flutterwave: flutterwaveProvider
    };
  }

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
    const provider = this.getProvider(input.provider);
    const baseMetadata = this.cloneMetadata(input.metadata);

    const initialization = await provider.initializePayment({
      amount: input.amount,
      currency: input.currency,
      metadata: baseMetadata
    });

    const combinedMetadata = {
      ...baseMetadata,
      ...initialization.metadata
    };

    if (!combinedMetadata.reference) {
      combinedMetadata.reference = initialization.reference;
    }

    const created = await this.prisma.donation.create({
      data: {
        memberId,
        amount: new Prisma.Decimal(input.amount),
        currency: input.currency,
        paymentMethod: input.provider,
        metadata: combinedMetadata,
        status: initialization.status ?? 'pending',
        reference: initialization.reference,
        transactionId: initialization.transactionId ?? null
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

    const provider = this.getProvider(existing.paymentMethod as Donation['provider']);
    const existingMetadata = this.parseMetadata(existing.metadata);
    let status = input.status;
    let transactionId = existing.transactionId;
    let providerMetadata: Record<string, unknown> = {};

    if (input.status === 'completed') {
      const reference = this.ensureReference(existing);
      const verification = await provider.verifyPayment({
        reference,
        metadata: existingMetadata
      });
      status = verification.status ?? input.status;
      transactionId = verification.transactionId ?? transactionId;
      providerMetadata = verification.metadata;
    } else if (input.status === 'refunded') {
      const reference = this.getRefundReference(existing);
      const amount = this.getAmountValue(existing.amount);
      const refund = await provider.refund({
        reference,
        amount,
        metadata: existingMetadata
      });
      providerMetadata = refund.metadata;
    }

    const combinedMetadata = {
      ...existingMetadata,
      ...providerMetadata,
      ...(input.metadata ?? {})
    };

    if (existing.reference && !combinedMetadata.reference) {
      combinedMetadata.reference = existing.reference;
    }

    const updated = await this.prisma.donation.update({
      where: { id: existing.id },
      data: {
        status,
        metadata: combinedMetadata,
        transactionId: transactionId ?? existing.transactionId ?? null
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

  private getProvider(provider: Donation['provider']): DonationPaymentProvider {
    const resolved = this.providers[provider];
    if (!resolved) {
      throw new BadRequestException(`Unsupported donation provider: ${provider}`);
    }

    return resolved;
  }

  private cloneMetadata(metadata?: Record<string, unknown>): Record<string, unknown> {
    if (!metadata) {
      return {};
    }

    return { ...metadata };
  }

  private parseMetadata(metadata: Prisma.JsonValue | null | undefined): Record<string, unknown> {
    if (metadata && typeof metadata === 'object' && !Array.isArray(metadata)) {
      return { ...(metadata as Record<string, unknown>) };
    }

    return {};
  }

  private ensureReference(record: DonationModel): string {
    if (record.reference) {
      return record.reference;
    }

    throw new BadRequestException('Donation does not have a provider reference');
  }

  private getRefundReference(record: DonationModel): string {
    if (record.transactionId) {
      return record.transactionId;
    }

    return this.ensureReference(record);
  }

  private getAmountValue(amount: Prisma.Decimal | number): number {
    return amount instanceof Prisma.Decimal ? amount.toNumber() : Number(amount);
  }
}
