import { ConflictException, Injectable, NotFoundException } from '@nestjs/common';
import argon2 from 'argon2';

import type { Provider, ProviderIdentity, UserAccount } from '@covenant-connect/shared';

import { AccountsRepository } from './accounts.repository';

type CreateAccountInput = {
  email: string;
  password?: string;
  firstName: string;
  lastName: string;
  roles?: string[];
  provider?: ProviderIdentity;
};

type UpdateAccountInput = Partial<Pick<UserAccount, 'firstName' | 'lastName' | 'avatarUrl' | 'roles'>>;

@Injectable()
export class AccountsService {
  constructor(private readonly repository: AccountsRepository) {}

  async createAccount(input: CreateAccountInput): Promise<UserAccount> {
    const existing = await this.repository.findByEmail(input.email);
    if (existing) {
      throw new ConflictException('An account already exists for this email');
    }

    const passwordHash = input.password ? await argon2.hash(input.password) : undefined;

    return this.repository.create({
      email: input.email,
      passwordHash,
      firstName: input.firstName,
      lastName: input.lastName,
      roles: input.roles ?? ['member'],
      providers: input.provider ? [input.provider] : []
    });
  }

  async listAccounts(): Promise<UserAccount[]> {
    return this.repository.list();
  }

  async getAccountById(accountId: string): Promise<UserAccount | null> {
    return this.repository.findById(accountId);
  }

  async getAccountByEmail(email: string): Promise<UserAccount | null> {
    return this.repository.findByEmail(email);
  }

  async getAccountByProvider(provider: Provider, providerId: string): Promise<UserAccount | null> {
    return this.repository.findByProvider(provider, providerId);
  }

  async updateAccount(accountId: string, input: UpdateAccountInput): Promise<UserAccount> {
    const account = await this.repository.update(accountId, input);
    if (!account) {
      throw new NotFoundException('Account not found');
    }

    return account;
  }

  async linkProvider(accountId: string, provider: ProviderIdentity): Promise<UserAccount> {
    const account = await this.repository.linkProvider(accountId, provider);
    if (!account) {
      throw new NotFoundException('Account not found');
    }

    return account;
  }

  async verifyPassword(account: UserAccount, password: string): Promise<boolean> {
    if (!account.passwordHash) {
      return false;
    }

    return argon2.verify(account.passwordHash, password);
  }
}
