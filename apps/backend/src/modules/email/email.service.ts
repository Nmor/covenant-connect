import { Injectable, Logger, NotFoundException } from '@nestjs/common';
import { randomUUID } from 'node:crypto';
import type { EmailProvider, EmailProviderType } from '@covenant-connect/shared';

type UpsertProviderInput = {
  type: EmailProviderType;
  name: string;
  credentials: Record<string, string>;
  isActive?: boolean;
};

@Injectable()
export class EmailService {
  private readonly logger = new Logger(EmailService.name);
  private readonly providers = new Map<string, EmailProvider>();

  async listProviders(): Promise<EmailProvider[]> {
    return Array.from(this.providers.values());
  }

  async upsertProvider(id: string | null, input: UpsertProviderInput): Promise<EmailProvider> {
    const now = new Date();
    const provider: EmailProvider = {
      id: id ?? randomUUID(),
      type: input.type,
      name: input.name,
      credentials: input.credentials,
      isActive: input.isActive ?? true,
      createdAt: now,
      updatedAt: now
    };

    this.providers.set(provider.id, provider);
    return provider;
  }

  async activate(providerId: string): Promise<EmailProvider> {
    const provider = this.providers.get(providerId);
    if (!provider) {
      throw new NotFoundException('Email provider not found');
    }

    for (const existing of this.providers.values()) {
      existing.isActive = existing.id === providerId;
    }

    provider.updatedAt = new Date();
    this.providers.set(provider.id, provider);
    return provider;
  }

  async sendMail(to: string, subject: string, html: string): Promise<{ provider: EmailProvider }> {
    const activeProvider = Array.from(this.providers.values()).find((provider) => provider.isActive);
    if (!activeProvider) {
      throw new NotFoundException('No active email provider configured');
    }

    // TODO: integrate with actual provider SDKs; this is a placeholder implementation.
    this.logger.log(
      `Dispatching email via ${activeProvider.name} to ${to} with subject "${subject}" (payload length: ${html.length})`
    );
    return { provider: activeProvider };
  }
}
