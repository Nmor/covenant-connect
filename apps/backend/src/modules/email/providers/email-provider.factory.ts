import { Injectable } from '@nestjs/common';
import type { EmailProviderType } from '@covenant-connect/shared';

import type { EmailProviderClient } from './email-provider.interface';
import { MailgunEmailProvider } from './mailgun.provider';
import { SesEmailProvider } from './ses.provider';
import { SmtpEmailProvider } from './smtp.provider';

@Injectable()
export class EmailProviderFactory {
  create(type: EmailProviderType, credentials: Record<string, string>): EmailProviderClient {
    switch (type) {
      case 'ses':
        return new SesEmailProvider(credentials);
      case 'mailgun':
        return new MailgunEmailProvider(credentials);
      case 'smtp':
        return new SmtpEmailProvider(credentials);
      default:
        throw new Error(`Unsupported email provider type: ${type}`);
    }
  }
}
