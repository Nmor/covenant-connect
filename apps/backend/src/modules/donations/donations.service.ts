import { BadRequestException, Injectable, NotFoundException, UnauthorizedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Prisma } from '@prisma/client';
import type { Donation as DonationModel } from '@prisma/client';
import type { Donation, PaginatedResult, Pagination } from '@covenant-connect/shared';
import { createHmac, timingSafeEqual } from 'node:crypto';

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

type WebhookContext = {
  rawBody: string;
  signature: string | null;
  headers: Record<string, string | string[] | undefined>;
};

type WebhookUpdate = {
  reference: string | null;
  transactionId: string | null;
  status: Donation['status'];
  metadata: Record<string, unknown>;
  amount?: number | null;
  reason?: string | null;
};

type WebhookProcessResult = {
  donation: Donation;
  wasUpdated: boolean;
};

@Injectable()
export class DonationsService {
  private readonly providers: Record<Donation['provider'], DonationPaymentProvider>;
  private readonly statusPriority: Record<Donation['status'], number> = {
    pending: 0,
    failed: 1,
    completed: 2,
    refunded: 3
  };

  constructor(
    private readonly prisma: PrismaService,
    private readonly configService: ConfigService,
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

  async handlePaystackWebhook(payload: unknown, context: WebhookContext): Promise<WebhookProcessResult> {
    this.verifyPaystackSignature(context.signature, context.rawBody);
    const update = this.extractPaystackWebhook(payload);
    return this.reconcileDonation('paystack', update);
  }

  async handleFincraWebhook(payload: unknown, context: WebhookContext): Promise<WebhookProcessResult> {
    this.verifyFincraSignature(context.signature, context.rawBody);
    const update = this.extractFincraWebhook(payload);
    return this.reconcileDonation('fincra', update);
  }

  async handleStripeWebhook(payload: unknown, context: WebhookContext): Promise<WebhookProcessResult> {
    this.verifyStripeSignature(context.signature, context.rawBody);
    const update = this.extractStripeWebhook(payload);
    return this.reconcileDonation('stripe', update);
  }

  async handleFlutterwaveWebhook(payload: unknown, context: WebhookContext): Promise<WebhookProcessResult> {
    this.verifyFlutterwaveSignature(context.signature);
    const update = this.extractFlutterwaveWebhook(payload);
    return this.reconcileDonation('flutterwave', update);
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

  private async reconcileDonation(
    provider: Donation['provider'],
    update: WebhookUpdate
  ): Promise<WebhookProcessResult> {
    if (!update.reference && !update.transactionId) {
      throw new BadRequestException(
        `${this.formatProviderName(provider)} webhook payload must include a reference or transaction id`
      );
    }

    const conditions: Prisma.DonationWhereInput[] = [];

    if (update.reference) {
      conditions.push({ reference: update.reference });
    }

    if (update.transactionId) {
      conditions.push({ transactionId: update.transactionId });
    }

    const where = conditions.length > 1 ? { OR: conditions } : conditions[0]!;

    const { record, wasUpdated } = await this.prisma.$transaction(async (tx) => {
      const donation = await tx.donation.findFirst({ where });

      if (!donation) {
        throw new NotFoundException('Donation not found for webhook reference');
      }

      const existingStatus = donation.status as Donation['status'];
      const existingMetadata = this.parseMetadata(donation.metadata);

      const statusShouldUpdate = this.shouldUpdateStatus(existingStatus, update.status);
      const hasNewTransactionId = Boolean(update.transactionId && update.transactionId !== donation.transactionId);
      const hasReasonChange = update.reason !== undefined && update.reason !== (donation.errorMessage ?? undefined);
      const metadataChanged = this.hasMetadataChanges(existingMetadata, update.metadata);

      if (!statusShouldUpdate && !hasNewTransactionId && !hasReasonChange && !metadataChanged) {
        return { record: donation, wasUpdated: false } as const;
      }

      const metadata = this.mergeMetadata(existingMetadata, update.metadata);

      const reference = update.reference ?? donation.reference;
      if (reference && !metadata.reference) {
        metadata.reference = reference;
      }

      const data: Prisma.DonationUpdateInput = {
        metadata
      };

      if (statusShouldUpdate) {
        data.status = update.status;
      }

      if (hasNewTransactionId) {
        data.transactionId = update.transactionId;
      }

      if (update.reason !== undefined) {
        data.errorMessage = update.reason;
      }

      const updated = await tx.donation.update({
        where: { id: donation.id },
        data
      });

      return { record: updated, wasUpdated: true } as const;
    });

    return {
      donation: this.toDomain(record),
      wasUpdated
    };
  }

  private shouldUpdateStatus(current: Donation['status'], next: Donation['status']): boolean {
    if (current === next) {
      return false;
    }

    return this.statusPriority[next] >= this.statusPriority[current];
  }

  private mergeMetadata(
    existing: Record<string, unknown>,
    updates: Record<string, unknown>
  ): Record<string, unknown> {
    return { ...existing, ...updates };
  }

  private hasMetadataChanges(existing: Record<string, unknown>, updates: Record<string, unknown>): boolean {
    return Object.entries(updates).some(([key, value]) => {
      if (!(key in existing)) {
        return true;
      }

      const existingValue = existing[key];
      return JSON.stringify(existingValue) !== JSON.stringify(value);
    });
  }

  private verifyPaystackSignature(signature: string | null, rawBody: string): void {
    const secret = this.getWebhookSecret('paystack');
    this.verifyHmacSignature({
      provider: 'Paystack',
      signature,
      rawBody,
      secret,
      algorithm: 'sha512'
    });
  }

  private verifyFincraSignature(signature: string | null, rawBody: string): void {
    const secret = this.getWebhookSecret('fincra');
    this.verifyHmacSignature({
      provider: 'Fincra',
      signature,
      rawBody,
      secret,
      algorithm: 'sha256'
    });
  }

  private verifyStripeSignature(signature: string | null, rawBody: string): void {
    const secret = this.getWebhookSecret('stripe');
    if (!signature) {
      throw new UnauthorizedException('Missing Stripe webhook signature');
    }

    const parts = signature.split(',');
    let timestamp: string | null = null;
    const signatures: string[] = [];

    for (const part of parts) {
      const [key, value] = part.split('=');
      if (key === 't') {
        timestamp = value ?? null;
      }
      if (key === 'v1' && value) {
        signatures.push(value);
      }
    }

    if (!timestamp || signatures.length === 0) {
      throw new UnauthorizedException('Invalid Stripe webhook signature header');
    }

    const signedPayload = `${timestamp}.${rawBody}`;
    const expected = createHmac('sha256', secret).update(signedPayload).digest('hex');

    const isValid = signatures.some((candidate) => this.timingSafeEqualHex(candidate, expected));
    if (!isValid) {
      throw new UnauthorizedException('Invalid Stripe webhook signature');
    }
  }

  private verifyFlutterwaveSignature(signature: string | null): void {
    const secret = this.getWebhookSecret('flutterwave');
    if (!signature) {
      throw new UnauthorizedException('Missing Flutterwave webhook signature');
    }

    if (!this.timingSafeEqualString(signature.trim(), secret.trim())) {
      throw new UnauthorizedException('Invalid Flutterwave webhook signature');
    }
  }

  private getWebhookSecret(provider: 'paystack' | 'fincra' | 'stripe' | 'flutterwave'): string {
    const paths: Record<typeof provider, string[]> = {
      paystack: ['application.payments.paystackWebhookSecret', 'application.payments.paystackKey'],
      fincra: ['application.payments.fincraWebhookSecret', 'application.payments.fincraKey'],
      stripe: ['application.payments.stripeWebhookSecret'],
      flutterwave: [
        'application.payments.flutterwaveWebhookSecret',
        'application.payments.flutterwaveKey'
      ]
    };

    for (const path of paths[provider]) {
      const value = this.configService.get<string>(path);
      if (value && value.trim().length > 0) {
        return value.trim();
      }
    }

    throw new UnauthorizedException(`${this.formatProviderName(provider)} webhook secret is not configured`);
  }

  private verifyHmacSignature(options: {
    provider: string;
    signature: string | null;
    rawBody: string;
    secret: string;
    algorithm: 'sha256' | 'sha512';
  }): void {
    const { provider, signature, rawBody, secret, algorithm } = options;

    if (!signature) {
      throw new UnauthorizedException(`Missing ${provider} webhook signature`);
    }

    const expected = createHmac(algorithm, secret).update(rawBody).digest('hex');
    if (!this.timingSafeEqualHex(signature, expected)) {
      throw new UnauthorizedException(`Invalid ${provider} webhook signature`);
    }
  }

  private timingSafeEqualHex(provided: string, expected: string): boolean {
    try {
      const providedBuffer = Buffer.from(provided.trim().toLowerCase(), 'hex');
      const expectedBuffer = Buffer.from(expected.trim().toLowerCase(), 'hex');

      if (providedBuffer.length !== expectedBuffer.length) {
        return false;
      }

      return timingSafeEqual(providedBuffer, expectedBuffer);
    } catch {
      return false;
    }
  }

  private timingSafeEqualString(provided: string, expected: string): boolean {
    const providedBuffer = Buffer.from(provided);
    const expectedBuffer = Buffer.from(expected);

    if (providedBuffer.length !== expectedBuffer.length) {
      return false;
    }

    return timingSafeEqual(providedBuffer, expectedBuffer);
  }

  private extractPaystackWebhook(payload: unknown): WebhookUpdate {
    const record = this.ensureRecord(payload, 'Paystack webhook payload must be an object');
    const data = this.coerceRecord(record.data);

    const reference =
      this.tryId(data.reference) ??
      this.tryId(data.reference_code) ??
      this.tryId(data.transaction_reference) ??
      this.tryId(record.reference);

    const transactionId =
      this.tryId(data.id) ?? this.tryId(data.transaction_id) ?? this.tryId(data.transactionId) ?? null;

    const statusSource = this.tryString(data, 'status') ?? this.tryString(record, 'event') ?? this.tryString(record, 'status');
    const status = this.normaliseStatus(statusSource);

    let reason: string | undefined;
    if (status === 'failed') {
      reason =
        this.tryString(data, 'gateway_response') ??
        this.tryString(data, 'message') ??
        this.tryString(record, 'message') ??
        undefined;
    } else if (status === 'completed') {
      reason = null;
    }

    const metadata: Record<string, unknown> = {
      paystackWebhook: record
    };

    if (statusSource) {
      metadata.paystackStatus = statusSource;
    }

    return {
      reference: reference ?? null,
      transactionId,
      status,
      metadata,
      reason
    };
  }

  private extractFincraWebhook(payload: unknown): WebhookUpdate {
    const record = this.ensureRecord(payload, 'Fincra webhook payload must be an object');
    const data = this.coerceRecord(record.data);

    const reference = this.tryId(data.reference) ?? this.tryId(record.reference) ?? null;
    const transactionId =
      this.tryId(data.transactionId) ??
      this.tryId(data.transaction_id) ??
      this.tryId(data.id) ??
      this.tryId(record.transactionId) ??
      null;

    const statusSource = this.tryString(data, 'status') ?? this.tryString(record, 'status');
    const status = this.normaliseStatus(statusSource);

    let reason: string | undefined;
    if (status === 'failed') {
      reason = this.tryString(data, 'failureReason') ?? this.tryString(record, 'failureReason') ?? undefined;
    } else if (status === 'completed') {
      reason = null;
    }

    const metadata: Record<string, unknown> = {
      fincraWebhook: record
    };

    if (statusSource) {
      metadata.fincraStatus = statusSource;
    }

    return {
      reference,
      transactionId,
      status,
      metadata,
      reason
    };
  }

  private extractStripeWebhook(payload: unknown): WebhookUpdate {
    const record = this.ensureRecord(payload, 'Stripe webhook payload must be an object');
    const data = this.coerceRecord(record.data);
    const object = this.coerceRecord(data.object);

    const reference =
      this.tryId(object.id) ??
      this.tryId(object.client_reference_id) ??
      this.tryId(data.client_reference_id) ??
      this.tryId(record.reference) ??
      null;

    const transactionId =
      this.tryId(object.payment_intent) ??
      this.tryId(object.id) ??
      this.tryId(data.payment_intent) ??
      null;

    const statusSource =
      this.tryString(object, 'payment_status') ??
      this.tryString(object, 'status') ??
      this.tryString(record, 'type');
    const status = this.normaliseStatus(statusSource);

    let reason: string | undefined;
    if (status === 'failed') {
      const lastPaymentError = this.coerceRecord(object.last_payment_error);
      reason = this.tryString(lastPaymentError, 'message') ?? this.tryString(object, 'status') ?? undefined;
    } else if (status === 'completed') {
      reason = null;
    }

    const metadata: Record<string, unknown> = {
      stripeWebhook: record
    };

    const eventType = this.tryString(record, 'type');
    if (eventType) {
      metadata.stripeEventType = eventType;
    }
    if (statusSource) {
      metadata.stripeStatus = statusSource;
    }

    return {
      reference,
      transactionId,
      status,
      metadata,
      reason
    };
  }

  private extractFlutterwaveWebhook(payload: unknown): WebhookUpdate {
    const record = this.ensureRecord(payload, 'Flutterwave webhook payload must be an object');
    const data = this.coerceRecord(record.data);

    const reference =
      this.tryId(data.tx_ref) ??
      this.tryId(data.reference) ??
      this.tryId(record.tx_ref) ??
      this.tryId(record.reference) ??
      null;

    const transactionId =
      this.tryId(data.id) ??
      this.tryId(data.flw_ref) ??
      this.tryId(record.id) ??
      this.tryId(record.flw_ref) ??
      null;

    const statusSource = this.tryString(data, 'status') ?? this.tryString(record, 'status');
    const status = this.normaliseStatus(statusSource);

    let reason: string | undefined;
    if (status === 'failed') {
      reason =
        this.tryString(data, 'processor_response') ??
        this.tryString(data, 'status') ??
        this.tryString(record, 'message') ??
        undefined;
    } else if (status === 'completed') {
      reason = null;
    }

    const metadata: Record<string, unknown> = {
      flutterwaveWebhook: record
    };

    if (statusSource) {
      metadata.flutterwaveStatus = statusSource;
    }

    return {
      reference,
      transactionId,
      status,
      metadata,
      reason
    };
  }

  private ensureRecord(value: unknown, message: string): Record<string, unknown> {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return { ...(value as Record<string, unknown>) };
    }

    throw new BadRequestException(message);
  }

  private coerceRecord(value: unknown): Record<string, unknown> {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return { ...(value as Record<string, unknown>) };
    }

    return {};
  }

  private tryString(record: Record<string, unknown>, key: string): string | null {
    const value = record[key];
    if (typeof value === 'string') {
      const trimmed = value.trim();
      return trimmed.length > 0 ? trimmed : null;
    }

    return null;
  }

  private tryId(value: unknown): string | null {
    if (typeof value === 'string') {
      const trimmed = value.trim();
      return trimmed.length > 0 ? trimmed : null;
    }

    if (typeof value === 'number' && Number.isFinite(value)) {
      return value.toString();
    }

    return null;
  }

  private normaliseStatus(value: string | null | undefined): Donation['status'] {
    if (!value) {
      return 'pending';
    }

    const normalised = value.toLowerCase();
    if (normalised.includes('success') || normalised.includes('complete') || normalised.includes('paid')) {
      return 'completed';
    }
    if (normalised.includes('refund')) {
      return 'refunded';
    }
    if (
      normalised.includes('fail') ||
      normalised.includes('declin') ||
      normalised.includes('error') ||
      normalised.includes('cancel')
    ) {
      return 'failed';
    }

    return 'pending';
  }

  private formatProviderName(provider: Donation['provider']): string {
    return provider.charAt(0).toUpperCase() + provider.slice(1);
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
