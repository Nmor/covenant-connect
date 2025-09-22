import 'reflect-metadata';

import { INestApplication } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Test } from '@nestjs/testing';
import { Prisma } from '@prisma/client';
import request from 'supertest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { DonationsController } from '../src/modules/donations/donations.controller';
import { CreateDonationDto } from '../src/modules/donations/dto/create-donation.dto';
import { DonationsModule } from '../src/modules/donations/donations.module';
import { DonationsService } from '../src/modules/donations/donations.service';
import { FincraPaymentProvider } from '../src/modules/donations/providers/fincra.provider';
import { FlutterwavePaymentProvider } from '../src/modules/donations/providers/flutterwave.provider';
import type { DonationPaymentProvider } from '../src/modules/donations/providers/payment-provider.interface';
import { DonationProviderError } from '../src/modules/donations/providers/provider.error';
import { PaystackPaymentProvider } from '../src/modules/donations/providers/paystack.provider';
import { StripePaymentProvider } from '../src/modules/donations/providers/stripe.provider';
import { PrismaService } from '../src/prisma/prisma.service';

type MockDonationPaymentProvider = DonationPaymentProvider & {
  initializePayment: ReturnType<typeof vi.fn>;
  verifyPayment: ReturnType<typeof vi.fn>;
  refund: ReturnType<typeof vi.fn>;
};

(Prisma as unknown as { Decimal: unknown }).Decimal = class {
  private readonly value: number;

  constructor(value: number) {
    this.value = value;
  }

  toNumber(): number {
    return this.value;
  }
};

const createMockProvider = (): MockDonationPaymentProvider => {
  return {
    initializePayment: vi.fn(),
    verifyPayment: vi.fn(),
    refund: vi.fn()
  } as unknown as MockDonationPaymentProvider;
};

class InMemoryPrismaService {
  private donations: Array<{
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
  }> = [];

  private sequence = 1;

  public readonly donation = {
    create: async ({ data }: { data: Record<string, unknown> }) => {
      const now = new Date();
      const record = {
        id: this.sequence++,
        memberId: typeof data.memberId === 'number' ? (data.memberId as number) : null,
        amount: (data.amount as Prisma.Decimal) ?? new Prisma.Decimal(0),
        currency: (data.currency as string) ?? 'USD',
        status: (data.status as string) ?? 'pending',
        paymentMethod: (data.paymentMethod as string) ?? 'paystack',
        metadata: this.normaliseMetadata(data.metadata),
        reference: (data.reference as string | null | undefined) ?? null,
        transactionId: (data.transactionId as string | null | undefined) ?? null,
        errorMessage: (data.errorMessage as string | null | undefined) ?? null,
        createdAt: now,
        updatedAt: now
      };

      this.donations.push(record);
      return record;
    }
  };

  async $transaction<T>(input: any): Promise<T> {
    if (Array.isArray(input)) {
      return Promise.all(input) as unknown as T;
    }

    if (typeof input === 'function') {
      return input(this);
    }

    throw new Error('Unsupported transaction input in InMemoryPrismaService');
  }

  getDonations() {
    return this.donations;
  }

  private normaliseMetadata(metadata: unknown): Record<string, unknown> {
    if (metadata && typeof metadata === 'object' && !Array.isArray(metadata)) {
      return { ...(metadata as Record<string, unknown>) };
    }

    return {};
  }
}

describe('DonationsController (e2e)', () => {
  let app: INestApplication;
  let prisma: InMemoryPrismaService;
  let paystackProvider: MockDonationPaymentProvider;

  const createApp = async () => {
    prisma = new InMemoryPrismaService();
    paystackProvider = createMockProvider();

    const configStub = { get: vi.fn(() => null) };

    const existingMetadata = Reflect.getMetadata('design:paramtypes', DonationsController);
    if (!existingMetadata) {
      Reflect.defineMetadata('design:paramtypes', [DonationsService], DonationsController);
    }

    const createMetadata = Reflect.getMetadata(
      'design:paramtypes',
      DonationsController.prototype,
      'create'
    );
    if (!createMetadata) {
      Reflect.defineMetadata(
        'design:paramtypes',
        [CreateDonationDto],
        DonationsController.prototype,
        'create'
      );
    }


    const moduleRef = await Test.createTestingModule({
      imports: [DonationsModule],
      providers: [
        { provide: PrismaService, useValue: prisma },
        { provide: ConfigService, useValue: configStub }
      ]
    })
      .overrideProvider(PaystackPaymentProvider)
      .useValue(paystackProvider)
      .overrideProvider(FincraPaymentProvider)
      .useValue(createMockProvider())
      .overrideProvider(StripePaymentProvider)
      .useValue(createMockProvider())
      .overrideProvider(FlutterwavePaymentProvider)
      .useValue(createMockProvider())
      .compile();

    const donationsService = moduleRef.get(DonationsService);
    (donationsService as any).prisma = prisma;
    (donationsService as any).configService = configStub;
    (donationsService as any).providers.paystack = paystackProvider;

    app = moduleRef.createNestApplication();
    await app.init();
  };

  beforeEach(async () => {
    await createApp();
  });

  afterEach(async () => {
    await app.close();
    vi.restoreAllMocks();
  });

  it('rejects requests missing required fields', async () => {
    const response = await request(app.getHttpServer()).post('/donations').send({});

    expect(response.status).toBe(400);
    expect(response.body.message).toEqual(
      expect.arrayContaining([
        expect.stringContaining('amount'),
        expect.stringContaining('currency'),
        expect.stringContaining('provider')
      ])
    );
  });

  it('rejects requests with non-positive amounts', async () => {
    const response = await request(app.getHttpServer())
      .post('/donations')
      .send({ amount: -5, currency: 'NGN', provider: 'paystack' });

    expect(response.status).toBe(400);
    expect(response.body.message).toEqual(
      expect.arrayContaining([expect.stringContaining('amount must be a positive number')])
    );
  });

  it('surfaces validation errors from the provider', async () => {
    paystackProvider.initializePayment.mockRejectedValueOnce(
      DonationProviderError.validation('Email is required for Paystack payments')
    );

    const response = await request(app.getHttpServer())
      .post('/donations')
      .send({ amount: 10, currency: 'NGN', provider: 'paystack', metadata: {} });

    expect(response.status).toBe(400);
    expect(response.body.message).toBe('Email is required for Paystack payments');
  });

  it('surfaces processing errors from the provider', async () => {
    paystackProvider.initializePayment.mockRejectedValueOnce(
      DonationProviderError.processing('Paystack is unavailable')
    );

    const response = await request(app.getHttpServer())
      .post('/donations')
      .send({ amount: 25, currency: 'NGN', provider: 'paystack', metadata: { email: 'donor@example.com' } });

    expect(response.status).toBe(502);
    expect(response.body.message).toBe('Paystack is unavailable');
  });

  it('creates donations when the provider succeeds', async () => {
    paystackProvider.initializePayment.mockResolvedValueOnce({
      reference: 'paystack-ref',
      transactionId: 'paystack-transaction',
      metadata: { authorizationUrl: 'https://paystack.test/redirect' },
      status: 'pending'
    });

    const response = await request(app.getHttpServer())
      .post('/donations')
      .send({
        amount: 100,
        currency: 'NGN',
        provider: 'paystack',
        metadata: { email: 'donor@example.com', callbackUrl: 'https://example.com/return' }
      });

    expect(response.status).toBe(201);
    expect(response.body).toMatchObject({
      amount: 100,
      currency: 'NGN',
      provider: 'paystack',
      status: 'pending',
      metadata: expect.objectContaining({ authorizationUrl: 'https://paystack.test/redirect' })
    });

    const [stored] = prisma.getDonations();
    expect(stored).toBeDefined();
    expect(stored.reference).toBe('paystack-ref');
    expect(paystackProvider.initializePayment).toHaveBeenCalledWith({
      amount: 100,
      currency: 'NGN',
      metadata: expect.objectContaining({ email: 'donor@example.com', callbackUrl: 'https://example.com/return' })
    });
  });
});
