import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import type { ConfigService } from '@nestjs/config';

import { PaystackPaymentProvider } from '../src/modules/donations/providers/paystack.provider';
import { FincraPaymentProvider } from '../src/modules/donations/providers/fincra.provider';
import { StripePaymentProvider } from '../src/modules/donations/providers/stripe.provider';
import { FlutterwavePaymentProvider } from '../src/modules/donations/providers/flutterwave.provider';

const createConfig = (values: Record<string, string | null>): ConfigService => {
  return {
    get: (key: string) => (key in values ? values[key] ?? null : null)
  } as unknown as ConfigService;
};

const createResponse = (
  body: unknown,
  init: { ok?: boolean; status?: number; text?: string } = {}
): Response => {
  return {
    ok: init.ok ?? true,
    status: init.status ?? 200,
    json: async () => body,
    text: async () => init.text ?? JSON.stringify(body)
  } as Response;
};

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('PaystackPaymentProvider', () => {
  const config = createConfig({ 'application.payments.paystackKey': 'paystack-secret' });
  const provider = new PaystackPaymentProvider(config);

  it('initializes payments with the expected payload', async () => {
    fetchMock.mockResolvedValue(
      createResponse({
        data: {
          authorization_url: 'https://paystack.test/redirect',
          reference: 'paystack-ref',
          id: 'paystack-transaction'
        }
      })
    );

    const result = await provider.initializePayment({
      amount: 50,
      currency: 'NGN',
      metadata: {
        email: 'donor@example.com',
        callbackUrl: 'https://example.com/callback',
        reference: 'paystack-ref'
      }
    });

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.paystack.co/transaction/initialize',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Bearer paystack-secret',
          'Content-Type': 'application/json'
        })
      })
    );

    const body = fetchMock.mock.calls[0][1]?.body as string;
    expect(JSON.parse(body)).toEqual({
      amount: 5000,
      currency: 'NGN',
      email: 'donor@example.com',
      reference: 'paystack-ref',
      callback_url: 'https://example.com/callback'
    });

    expect(result).toMatchObject({
      reference: 'paystack-ref',
      transactionId: 'paystack-transaction',
      status: 'pending',
      metadata: expect.objectContaining({
        authorizationUrl: 'https://paystack.test/redirect'
      })
    });
  });

  it('verifies payments and normalizes status', async () => {
    fetchMock.mockResolvedValue(
      createResponse({ data: { status: 'success', id: 'paystack-transaction', reference: 'paystack-ref' } })
    );

    const result = await provider.verifyPayment({ reference: 'paystack-ref', metadata: {} });

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.paystack.co/transaction/verify/paystack-ref',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({ Authorization: 'Bearer paystack-secret' })
      })
    );

    expect(result.status).toBe('completed');
    expect(result.transactionId).toBe('paystack-transaction');
    expect(result.metadata).toHaveProperty('verification');
  });

  it('creates refunds with the transaction reference', async () => {
    fetchMock.mockResolvedValue(createResponse({ data: { status: 'success' } }));

    const result = await provider.refund({ reference: 'paystack-ref', amount: 50, metadata: {} });

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.paystack.co/refund',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Bearer paystack-secret',
          'Content-Type': 'application/json'
        })
      })
    );

    const body = fetchMock.mock.calls[0][1]?.body as string;
    expect(JSON.parse(body)).toEqual({ transaction: 'paystack-ref', amount: 5000 });
    expect(result.metadata).toHaveProperty('refund');
  });

  it('throws when the Paystack API responds with an error', async () => {
    fetchMock.mockResolvedValue(createResponse({}, { ok: false, status: 400, text: 'bad request' }));

    await expect(
      provider.initializePayment({
        amount: 50,
        currency: 'NGN',
        metadata: {
          email: 'donor@example.com',
          callbackUrl: 'https://example.com/callback',
          reference: 'paystack-ref'
        }
      })
    ).rejects.toThrow(/Paystack initialize request failed/);
  });
});

describe('FincraPaymentProvider', () => {
  const config = createConfig({ 'application.payments.fincraKey': 'fincra-secret' });
  const provider = new FincraPaymentProvider(config);

  it('initializes checkout sessions', async () => {
    fetchMock.mockResolvedValue(
      createResponse({
        data: {
          checkoutUrl: 'https://fincra.test/checkout',
          transactionReference: 'fincra-ref',
          id: 'fincra-transaction'
        }
      })
    );

    const result = await provider.initializePayment({
      amount: 150.75,
      currency: 'USD',
      metadata: {
        email: 'donor@example.com',
        firstName: 'Jane',
        lastName: 'Doe',
        callbackUrl: 'https://example.com/fincra-callback',
        country: 'NG',
        reference: 'fincra-ref'
      }
    });

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.fincra.com/checkout/payments',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'api-key': 'fincra-secret',
          'Content-Type': 'application/json'
        })
      })
    );

    const body = JSON.parse(fetchMock.mock.calls[0][1]?.body as string) as Record<string, unknown>;
    expect(body).toMatchObject({
      amount: '150.75',
      currency: 'USD',
      reference: 'fincra-ref',
      redirectUrl: 'https://example.com/fincra-callback',
      customer: { firstName: 'Jane', lastName: 'Doe', email: 'donor@example.com' },
      paymentType: 'card',
      country: 'NG'
    });

    expect(result).toMatchObject({
      reference: 'fincra-ref',
      transactionId: 'fincra-transaction',
      status: 'pending',
      metadata: expect.objectContaining({ authorizationUrl: 'https://fincra.test/checkout' })
    });
  });

  it('verifies payments and maps the response', async () => {
    fetchMock.mockResolvedValue(
      createResponse({ data: { status: 'successful', id: 'fincra-transaction', transactionId: 'fincra-transaction' } })
    );

    const result = await provider.verifyPayment({ reference: 'fincra-ref', metadata: {} });

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.fincra.com/checkout/payments/fincra-ref',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({ 'api-key': 'fincra-secret' })
      })
    );

    expect(result.status).toBe('completed');
    expect(result.transactionId).toBe('fincra-transaction');
  });

  it('sends refund requests to the correct endpoint', async () => {
    fetchMock.mockResolvedValue(createResponse({ data: { status: 'success' } }));

    const result = await provider.refund({ reference: 'fincra-ref', amount: 100, metadata: {} });

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.fincra.com/transactions/fincra-ref/refund',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'api-key': 'fincra-secret',
          'Content-Type': 'application/json'
        })
      })
    );

    const body = JSON.parse(fetchMock.mock.calls[0][1]?.body as string) as Record<string, unknown>;
    expect(body).toEqual({ amount: '100.00' });
    expect(result.metadata).toHaveProperty('refund');
  });

  it('throws when Fincra responds with an error', async () => {
    fetchMock.mockResolvedValue(createResponse({}, { ok: false, status: 500, text: 'server error' }));

    await expect(
      provider.initializePayment({
        amount: 100,
        currency: 'USD',
        metadata: {
          email: 'donor@example.com',
          firstName: 'Jane',
          lastName: 'Doe',
          callbackUrl: 'https://example.com/fincra-callback'
        }
      })
    ).rejects.toThrow(/Fincra initialize request failed/);
  });
});

describe('StripePaymentProvider', () => {
  const config = createConfig({ 'application.payments.stripeKey': 'stripe-secret' });
  const provider = new StripePaymentProvider(config);

  it('initializes Stripe checkout sessions', async () => {
    fetchMock.mockResolvedValue(
      createResponse({ id: 'cs_test_123', url: 'https://stripe.test/checkout', payment_intent: 'pi_123' })
    );

    const result = await provider.initializePayment({
      amount: 75,
      currency: 'USD',
      metadata: {
        email: 'donor@example.com',
        successUrl: 'https://example.com/success',
        cancelUrl: 'https://example.com/cancel',
        reference: 'stripe-ref'
      }
    });

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.stripe.com/v1/checkout/sessions',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Bearer stripe-secret',
          'Content-Type': 'application/x-www-form-urlencoded'
        })
      })
    );

    const rawBody = fetchMock.mock.calls[0][1]?.body as URLSearchParams | string;
    const params = new URLSearchParams(rawBody instanceof URLSearchParams ? rawBody.toString() : String(rawBody));
    expect(params.get('client_reference_id')).toBe('stripe-ref');
    expect(params.get('customer_email')).toBe('donor@example.com');
    expect(params.get("line_items[0][price_data][unit_amount]")).toBe('7500');

    expect(result).toMatchObject({
      reference: 'cs_test_123',
      transactionId: 'pi_123',
      status: 'pending',
      metadata: expect.objectContaining({ authorizationUrl: 'https://stripe.test/checkout' })
    });
  });

  it('verifies Stripe sessions', async () => {
    fetchMock.mockResolvedValue(createResponse({ payment_status: 'paid', payment_intent: 'pi_123' }));

    const result = await provider.verifyPayment({ reference: 'cs_test_123', metadata: {} });

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.stripe.com/v1/checkout/sessions/cs_test_123',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({ Authorization: 'Bearer stripe-secret' })
      })
    );

    expect(result.status).toBe('completed');
    expect(result.transactionId).toBe('pi_123');
  });

  it('issues Stripe refunds using the payment intent', async () => {
    fetchMock.mockResolvedValue(createResponse({ id: 're_123', status: 'succeeded' }));

    const result = await provider.refund({ reference: 'pi_123', amount: 75, metadata: {} });

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.stripe.com/v1/refunds',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Bearer stripe-secret',
          'Content-Type': 'application/x-www-form-urlencoded'
        })
      })
    );

    const rawBody = fetchMock.mock.calls[0][1]?.body as URLSearchParams | string;
    const params = new URLSearchParams(rawBody instanceof URLSearchParams ? rawBody.toString() : String(rawBody));
    expect(params.get('payment_intent')).toBe('pi_123');
    expect(params.get('amount')).toBe('7500');
    expect(result.metadata).toHaveProperty('refund');
  });

  it('throws when Stripe returns an error', async () => {
    fetchMock.mockResolvedValue(createResponse({}, { ok: false, status: 401, text: 'unauthorized' }));

    await expect(
      provider.initializePayment({
        amount: 10,
        currency: 'USD',
        metadata: {
          email: 'donor@example.com',
          successUrl: 'https://example.com/success',
          cancelUrl: 'https://example.com/cancel'
        }
      })
    ).rejects.toThrow(/Stripe initialize request failed/);
  });
});

describe('FlutterwavePaymentProvider', () => {
  const config = createConfig({ 'application.payments.flutterwaveKey': 'flutterwave-secret' });
  const provider = new FlutterwavePaymentProvider(config);

  it('initializes Flutterwave payments', async () => {
    fetchMock.mockResolvedValue(
      createResponse({
        data: {
          link: 'https://flutterwave.test/checkout',
          tx_ref: 'flutterwave-ref',
          id: 'flutterwave-transaction'
        }
      })
    );

    const result = await provider.initializePayment({
      amount: 200,
      currency: 'NGN',
      metadata: {
        email: 'donor@example.com',
        callbackUrl: 'https://example.com/flutterwave-callback',
        reference: 'flutterwave-ref'
      }
    });

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.flutterwave.com/v3/payments',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Bearer flutterwave-secret',
          'Content-Type': 'application/json'
        })
      })
    );

    const body = JSON.parse(fetchMock.mock.calls[0][1]?.body as string) as Record<string, unknown>;
    expect(body).toMatchObject({
      tx_ref: 'flutterwave-ref',
      amount: '200.00',
      currency: 'NGN',
      redirect_url: 'https://example.com/flutterwave-callback',
      customer: { email: 'donor@example.com' }
    });

    expect(result).toMatchObject({
      reference: 'flutterwave-ref',
      transactionId: 'flutterwave-transaction',
      status: 'pending',
      metadata: expect.objectContaining({ authorizationUrl: 'https://flutterwave.test/checkout' })
    });
  });

  it('verifies Flutterwave transactions', async () => {
    fetchMock.mockResolvedValue(createResponse({ data: { status: 'successful', id: 'flutterwave-transaction' } }));

    const result = await provider.verifyPayment({ reference: 'flutterwave-ref', metadata: {} });

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.flutterwave.com/v3/transactions/flutterwave-ref/verify',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({ Authorization: 'Bearer flutterwave-secret' })
      })
    );

    expect(result.status).toBe('completed');
    expect(result.transactionId).toBe('flutterwave-transaction');
  });

  it('issues Flutterwave refunds', async () => {
    fetchMock.mockResolvedValue(createResponse({ data: { status: 'success' } }));

    const result = await provider.refund({ reference: 'flutterwave-ref', amount: 200, metadata: {} });

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.flutterwave.com/v3/transactions/flutterwave-ref/refund',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Bearer flutterwave-secret',
          'Content-Type': 'application/json'
        })
      })
    );

    const body = JSON.parse(fetchMock.mock.calls[0][1]?.body as string) as Record<string, unknown>;
    expect(body).toEqual({ amount: '200.00' });
    expect(result.metadata).toHaveProperty('refund');
  });

  it('throws when Flutterwave returns an error', async () => {
    fetchMock.mockResolvedValue(createResponse({}, { ok: false, status: 502, text: 'bad gateway' }));

    await expect(
      provider.initializePayment({
        amount: 200,
        currency: 'NGN',
        metadata: {
          email: 'donor@example.com',
          callbackUrl: 'https://example.com/flutterwave-callback'
        }
      })
    ).rejects.toThrow(/Flutterwave initialize request failed/);
  });
});
