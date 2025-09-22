import { NotFoundException, ServiceUnavailableException } from '@nestjs/common';
import type { Prisma, EmailProvider as PrismaEmailProvider } from '@prisma/client';
import type { EmailProviderType } from '@covenant-connect/shared';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { EmailService } from '../src/modules/email/email.service';
import { EmailProviderError } from '../src/modules/email/providers/email-provider.error';
import type { EmailProviderFactory } from '../src/modules/email/providers/email-provider.factory';
import type { EmailProviderClient } from '../src/modules/email/providers/email-provider.interface';
import type { PrismaService } from '../src/prisma/prisma.service';

type PrismaEmailProviderRecord = Omit<PrismaEmailProvider, 'credentials'> & {
  credentials: Prisma.JsonValue;
};

type PrismaMock = Pick<PrismaService, 'emailProvider'> & {
  emailProvider: {
    findMany: ReturnType<typeof vi.fn>;
  };
};

describe('EmailService.sendMail', () => {
  let prisma: PrismaMock;
  let factory: { create: ReturnType<typeof vi.fn> };
  let service: EmailService;

  const createProviderRecord = (
    id: string,
    type: EmailProviderType,
    options: {
      isActive?: boolean;
      updatedAt?: Date;
      credentials?: Record<string, string>;
      name?: string;
    } = {}
  ): PrismaEmailProviderRecord => ({
    id,
    type,
    name: options.name ?? `${type}-provider`,
    credentials: (options.credentials ?? {}) as Prisma.JsonObject,
    isActive: options.isActive ?? false,
    createdAt: new Date('2024-01-01T00:00:00.000Z'),
    updatedAt: options.updatedAt ?? new Date('2024-01-01T00:00:00.000Z')
  });

  const stubClients = () => {
    const sesClient: EmailProviderClient = { sendEmail: vi.fn() };
    const mailgunClient: EmailProviderClient = { sendEmail: vi.fn() };
    const smtpClient: EmailProviderClient = { sendEmail: vi.fn() };

    factory.create.mockImplementation((type: EmailProviderType) => {
      switch (type) {
        case 'ses':
          return sesClient;
        case 'mailgun':
          return mailgunClient;
        case 'smtp':
          return smtpClient;
        default:
          throw new Error(`Unexpected provider type in test: ${type}`);
      }
    });

    return { sesClient, mailgunClient, smtpClient };
  };

  beforeEach(() => {
    prisma = {
      emailProvider: {
        findMany: vi.fn()
      }
    } as unknown as PrismaMock;

    factory = {
      create: vi.fn()
    };

    service = new EmailService(prisma as unknown as PrismaService, factory as unknown as EmailProviderFactory);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sends mail using the active provider when delivery succeeds', async () => {
    const providers = [
      createProviderRecord('ses-id', 'ses', { isActive: true, updatedAt: new Date('2024-01-03T00:00:00.000Z') }),
      createProviderRecord('mailgun-id', 'mailgun'),
      createProviderRecord('smtp-id', 'smtp')
    ];

    prisma.emailProvider.findMany.mockResolvedValue(providers as PrismaEmailProvider[]);

    const { sesClient, mailgunClient, smtpClient } = stubClients();
    (sesClient.sendEmail as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);

    const result = await service.sendMail({
      to: 'recipient@example.com',
      subject: 'Welcome',
      html: '<p>Hello there</p>'
    });

    expect(result.provider.id).toBe('ses-id');
    expect(sesClient.sendEmail).toHaveBeenCalledTimes(1);
    expect(mailgunClient.sendEmail).not.toHaveBeenCalled();
    expect(smtpClient.sendEmail).not.toHaveBeenCalled();

    const payload = (sesClient.sendEmail as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(payload).toMatchObject({
      to: ['recipient@example.com'],
      subject: 'Welcome',
      html: '<p>Hello there</p>'
    });
    expect(payload.text).toBe('Hello there');
  });

  it('falls back to the next configured provider when the active provider fails', async () => {
    const providers = [
      createProviderRecord('ses-id', 'ses', { isActive: true, updatedAt: new Date('2024-01-03T00:00:00.000Z') }),
      createProviderRecord('mailgun-id', 'mailgun', { updatedAt: new Date('2024-01-02T00:00:00.000Z') }),
      createProviderRecord('smtp-id', 'smtp', { updatedAt: new Date('2024-01-01T00:00:00.000Z') })
    ];

    prisma.emailProvider.findMany.mockResolvedValue(providers as PrismaEmailProvider[]);

    const { sesClient, mailgunClient, smtpClient } = stubClients();
    (sesClient.sendEmail as ReturnType<typeof vi.fn>).mockRejectedValue(
      EmailProviderError.transport('SES outage')
    );
    (mailgunClient.sendEmail as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);

    const result = await service.sendMail({
      to: 'fallback@example.com',
      subject: 'Fallback',
      html: '<strong>Important</strong>'
    });

    expect(result.provider.id).toBe('mailgun-id');
    expect(sesClient.sendEmail).toHaveBeenCalledTimes(1);
    expect(mailgunClient.sendEmail).toHaveBeenCalledTimes(1);
    expect(smtpClient.sendEmail).not.toHaveBeenCalled();
  });

  it('attempts all providers and throws when none succeed', async () => {
    const providers = [
      createProviderRecord('ses-id', 'ses', { isActive: true, updatedAt: new Date('2024-01-03T00:00:00.000Z') }),
      createProviderRecord('mailgun-id', 'mailgun', { updatedAt: new Date('2024-01-02T00:00:00.000Z') }),
      createProviderRecord('smtp-id', 'smtp', { updatedAt: new Date('2024-01-01T00:00:00.000Z') })
    ];

    prisma.emailProvider.findMany.mockResolvedValue(providers as PrismaEmailProvider[]);

    const { sesClient, mailgunClient, smtpClient } = stubClients();
    (sesClient.sendEmail as ReturnType<typeof vi.fn>).mockRejectedValue(
      EmailProviderError.transport('SES outage')
    );
    (mailgunClient.sendEmail as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('Mailgun timeout')
    );
    (smtpClient.sendEmail as ReturnType<typeof vi.fn>).mockRejectedValue(
      EmailProviderError.configuration('SMTP not configured')
    );

    await expect(
      service.sendMail({
        to: 'fail@example.com',
        subject: 'Failure',
        html: '<em>Test</em>'
      })
    ).rejects.toBeInstanceOf(ServiceUnavailableException);

    expect(sesClient.sendEmail).toHaveBeenCalledTimes(1);
    expect(mailgunClient.sendEmail).toHaveBeenCalledTimes(1);
    expect(smtpClient.sendEmail).toHaveBeenCalledTimes(1);
  });

  it('throws when no providers are configured', async () => {
    prisma.emailProvider.findMany.mockResolvedValue([]);

    await expect(
      service.sendMail({
        to: 'none@example.com',
        subject: 'Unavailable',
        html: '<p>Missing</p>'
      })
    ).rejects.toBeInstanceOf(NotFoundException);
  });
});
