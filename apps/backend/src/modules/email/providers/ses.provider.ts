import { SESClient, SendEmailCommand } from '@aws-sdk/client-ses';

import { EmailProviderError } from './email-provider.error';
import type { EmailProviderClient, SendEmailPayload } from './email-provider.interface';
import { getString, cloneCredentials } from './provider.utils';

type SesClient = Pick<SESClient, 'send'>;

type SesProviderOptions = {
  client?: SesClient;
};

export class SesEmailProvider implements EmailProviderClient {
  private readonly credentials: Record<string, string>;
  private readonly client: SesClient | undefined;

  constructor(credentials: Record<string, string>, options: SesProviderOptions = {}) {
    this.credentials = cloneCredentials(credentials);
    this.client = options.client;
  }

  async sendEmail(payload: SendEmailPayload): Promise<void> {
    const accessKeyId = getString(this.credentials, 'access_key_id');
    const secretAccessKey = getString(this.credentials, 'secret_access_key');
    const region = getString(this.credentials, 'region') || 'us-east-1';
    const sender = this.resolveSender(payload.from);

    if (!accessKeyId || !secretAccessKey) {
      throw EmailProviderError.configuration('AWS SES integration is missing required credentials');
    }

    const client = this.client ?? new SESClient({
      region,
      credentials: {
        accessKeyId,
        secretAccessKey
      }
    });

    const command = new SendEmailCommand({
      Source: sender,
      Destination: {
        ToAddresses: payload.to
      },
      Message: {
        Subject: { Data: payload.subject },
        Body: {
          Text: { Data: payload.text }
        }
      }
    });

    if (payload.html) {
      command.input.Message?.Body && (command.input.Message.Body.Html = { Data: payload.html });
    }

    const configurationSet = getString(this.credentials, 'configuration_set');
    if (configurationSet) {
      command.input.ConfigurationSetName = configurationSet;
    }

    const replyTo = payload.replyTo || getString(this.credentials, 'reply_to');
    if (replyTo) {
      command.input.ReplyToAddresses = [replyTo];
    }

    try {
      await client.send(command);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      throw EmailProviderError.transport(`AWS SES send_email failed: ${message}`, error);
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

    throw EmailProviderError.configuration('AWS SES integration requires a sender email address');
  }
}
