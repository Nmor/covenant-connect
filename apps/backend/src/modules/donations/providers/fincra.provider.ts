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
import { DonationProviderError } from './provider.error';

@Injectable()
export class FincraPaymentProvider implements DonationPaymentProvider {
  constructor(private readonly configService: ConfigService) {}

  async initializePayment(input: InitializePaymentInput): Promise<InitializePaymentResult> {
    const secretKey = this.getSecretKey();
    const metadata = this.cloneMetadata(input.metadata);

    const email = this.requireString(metadata, 'email', 'Fincra initialization requires an email');
    const firstName = this.requireString(metadata, 'firstName', 'Fincra initialization requires a first name');
    const lastName = this.requireString(metadata, 'lastName', 'Fincra initialization requires a last name');
    const callbackUrl = this.requireString(metadata, 'callbackUrl', 'Fincra initialization requires a callbackUrl');
    const country = this.tryString(metadata, 'country');
    const reference = this.extractReference(metadata);

    const payload: Record<string, unknown> = {
      amount: input.amount.toFixed(2),
      currency: input.currency,
      reference,
      customer: {
        firstName,
        lastName,
        email
      },
      redirectUrl: callbackUrl,
      paymentType: 'card'
    };

    if (country) {
      payload.country = country;
    }

    const response = await this.request('initialize', 'https://api.fincra.com/checkout/payments', {
      method: 'POST',
      headers: {
        'api-key': secretKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    const json = await this.parseJson<{ data?: Record<string, unknown> }>(response, 'initialize');
    const data = this.ensureRecord(json.data);
    const authorizationUrl =
      this.tryString(data, 'checkoutUrl') ??
      this.tryString(data, 'checkout_url') ??
      this.tryString(data, 'paymentLink') ??
      this.tryString(data, 'link');

    if (!authorizationUrl) {
      throw DonationProviderError.processing('Fincra initialize response did not include a checkout URL');
    }

    const resolvedReference =
      this.tryString(data, 'transactionReference') ?? this.tryString(data, 'reference') ?? reference;
    const transactionId = this.tryString(data, 'id') ?? this.tryString(data, 'transactionId');

    return {
      reference: resolvedReference,
      transactionId: transactionId ?? null,
      metadata: {
        authorizationUrl,
        providerReference: resolvedReference,
        fincra: {
          response: data
        }
      },
      status: 'pending'
    };
  }

  async verifyPayment(input: VerifyPaymentInput): Promise<VerifyPaymentResult> {
    const secretKey = this.getSecretKey();
    const url = `https://api.fincra.com/checkout/payments/${encodeURIComponent(input.reference)}`;

    const response = await this.request('verify', url, {
      method: 'GET',
      headers: {
        'api-key': secretKey
      }
    });

    const json = await this.parseJson<{ data?: Record<string, unknown> }>(response, 'verify');
    const data = this.ensureRecord(json.data);

    return {
      status: this.normaliseStatus(this.tryString(data, 'status')),
      transactionId: this.tryString(data, 'id') ?? this.tryString(data, 'transactionId') ?? null,
      metadata: {
        verification: data,
        fincra: {
          verification: data
        }
      }
    };
  }

  async refund(input: RefundPaymentInput): Promise<RefundPaymentResult> {
    const secretKey = this.getSecretKey();
    const url = `https://api.fincra.com/transactions/${encodeURIComponent(input.reference)}/refund`;

    const payload = {
      amount: input.amount.toFixed(2)
    };

    const response = await this.request('refund', url, {
      method: 'POST',
      headers: {
        'api-key': secretKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    const json = await this.parseJson<Record<string, unknown>>(response, 'refund');

    return {
      metadata: {
        refund: json,
        fincra: {
          refund: json
        }
      }
    };
  }

  private getSecretKey(): string {
    const key = this.configService.get<string>('application.payments.fincraKey');
    if (!key) {
      throw DonationProviderError.processing('Fincra secret key is not configured');
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

    throw DonationProviderError.validation(message);
  }

  private tryString(metadata: Record<string, unknown>, key: string): string | null {
    const value = metadata[key];
    return typeof value === 'string' ? value : null;
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
        throw DonationProviderError.processing(
          `Fincra ${action} request failed with status ${response.status}: ${body}`
        );
      }

      return response;
    } catch (error) {
      if (error instanceof DonationProviderError) {
        throw error;
      }

      const message = error instanceof Error ? error.message : 'Unknown error';
      throw DonationProviderError.processing(`Fincra ${action} request failed: ${message}`);
    }
  }

  private async parseJson<T>(response: Response, action: string): Promise<T> {
    try {
      return (await response.json()) as T;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      throw DonationProviderError.processing(`Fincra ${action} response was not valid JSON: ${message}`);
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
