import { EmailProviderError } from './email-provider.error';
import type { EmailProviderClient, SendEmailPayload } from './email-provider.interface';
import { cloneCredentials, getString } from './provider.utils';

type FetchImplementation = (
  input: string,
  init: {
    method: string;
    headers: Record<string, string>;
    body: URLSearchParams;
    signal?: AbortSignal;
  }
) => Promise<Response>;

type MailgunProviderOptions = {
  fetchImpl?: FetchImplementation;
  timeoutMs?: number;
};

export class MailgunEmailProvider implements EmailProviderClient {
  private readonly credentials: Record<string, string>;
  private readonly fetchImpl: FetchImplementation;
  private readonly timeoutMs: number;

  constructor(credentials: Record<string, string>, options: MailgunProviderOptions = {}) {
    this.credentials = cloneCredentials(credentials);
    const resolvedFetch = options.fetchImpl ?? (globalThis.fetch as FetchImplementation | undefined);
    if (!resolvedFetch) {
      throw EmailProviderError.configuration('Mailgun provider requires a fetch implementation');
    }

    this.fetchImpl = resolvedFetch as FetchImplementation;
    this.timeoutMs = options.timeoutMs ?? 10_000;
  }

  async sendEmail(payload: SendEmailPayload): Promise<void> {
    const apiKey = getString(this.credentials, 'api_key');
    const domain = getString(this.credentials, 'domain');
    const baseUrl = getString(this.credentials, 'base_url') || 'https://api.mailgun.net/v3';
    const sender = this.resolveSender(payload.from);

    if (!apiKey || !domain) {
      throw EmailProviderError.configuration('Mailgun integration is missing required configuration');
    }

    const url = `${baseUrl.replace(/\/$/, '')}/${domain}/messages`;
    const data = new URLSearchParams();
    data.append('from', sender);
    for (const recipient of payload.to) {
      data.append('to', recipient);
    }
    data.append('subject', payload.subject);
    data.append('text', payload.text);
    if (payload.html) {
      data.append('html', payload.html);
    }

    const replyTo = payload.replyTo || getString(this.credentials, 'reply_to');
    if (replyTo) {
      data.append('h:Reply-To', replyTo);
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const response = await this.fetchImpl(url, {
        method: 'POST',
        headers: {
          Authorization: `Basic ${Buffer.from(`api:${apiKey}`).toString('base64')}`
        },
        body: data,
        signal: controller.signal
      });

      if (!response.ok) {
        const body = await response.text();
        throw EmailProviderError.transport(
          `Mailgun request failed with ${response.status}: ${body}`
        );
      }
    } catch (error) {
      if (error instanceof EmailProviderError) {
        throw error;
      }

      const message = error instanceof Error ? error.message : 'Unknown error';
      throw EmailProviderError.transport(`Mailgun request failed: ${message}`, error);
    } finally {
      clearTimeout(timeout);
    }
  }

  private resolveSender(override?: string): string {
    if (override && override.trim()) {
      return override.trim();
    }

    const configured = getString(this.credentials, 'sender_email');
    if (configured) {
      return configured;
    }

    throw EmailProviderError.configuration('Mailgun integration requires a sender email address');
  }
}
