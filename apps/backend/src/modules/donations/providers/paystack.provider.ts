import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { randomUUID } from 'node:crypto';
import type { Donation } from '@covenant-connect/shared';

import type {
  DonationPaymentProvider,
  InitializePaymentInput,
  InitializePaymentResult,
  RefundPaymentInput,
  RefundPaymentResult,
  VerifyPaymentInput,
  VerifyPaymentResult
} from './payment-provider.interface';

@Injectable()
export class PaystackPaymentProvider implements DonationPaymentProvider {
  constructor(private readonly configService: ConfigService) {}

  async initializePayment(input: InitializePaymentInput): Promise<InitializePaymentResult> {
    const secretKey = this.getSecretKey();
    const metadata = this.cloneMetadata(input.metadata);
    const email = this.requireString(metadata, 'email', 'Paystack initialization requires an email');
    const callbackUrl = this.requireString(metadata, 'callbackUrl', 'Paystack initialization requires a callbackUrl');
    const reference = this.extractReference(metadata);

    const payload = {
      amount: Math.round(input.amount * 100),
      currency: input.currency,
      email,
      reference,
      callback_url: callbackUrl
    };

    const response = await this.request('initialize', 'https://api.paystack.co/transaction/initialize', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${secretKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    const json = await this.parseJson<{ data?: Record<string, unknown>; authorization_url?: string }>(response, 'initialize');
    const data = this.ensureRecord(json.data);
    const authorizationUrl = this.tryString(data, 'authorization_url') ?? this.tryString(json, 'authorization_url');

    if (!authorizationUrl) {
      throw new Error('Paystack initialize response did not include an authorization URL');
    }

    const resolvedReference = this.tryString(data, 'reference') ?? reference;
    const transactionId = this.tryString(data, 'id');

    return {
      reference: resolvedReference,
      transactionId: transactionId ?? null,
      metadata: {
        authorizationUrl,
        providerReference: resolvedReference,
        paystack: {
          response: data
        }
      },
      status: 'pending'
    };
  }

  async verifyPayment(input: VerifyPaymentInput): Promise<VerifyPaymentResult> {
    const secretKey = this.getSecretKey();
    const url = `https://api.paystack.co/transaction/verify/${encodeURIComponent(input.reference)}`;

    const response = await this.request('verify', url, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${secretKey}`
      }
    });

    const json = await this.parseJson<{ data?: Record<string, unknown> }>(response, 'verify');
    const data = this.ensureRecord(json.data);
    const status = this.normaliseStatus(this.tryString(data, 'status'));
    const transactionId = this.tryString(data, 'id');

    return {
      status,
      transactionId: transactionId ?? null,
      metadata: {
        verification: data,
        paystack: {
          verification: data
        }
      }
    };
  }

  async refund(input: RefundPaymentInput): Promise<RefundPaymentResult> {
    const secretKey = this.getSecretKey();

    const payload = {
      transaction: input.reference,
      amount: Math.round(input.amount * 100)
    };

    const response = await this.request('refund', 'https://api.paystack.co/refund', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${secretKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    const json = await this.parseJson<Record<string, unknown>>(response, 'refund');

    return {
      metadata: {
        refund: json,
        paystack: {
          refund: json
        }
      }
    };
  }

  private getSecretKey(): string {
    const key = this.configService.get<string>('application.payments.paystackKey');
    if (!key) {
      throw new Error('Paystack secret key is not configured');
    }

    return key;
  }

  private extractReference(metadata: Record<string, unknown>): string {
    const reference = metadata.reference;
    if (typeof reference === 'string' && reference.trim().length > 0) {
      return reference;
    }

    return randomUUID();
  }

  private requireString(metadata: Record<string, unknown>, key: string, message: string): string {
    const value = metadata[key];
    if (typeof value === 'string' && value.trim().length > 0) {
      return value;
    }

    throw new Error(message);
  }

  private cloneMetadata(metadata: Record<string, unknown>): Record<string, unknown> {
    return { ...metadata };
  }

  private ensureRecord(value: unknown): Record<string, unknown> {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return value as Record<string, unknown>;
    }

    return {};
  }

  private tryString(record: Record<string, unknown>, key: string): string | null {
    const value = record[key];
    return typeof value === 'string' ? value : null;
  }

  private normaliseStatus(status: string | null | undefined): Donation['status'] {
    if (!status) {
      return 'pending';
    }

    const normalised = status.toLowerCase();
    if (normalised.includes('success')) {
      return 'completed';
    }
    if (normalised.includes('fail')) {
      return 'failed';
    }
    if (normalised.includes('refund')) {
      return 'refunded';
    }

    return 'pending';
  }

  private async request(action: string, url: string, init: RequestInit): Promise<Response> {
    try {
      const response = await fetch(url, init);
      if (!response.ok) {
        const body = await this.safeReadBody(response);
        throw new Error(`Paystack ${action} request failed with status ${response.status}: ${body}`);
      }

      return response;
    } catch (error) {
      if (error instanceof Error && error.message.startsWith('Paystack')) {
        throw error;
      }

      const message = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Paystack ${action} request failed: ${message}`);
    }
  }

  private async parseJson<T>(response: Response, action: string): Promise<T> {
    try {
      return (await response.json()) as T;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Paystack ${action} response was not valid JSON: ${message}`);
    }
  }

  private async safeReadBody(response: Response): Promise<string> {
    try {
      return await response.text();
    } catch {
      return '';
    }
  }
}
