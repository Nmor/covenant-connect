import { ConflictException, Injectable, NotFoundException } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import type { Provider, ProviderIdentity, UserAccount } from '@covenant-connect/shared';

import { PrismaService } from '../../prisma/prisma.service';

type Argon2Module = typeof import('argon2');

let argon2ModulePromise: Promise<Argon2Module> | null = null;

const loadArgon2 = async (): Promise<Argon2Module> => {
  if (!argon2ModulePromise) {
    argon2ModulePromise = import('argon2');
  }

  const module = await argon2ModulePromise;
  return (module as Argon2Module & { default?: Argon2Module }).default ?? module;
};

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
  constructor(private readonly prisma: PrismaService) {}

  async createAccount(input: CreateAccountInput): Promise<UserAccount> {
    const email = input.email.trim().toLowerCase();
    const existing = await this.prisma.user.findUnique({
      where: { email }
    });

    if (existing) {
      throw new ConflictException('An account already exists for this email');
    }

    const roles = input.roles && input.roles.length > 0 ? input.roles : ['member'];
    const passwordHash = input.password ? await (await loadArgon2()).hash(input.password) : undefined;
    const username = await this.generateUsername(email);

    const created = await this.prisma.user.create({
      data: {
        email,
        username,
        passwordHash,
        firstName: input.firstName,
        lastName: input.lastName,
        roles,
        isAdmin: roles.includes('admin'),
        providerIdentities: input.provider
          ? {
              create: this.toProviderCreate(input.provider)
            }
          : undefined
      },
      include: { providerIdentities: true }
    });

    return this.toDomainAccount(created);
  }

  async listAccounts(): Promise<UserAccount[]> {
    const users = await this.prisma.user.findMany({
      include: { providerIdentities: true },
      orderBy: { createdAt: 'asc' }
    });

    return users.map((user) => this.toDomainAccount(user));
  }

  async getAccountById(accountId: string): Promise<UserAccount | null> {
    const id = this.parseId(accountId);
    if (id === null) {
      return null;
    }

    const user = await this.prisma.user.findUnique({
      where: { id },
      include: { providerIdentities: true }
    });

    return user ? this.toDomainAccount(user) : null;
  }

  async getAccountByEmail(email: string): Promise<UserAccount | null> {
    const user = await this.prisma.user.findUnique({
      where: { email: email.trim().toLowerCase() },
      include: { providerIdentities: true }
    });

    return user ? this.toDomainAccount(user) : null;
  }

  async getAccountByProvider(provider: Provider, providerId: string): Promise<UserAccount | null> {
    const identity = await this.prisma.accountProvider.findUnique({
      where: {
        provider_providerId: {
          provider,
          providerId
        }
      },
      include: {
        user: {
          include: { providerIdentities: true }
        }
      }
    });

    return identity?.user ? this.toDomainAccount(identity.user) : null;
  }

  async updateAccount(accountId: string, input: UpdateAccountInput): Promise<UserAccount> {
    const id = this.parseId(accountId);
    if (id === null) {
      throw new NotFoundException('Account not found');
    }

    const data: Prisma.UserUpdateInput = {};

    if (input.firstName !== undefined) {
      data.firstName = input.firstName;
    }

    if (input.lastName !== undefined) {
      data.lastName = input.lastName;
    }

    if (input.avatarUrl !== undefined) {
      data.avatarUrl = input.avatarUrl ?? null;
    }

    if (input.roles !== undefined) {
      data.roles = input.roles;
      data.isAdmin = input.roles.includes('admin');
    }

    try {
      const updated = await this.prisma.user.update({
        where: { id },
        data,
        include: { providerIdentities: true }
      });

      return this.toDomainAccount(updated);
    } catch (error) {
      if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === 'P2025') {
        throw new NotFoundException('Account not found');
      }
      throw error;
    }
  }

  async linkProvider(accountId: string, provider: ProviderIdentity): Promise<UserAccount> {
    const id = this.parseId(accountId);
    if (id === null) {
      throw new NotFoundException('Account not found');
    }

    const existingAccount = await this.prisma.user.findUnique({
      where: { id }
    });

    if (!existingAccount) {
      throw new NotFoundException('Account not found');
    }

    const conflict = await this.prisma.accountProvider.findUnique({
      where: {
        provider_providerId: {
          provider: provider.provider,
          providerId: provider.providerId
        }
      }
    });

    if (conflict && conflict.userId !== id) {
      throw new ConflictException('This provider identity is already linked to another account');
    }

    await this.prisma.accountProvider.deleteMany({
      where: {
        userId: id,
        provider: provider.provider,
        NOT: {
          providerId: provider.providerId
        }
      }
    });

    await this.prisma.accountProvider.upsert({
      where: {
        provider_providerId: {
          provider: provider.provider,
          providerId: provider.providerId
        }
      },
      update: {
        userId: id,
        accessToken: provider.accessToken ?? null,
        refreshToken: provider.refreshToken ?? null,
        expiresAt: provider.expiresAt ?? null
      },
      create: {
        userId: id,
        provider: provider.provider,
        providerId: provider.providerId,
        accessToken: provider.accessToken ?? null,
        refreshToken: provider.refreshToken ?? null,
        expiresAt: provider.expiresAt ?? null
      }
    });

    const user = await this.prisma.user.findUnique({
      where: { id },
      include: { providerIdentities: true }
    });

    if (!user) {
      throw new NotFoundException('Account not found');
    }

    return this.toDomainAccount(user);
  }

  async verifyPassword(account: UserAccount, password: string): Promise<boolean> {
    if (!account.passwordHash) {
      return false;
    }

    const argon2 = await loadArgon2();
    return argon2.verify(account.passwordHash, password);
  }

  private toDomainAccount(
    user: Prisma.UserGetPayload<{ include: { providerIdentities: true } }>
  ): UserAccount {
    return {
      id: user.id.toString(),
      email: user.email,
      passwordHash: user.passwordHash ?? undefined,
      firstName: user.firstName ?? '',
      lastName: user.lastName ?? '',
      avatarUrl: user.avatarUrl ?? undefined,
      createdAt: user.createdAt,
      updatedAt: user.updatedAt,
      roles: user.roles,
      providers: user.providerIdentities.map((identity) => ({
        provider: identity.provider as Provider,
        providerId: identity.providerId,
        accessToken: identity.accessToken ?? undefined,
        refreshToken: identity.refreshToken ?? undefined,
        expiresAt: identity.expiresAt ?? undefined
      }))
    };
  }

  private async generateUsername(email: string): Promise<string> {
    const base = email.split('@')[0]?.replace(/[^a-z0-9]/gi, '').toLowerCase() || 'user';
    let candidate = base;
    let suffix = 1;

    // eslint-disable-next-line no-constant-condition
    while (true) {
      const existing = await this.prisma.user.findUnique({ where: { username: candidate } });
      if (!existing) {
        return candidate;
      }

      candidate = `${base}${suffix}`;
      suffix += 1;
    }
  }

  private toProviderCreate(provider: ProviderIdentity) {
    return {
      provider: provider.provider,
      providerId: provider.providerId,
      accessToken: provider.accessToken ?? null,
      refreshToken: provider.refreshToken ?? null,
      expiresAt: provider.expiresAt ?? null
    } satisfies Prisma.AccountProviderCreateWithoutUserInput;
  }

  private parseId(id: string): number | null {
    const parsed = Number.parseInt(id, 10);
    if (Number.isNaN(parsed)) {
      return null;
    }

    return parsed;
  }
}
