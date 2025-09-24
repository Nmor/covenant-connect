import { ConfigService } from '@nestjs/config';
import { Prisma } from '@prisma/client';
import { createHmac } from 'node:crypto';

import { DonationsService } from './donations.service';
import type {
  DonationPaymentProvider,
  InitializePaymentInput,
  InitializePaymentResult,
  RefundPaymentInput,
  RefundPaymentResult,
  VerifyPaymentInput,
  VerifyPaymentResult,
} from './providers/payment-provider.interface';
import { PaystackPaymentProvider } from './providers/paystack.provider';
import { FincraPaymentProvider } from './providers/fincra.provider';
import { StripePaymentProvider } from './providers/stripe.provider';
import { FlutterwavePaymentProvider } from './providers/flutterwave.provider';
import type { PrismaService } from '../../prisma/prisma.service';

type DonationRecord = {
  id: number;
  memberId: number | null;
  amount: Prisma.Decimal;
  currency: string;
  status: string;
  paymentMethod: string;
  metadata: Record<string, unknown>;
  reference: string | null;
  transactionId: string | null;
  errorMessage: string | null;
  createdAt: Date;
  updatedAt: Date;
};

class InMemoryPrismaService {
  private sequence = 1;
  private readonly records: DonationRecord[] = [];

  public readonly donation = {
    create: jest.fn(async ({ data }: { data: Record<string, unknown> }) => {
      const now = new Date();
      const record: DonationRecord = {
        id: this.sequence++,
        memberId: typeof data.memberId === 'number' ? (data.memberId as number) : null,
        amount: (data.amount as Prisma.Decimal) ?? new Prisma.Decimal(0),
        currency: (data.currency as string) ?? 'USD',
        status: (data.status as string) ?? 'pending',
        paymentMethod: (data.paymentMethod as string) ?? 'paystack',
        metadata: this.cloneMetadata(data.metadata),
        reference: (data.reference as string | null | undefined) ?? null,
        transactionId: (data.transactionId as string | null | undefined) ?? null,
        errorMessage: (data.errorMessage as string | null | undefined) ?? null,
        createdAt: now,
        updatedAt: now,
      };

      this.records.push(record);
      return { ...record };
    }),

    findUnique: jest.fn(async ({ where }: { where: { id: number | string } }) => {
      const id = typeof where.id === 'number' ? where.id : Number.parseInt(where.id as string, 10);
      if (Number.isNaN(id)) {
        return null;
      }

      const found = this.records.find((record) => record.id === id);
      return found ? { ...found } : null;
    }),

    update: jest.fn(async ({
      where,
      data,
    }: {
      where: { id: number | string };
      data: Record<string, unknown>;
    }) => {
      const id = typeof where.id === 'number' ? where.id : Number.parseInt(where.id as string, 10);
      const record = this.records.find((item) => item.id === id);
      if (!record) {
        throw new Error('Donation not found');
      }

      if (data.status !== undefined) {
        record.status = data.status as string;
      }
      if (data.metadata !== undefined) {
        record.metadata = this.cloneMetadata(data.metadata);
      }
      if ('transactionId' in data) {
        record.transactionId = (data.transactionId as string | null | undefined) ?? null;
      }
      if ('errorMessage' in data) {
        record.errorMessage = (data.errorMessage as string | null | undefined) ?? null;
      }

      record.updatedAt = new Date();
      return { ...record };
    }),

    findMany: jest.fn(
      async ({ skip = 0, take = this.records.length, orderBy }: { skip?: number; take?: number; orderBy?: any } = {}) => {
        const sorted = [...this.records];
        if (orderBy?.createdAt === 'desc') {
          sorted.sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
        }

        return sorted.slice(skip, skip + take).map((record) => ({ ...record }));
      }
    ),

    count: jest.fn(async () => this.records.length),

    findFirst: jest.fn(async ({ where }: { where?: Record<string, unknown> }) => {
      if (!where) {
        return this.records[0] ? { ...this.records[0] } : null;
      }

      const conditions = Array.isArray((where as { OR?: Record<string, unknown>[] }).OR)
        ? ((where as { OR?: Record<string, unknown>[] }).OR as Record<string, unknown>[])
        : [where];

      const record = this.records.find((entry) =>
        conditions.some((condition) => {
          if (!condition) {
            return false;
          }
          if ('reference' in condition && condition.reference !== undefined) {
            return entry.reference === condition.reference;
          }
          if ('transactionId' in condition && condition.transactionId !== undefined) {
            return entry.transactionId === condition.transactionId;
          }
          return false;
        })
      );

      return record ? { ...record } : null;
    }),
  };

  async $transaction<T>(input: any): Promise<T> {
    if (Array.isArray(input)) {
      return (await Promise.all(input)) as unknown as T;
    }

    if (typeof input === 'function') {
      return (await input(this)) as T;
    }

    throw new Error('Unsupported transaction input');
  }

  seedDonation(overrides: Partial<DonationRecord> = {}): DonationRecord {
    const now = overrides.createdAt ?? new Date();
    const record: DonationRecord = {
      id: overrides.id ?? this.sequence++,
      memberId: overrides.memberId ?? null,
      amount: overrides.amount ?? new Prisma.Decimal(0),
      currency: overrides.currency ?? 'USD',
      status: overrides.status ?? 'pending',
      paymentMethod: overrides.paymentMethod ?? 'paystack',
      metadata: { ...(overrides.metadata ?? {}) },
      reference: overrides.reference ?? null,
      transactionId: overrides.transactionId ?? null,
      errorMessage: overrides.errorMessage ?? null,
      createdAt: now,
      updatedAt: overrides.updatedAt ?? now,
    };

    this.records.push(record);
    return record;
  }

  private cloneMetadata(metadata: unknown): Record<string, unknown> {
    if (metadata && typeof metadata === 'object' && !Array.isArray(metadata)) {
      return { ...(metadata as Record<string, unknown>) };
    }

    return {};
  }
}

describe('DonationsService', () => {
  let prisma: InMemoryPrismaService;
  let config: ConfigService;
  let paystack: jest.Mocked<DonationPaymentProvider>;
  let fincra: jest.Mocked<DonationPaymentProvider>;
  let stripe: jest.Mocked<DonationPaymentProvider>;
  let flutterwave: jest.Mocked<DonationPaymentProvider>;
  let service: DonationsService;

  const createProvider = (): jest.Mocked<DonationPaymentProvider> => ({
    initializePayment: jest.fn<Promise<InitializePaymentResult>, [InitializePaymentInput]>(),
    verifyPayment: jest.fn<Promise<VerifyPaymentResult>, [VerifyPaymentInput]>(),
    refund: jest.fn<Promise<RefundPaymentResult>, [RefundPaymentInput]>(),
  });

  beforeEach(() => {
    prisma = new InMemoryPrismaService();
    config = new ConfigService({
      application: {
        payments: {
          paystackWebhookSecret: 'paystack-secret',
          fincraWebhookSecret: 'fincra-secret',
          stripeWebhookSecret: 'stripe-secret',
          flutterwaveWebhookSecret: 'flutterwave-secret',
        },
      },
    });

    paystack = createProvider();
    fincra = createProvider();
    stripe = createProvider();
    flutterwave = createProvider();

    service = new DonationsService(
      prisma as unknown as PrismaService,
      config,
      paystack as unknown as PaystackPaymentProvider,
      fincra as unknown as FincraPaymentProvider,
      stripe as unknown as StripePaymentProvider,
      flutterwave as unknown as FlutterwavePaymentProvider
    );
  });

  it('creates donations by delegating to the configured provider', async () => {
    paystack.initializePayment.mockResolvedValue({
      reference: 'paystack-ref',
      transactionId: 'paystack-transaction',
      metadata: { provider: 'paystack', authorizationUrl: 'https://paystack.test/checkout' },
      status: 'pending',
    });

    const donation = await service.create({
      memberId: '17',
      amount: 125,
      currency: 'NGN',
      provider: 'paystack',
      metadata: { donorEmail: 'donor@example.com' },
    });

    expect(paystack.initializePayment).toHaveBeenCalledWith({
      amount: 125,
      currency: 'NGN',
      metadata: { donorEmail: 'donor@example.com' },
    });

    expect(prisma.donation.create).toHaveBeenCalled();
    expect(donation.metadata).toMatchObject({
      donorEmail: 'donor@example.com',
      provider: 'paystack',
      authorizationUrl: 'https://paystack.test/checkout',
      reference: 'paystack-ref',
    });
    expect(donation.memberId).toBe('17');
  });

  it('verifies payments when marking donations as completed', async () => {
    const existing = prisma.seedDonation({
      id: 42,
      paymentMethod: 'paystack',
      status: 'pending',
      reference: 'don-ref',
      metadata: { donorEmail: 'donor@example.com' },
      amount: new Prisma.Decimal(50),
      currency: 'NGN',
    });

    paystack.verifyPayment.mockResolvedValue({
      status: 'completed',
      transactionId: 'verify-1',
      metadata: { verified: true },
    });

    const donation = await service.updateStatus(existing.id.toString(), {
      status: 'completed',
      metadata: { receiptUrl: 'https://example.com/receipt' },
    });

    expect(paystack.verifyPayment).toHaveBeenCalledWith({
      reference: 'don-ref',
      metadata: expect.objectContaining({ donorEmail: 'donor@example.com' }),
    });
    expect(donation.status).toBe('completed');
    expect(donation.metadata).toMatchObject({
      donorEmail: 'donor@example.com',
      verified: true,
      receiptUrl: 'https://example.com/receipt',
      reference: 'don-ref',
    });
  });

  it('reconciles Paystack webhooks when signatures are valid', async () => {
    prisma.seedDonation({
      id: 7,
      paymentMethod: 'paystack',
      status: 'pending',
      reference: 'paystack-ref',
      metadata: { donorEmail: 'donor@example.com' },
    });

    const payload = {
      data: {
        reference: 'paystack-ref',
        id: 'tx-999',
        status: 'success',
      },
      event: 'charge.success',
    };
    const rawBody = JSON.stringify(payload);
    const signature = createHmac('sha512', 'paystack-secret').update(rawBody).digest('hex');

    const result = await service.handlePaystackWebhook(payload, {
      rawBody,
      signature,
      headers: {},
    });

    expect(result.wasUpdated).toBe(true);
    expect(result.donation.status).toBe('completed');
    expect(result.donation.metadata).toMatchObject({
      paystackStatus: 'success',
      reference: 'paystack-ref',
    });
  });
});
