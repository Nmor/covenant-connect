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
export class StripePaymentProvider implements DonationPaymentProvider {
  constructor(private readonly configService: ConfigService) {}

  async initializePayment(input: InitializePaymentInput): Promise<InitializePaymentResult> {
    const secretKey = this.getSecretKey();
    const metadata = this.cloneMetadata(input.metadata);

    const email = this.requireString(metadata, 'email', 'Stripe initialization requires an email');
    const successUrl = this.requireString(metadata, 'successUrl', 'Stripe initialization requires a successUrl');
    const cancelUrl = this.requireString(metadata, 'cancelUrl', 'Stripe initialization requires a cancelUrl');
    const reference = this.extractReference(metadata);

    const amountInMinorUnits = Math.round(input.amount * 100);
    const params = new URLSearchParams({
      mode: 'payment',
      success_url: successUrl,
      cancel_url: cancelUrl,
      'line_items[0][price_data][currency]': input.currency.toLowerCase(),
      'line_items[0][price_data][product_data][name]': 'Donation',
      'line_items[0][price_data][unit_amount]': amountInMinorUnits.toString(),
      'line_items[0][quantity]': '1',
      customer_email: email,
      client_reference_id: reference
    });

    const response = await this.request('initialize', 'https://api.stripe.com/v1/checkout/sessions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${secretKey}`,
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: params
    });

    const session = await this.parseJson<Record<string, unknown>>(response, 'initialize');
    const url = this.requireRecordString(session, 'url', 'Stripe initialize response did not include a checkout URL');
    const sessionId = this.requireRecordString(session, 'id', 'Stripe initialize response did not include a session id');
    const paymentIntent = this.tryString(session, 'payment_intent');

    return {
      reference: sessionId,
      transactionId: paymentIntent ?? null,
      metadata: {
        authorizationUrl: url,
        providerReference: sessionId,
        stripe: {
          session
        }
      },
      status: 'pending'
    };
  }

  async verifyPayment(input: VerifyPaymentInput): Promise<VerifyPaymentResult> {
    const secretKey = this.getSecretKey();
    const url = `https://api.stripe.com/v1/checkout/sessions/${encodeURIComponent(input.reference)}`;

    const response = await this.request('verify', url, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${secretKey}`
      }
    });

    const session = await this.parseJson<Record<string, unknown>>(response, 'verify');
    const paymentStatus = this.tryString(session, 'payment_status') ?? this.tryString(session, 'status');
    const transactionId = this.tryString(session, 'payment_intent') ?? this.tryString(session, 'id');

    return {
      status: this.normaliseStatus(paymentStatus),
      transactionId: transactionId ?? null,
      metadata: {
        verification: session,
        stripe: {
          verification: session
        }
      }
    };
  }

  async refund(input: RefundPaymentInput): Promise<RefundPaymentResult> {
    const secretKey = this.getSecretKey();
    const amountInMinorUnits = Math.round(input.amount * 100);

    const params = new URLSearchParams({
      payment_intent: input.reference,
      amount: amountInMinorUnits.toString()
    });

    const response = await this.request('refund', 'https://api.stripe.com/v1/refunds', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${secretKey}`,
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: params
    });

    const refund = await this.parseJson<Record<string, unknown>>(response, 'refund');

    return {
      metadata: {
        refund,
        stripe: {
          refund
        }
      }
    };
  }

  private getSecretKey(): string {
    const key = this.configService.get<string>('application.payments.stripeKey');
    if (!key) {
      throw DonationProviderError.processing('Stripe secret key is not configured');
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

  private requireRecordString(record: Record<string, unknown>, key: string, message: string): string {
    const value = record[key];
    if (typeof value === 'string' && value.trim().length > 0) {
      return value;
    }

    throw DonationProviderError.validation(message);
  }

  private tryString(record: Record<string, unknown>, key: string): string | null {
    const value = record[key];
    return typeof value === 'string' ? value : null;
  }

  private cloneMetadata(metadata: Record<string, unknown>): Record<string, unknown> {
    return { ...metadata };
  }

  private normaliseStatus(status: string | null | undefined): Donation['status'] {
    if (!status) {
      return 'pending';
    }

    const normalised = status.toLowerCase();
    if (normalised.includes('paid') || normalised.includes('success')) {
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
          `Stripe ${action} request failed with status ${response.status}: ${body}`
        );
      }

      return response;
    } catch (error) {
      if (error instanceof DonationProviderError) {
        throw error;
      }

      const message = error instanceof Error ? error.message : 'Unknown error';
      throw DonationProviderError.processing(`Stripe ${action} request failed: ${message}`);
    }
  }

  private async parseJson<T>(response: Response, action: string): Promise<T> {
    try {
      return (await response.json()) as T;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      throw DonationProviderError.processing(`Stripe ${action} response was not valid JSON: ${message}`);
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
