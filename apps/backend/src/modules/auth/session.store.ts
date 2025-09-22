import { Injectable } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { randomBytes } from 'node:crypto';

import { PrismaService } from '../../prisma/prisma.service';

export type Session = {
  token: string;
  userId: string;
  createdAt: Date;
  expiresAt: Date;
};

@Injectable()
export class SessionStore {
  constructor(private readonly prisma: PrismaService) {}

  async create(userId: string, ttlSeconds: number): Promise<Session> {
    const token = randomBytes(48).toString('hex');
    const now = new Date();
    const expiresAt = new Date(now.getTime() + ttlSeconds * 1000);
    const parsedUserId = this.parseId(userId);

    const created = await this.prisma.session.create({
      data: {
        token,
        userId: parsedUserId,
        createdAt: now,
        expiresAt
      }
    });

    return this.toDomain(created);
  }

  async get(token: string): Promise<Session | null> {
    const record = await this.prisma.session.findUnique({ where: { token } });
    if (!record) {
      return null;
    }

    if (record.expiresAt.getTime() < Date.now()) {
      await this.prisma.session.delete({ where: { token } });
      return null;
    }

    return this.toDomain(record);
  }

  async revoke(token: string): Promise<void> {
    try {
      await this.prisma.session.delete({ where: { token } });
    } catch (error) {
      if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === 'P2025') {
        return;
      }

      throw error;
    }
  }

  private toDomain(record: { token: string; userId: number; createdAt: Date; expiresAt: Date }): Session {
    return {
      token: record.token,
      userId: record.userId.toString(),
      createdAt: record.createdAt,
      expiresAt: record.expiresAt
    };
  }

  private parseId(id: string): number {
    const parsed = Number.parseInt(id, 10);
    if (Number.isNaN(parsed)) {
      throw new Error('Invalid session user identifier');
    }

    return parsed;
  }
}
