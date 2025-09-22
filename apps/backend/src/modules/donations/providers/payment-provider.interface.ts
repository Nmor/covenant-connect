import type { Donation } from '@covenant-connect/shared';

export type InitializePaymentInput = {
  amount: number;
  currency: string;
  metadata: Record<string, unknown>;
};

export type InitializePaymentResult = {
  reference: string;
  transactionId?: string | null;
  metadata: Record<string, unknown>;
  status?: Donation['status'];
};

export type VerifyPaymentInput = {
  reference: string;
  metadata: Record<string, unknown>;
};

export type VerifyPaymentResult = {
  status: Donation['status'];
  transactionId?: string | null;
  metadata: Record<string, unknown>;
};

export type RefundPaymentInput = {
  reference: string;
  amount: number;
  metadata: Record<string, unknown>;
};

export type RefundPaymentResult = {
  metadata: Record<string, unknown>;
};

export interface DonationPaymentProvider {
  initializePayment(input: InitializePaymentInput): Promise<InitializePaymentResult>;
  verifyPayment(input: VerifyPaymentInput): Promise<VerifyPaymentResult>;
  refund(input: RefundPaymentInput): Promise<RefundPaymentResult>;
}
