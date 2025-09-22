import type { TransportOptions, Transporter } from 'nodemailer';
import nodemailer from 'nodemailer';

import { EmailProviderError } from './email-provider.error';
import type { EmailProviderClient, SendEmailPayload } from './email-provider.interface';
import { cloneCredentials, getString, parseBoolean } from './provider.utils';

type TransportFactory = (options: TransportOptions) => Transporter;

type SmtpProviderOptions = {
  transportFactory?: TransportFactory;
};

export class SmtpEmailProvider implements EmailProviderClient {
  private readonly credentials: Record<string, string>;
  private readonly transportFactory: TransportFactory;

  constructor(credentials: Record<string, string>, options: SmtpProviderOptions = {}) {
    this.credentials = cloneCredentials(credentials);
    this.transportFactory = options.transportFactory ?? ((config) => nodemailer.createTransport(config));
  }

  async sendEmail(payload: SendEmailPayload): Promise<void> {
    const host = getString(this.credentials, 'server');
    const portValue = getString(this.credentials, 'port') || '587';
    const username = getString(this.credentials, 'username');
    const password = getString(this.credentials, 'password');
    const sender = this.resolveSender(payload.from);
    const useTls = parseBoolean(this.credentials['use_tls']);

    if (!host) {
      throw EmailProviderError.configuration('SMTP integration requires a server hostname');
    }

    if (!sender) {
      throw EmailProviderError.configuration('SMTP integration requires a sender email address');
    }

    const port = Number.parseInt(portValue, 10);
    if (Number.isNaN(port)) {
      throw EmailProviderError.configuration('SMTP port must be an integer');
    }

    const transporter = this.transportFactory({
      host,
      port,
      secure: port === 465,
      requireTLS: useTls,
      auth: username && password ? { user: username, pass: password } : undefined
    });

    try {
      await transporter.sendMail({
        from: sender,
        to: payload.to.join(', '),
        subject: payload.subject,
        text: payload.text,
        html: payload.html,
        replyTo: payload.replyTo || getString(this.credentials, 'reply_to') || undefined
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      throw EmailProviderError.transport(`SMTP sendMail failed: ${message}`, error);
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

    throw EmailProviderError.configuration('SMTP integration requires a sender email address');
  }
}
