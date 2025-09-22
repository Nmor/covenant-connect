import type { EmailProviderType } from '@covenant-connect/shared';

export type SendEmailPayload = {
  to: string[];
  subject: string;
  text: string;
  html?: string;
  from?: string;
  replyTo?: string;
};

export interface EmailProviderClient {
  sendEmail(payload: SendEmailPayload): Promise<void>;
}

export interface EmailProviderFactoryContract {
  create(type: EmailProviderType, credentials: Record<string, string>): EmailProviderClient;
}
