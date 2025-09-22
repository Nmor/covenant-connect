import {
  BadRequestException,
  Injectable,
  Logger,
  NotFoundException,
  ServiceUnavailableException
} from '@nestjs/common';
import type { EmailProvider, EmailProviderType } from '@covenant-connect/shared';
import type { EmailProvider as PrismaEmailProvider, Prisma } from '@prisma/client';

import { PrismaService } from '../../prisma/prisma.service';
import { EmailProviderError } from './providers/email-provider.error';
import { EmailProviderFactory } from './providers/email-provider.factory';
import type { SendEmailPayload } from './providers/email-provider.interface';

type UpsertProviderInput = {
  type: EmailProviderType;
  name: string;
  credentials: Record<string, string>;
  isActive?: boolean;
};

type SendMailInput = {
  to: string | string[];
  subject: string;
  html?: string;
  text?: string;
  from?: string;
  replyTo?: string;
};

type ProviderAttemptError = {
  provider: EmailProvider;
  error: EmailProviderError;
};

@Injectable()
export class EmailService {
  private readonly logger = new Logger(EmailService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly providerFactory: EmailProviderFactory
  ) {}

  async listProviders(): Promise<EmailProvider[]> {
    const providers = await this.prisma.emailProvider.findMany({
      orderBy: {
        createdAt: 'asc'
      }
    });

    return providers.map((provider) => this.mapProvider(provider));
  }

  async upsertProvider(id: string | null, input: UpsertProviderInput): Promise<EmailProvider> {
    const name = input.name.trim();
    const credentials = this.sanitiseCredentials(input.credentials);
    const shouldActivate = input.isActive === true;
    const shouldDeactivate = input.isActive === false;

    if (!name) {
      throw new BadRequestException('Provider name is required');
    }

    if (id) {
      return this.prisma.$transaction(async (tx) => {
        const existing = await tx.emailProvider.findUnique({ where: { id } });
        if (!existing) {
          throw new NotFoundException('Email provider not found');
        }

        const data: Prisma.EmailProviderUpdateInput = {
          type: input.type,
          name,
          credentials
        };

        if (shouldActivate || shouldDeactivate) {
          data.isActive = shouldActivate;
        }

        let updated = await tx.emailProvider.update({
          where: { id },
          data
        });

        if (shouldActivate) {
          await tx.emailProvider.updateMany({
            where: { id: { not: id } },
            data: { isActive: false }
          });
          updated = await tx.emailProvider.update({
            where: { id },
            data: { isActive: true }
          });
        }

        return this.mapProvider(updated);
      });
    }

    return this.prisma.$transaction(async (tx) => {
      let created = await tx.emailProvider.create({
        data: {
          type: input.type,
          name,
          credentials,
          isActive: shouldActivate
        }
      });

      if (shouldActivate) {
        await tx.emailProvider.updateMany({
          where: { id: { not: created.id } },
          data: { isActive: false }
        });
        created = await tx.emailProvider.update({
          where: { id: created.id },
          data: { isActive: true }
        });
      }

      return this.mapProvider(created);
    });
  }

  async activate(providerId: string): Promise<EmailProvider> {
    return this.prisma.$transaction(async (tx) => {
      const provider = await tx.emailProvider.findUnique({ where: { id: providerId } });
      if (!provider) {
        throw new NotFoundException('Email provider not found');
      }

      await tx.emailProvider.updateMany({
        where: { id: { not: providerId } },
        data: { isActive: false }
      });

      const updated = await tx.emailProvider.update({
        where: { id: providerId },
        data: { isActive: true }
      });

      return this.mapProvider(updated);
    });
  }

  async sendMail(input: SendMailInput): Promise<{ provider: EmailProvider }> {
    const recipients = this.normaliseRecipients(input.to);
    const subject = (input.subject ?? '').trim();
    const html = input.html?.trim() || undefined;

    if (!subject) {
      throw new BadRequestException('Email subject is required');
    }

    const text = this.resolvePlainText(input.text, html, subject);

    const providers = await this.prisma.emailProvider.findMany({
      orderBy: [
        { isActive: 'desc' },
        { updatedAt: 'desc' },
        { createdAt: 'asc' }
      ]
    });

    if (providers.length === 0) {
      throw new NotFoundException('No email providers are configured');
    }

    const attempts: ProviderAttemptError[] = [];
    const payload: SendEmailPayload = {
      to: recipients,
      subject,
      text,
      html,
      from: input.from?.trim() || undefined,
      replyTo: input.replyTo?.trim() || undefined
    };

    for (const record of providers) {
      const provider = this.mapProvider(record);
      const adapter = this.providerFactory.create(provider.type, provider.credentials);

      try {
        await adapter.sendEmail(payload);
        this.logger.log(
          `Email delivered via ${provider.name} (${provider.type}) to ${payload.to.join(', ')}`
        );
        return { provider };
      } catch (error) {
        const normalised = this.normaliseError(error);
        attempts.push({ provider, error: normalised });
        this.logger.warn(
          `Failed to send email via ${provider.name} (${provider.type}): ${normalised.message}`
        );
      }
    }

    const details = attempts
      .map((attempt) => `${attempt.provider.name} (${attempt.provider.type}): ${attempt.error.message}`)
      .join('; ');

    throw new ServiceUnavailableException(
      details ? `Unable to send email using configured providers. ${details}` : 'Unable to send email'
    );
  }

  private mapProvider(record: PrismaEmailProvider): EmailProvider {
    return {
      id: record.id,
      type: this.castProviderType(record.type),
      name: record.name,
      credentials: this.parseCredentials(record.credentials),
      isActive: record.isActive,
      createdAt: record.createdAt,
      updatedAt: record.updatedAt
    };
  }

  private castProviderType(value: string): EmailProviderType {
    if (value === 'ses' || value === 'mailgun' || value === 'smtp') {
      return value;
    }

    this.logger.error(`Encountered unsupported email provider type: ${value}`);
    throw new BadRequestException(`Unsupported email provider type: ${value}`);
  }

  private parseCredentials(value: Prisma.JsonValue | null): Record<string, string> {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      return {};
    }

    return Object.entries(value as Record<string, unknown>).reduce<Record<string, string>>(
      (acc, [key, entry]) => {
        if (typeof entry === 'string') {
          acc[key] = entry;
        } else if (entry != null) {
          acc[key] = String(entry);
        }

        return acc;
      },
      {}
    );
  }

  private sanitiseCredentials(credentials: Record<string, string>): Record<string, string> {
    return Object.entries(credentials).reduce<Record<string, string>>((acc, [key, value]) => {
      if (typeof value === 'string') {
        acc[key] = value.trim();
      }
      return acc;
    }, {});
  }

  private normaliseRecipients(to: string | string[]): string[] {
    if (!Array.isArray(to) && typeof to !== 'string') {
      throw new BadRequestException('At least one recipient email address is required');
    }

    const values = Array.isArray(to) ? to : to.split(',');
    const recipients = values
      .map((value) => value.trim())
      .filter((value) => value.length > 0);

    const unique = Array.from(new Set(recipients));
    if (unique.length === 0) {
      throw new BadRequestException('At least one recipient email address is required');
    }

    return unique;
  }

  private resolvePlainText(text: string | undefined, html: string | undefined, subject: string): string {
    const trimmed = text?.trim();
    if (trimmed) {
      return trimmed;
    }

    if (html) {
      const stripped = html.replace(/<[^>]+>/g, ' ');
      const normalised = stripped.replace(/\s+/g, ' ').trim();
      if (normalised) {
        return normalised;
      }
    }

    return subject;
  }

  private normaliseError(error: unknown): EmailProviderError {
    if (error instanceof EmailProviderError) {
      return error;
    }

    if (error instanceof Error) {
      return EmailProviderError.unknown(error.message, error);
    }

    return EmailProviderError.unknown('Unknown error', error);
  }
}
