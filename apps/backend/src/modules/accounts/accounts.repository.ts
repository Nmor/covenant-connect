import { Injectable } from '@nestjs/common';
import { randomUUID } from 'node:crypto';
import type { Provider, ProviderIdentity, UserAccount } from '@covenant-connect/shared';

@Injectable()
export class AccountsRepository {
  private readonly accounts = new Map<string, UserAccount>();

  async list(): Promise<UserAccount[]> {
    return Array.from(this.accounts.values());
  }

  async findById(id: string): Promise<UserAccount | null> {
    return this.accounts.get(id) ?? null;
  }

  async findByEmail(email: string): Promise<UserAccount | null> {
    const normalised = email.toLowerCase();
    return (
      Array.from(this.accounts.values()).find((account) => account.email.toLowerCase() === normalised) ??
      null
    );
  }

  async findByProvider(provider: Provider, providerId: string): Promise<UserAccount | null> {
    return (
      Array.from(this.accounts.values()).find((account) =>
        account.providers.some((identity) => identity.provider === provider && identity.providerId === providerId)
      ) ?? null
    );
  }

  async create(data: Omit<UserAccount, 'id' | 'createdAt' | 'updatedAt'>): Promise<UserAccount> {
    const now = new Date();
    const account: UserAccount = {
      id: randomUUID(),
      createdAt: now,
      updatedAt: now,
      ...data
    };

    this.accounts.set(account.id, account);
    return account;
  }

  async update(accountId: string, data: Partial<UserAccount>): Promise<UserAccount | null> {
    const account = await this.findById(accountId);
    if (!account) {
      return null;
    }

    const updated: UserAccount = {
      ...account,
      ...data,
      updatedAt: new Date()
    };

    this.accounts.set(updated.id, updated);
    return updated;
  }

  async linkProvider(accountId: string, provider: ProviderIdentity): Promise<UserAccount | null> {
    const account = await this.findById(accountId);
    if (!account) {
      return null;
    }

    const others = account.providers.filter((identity) => identity.provider !== provider.provider);
    const updated: UserAccount = {
      ...account,
      providers: [...others, provider],
      updatedAt: new Date()
    };

    this.accounts.set(updated.id, updated);
    return updated;
  }
}
