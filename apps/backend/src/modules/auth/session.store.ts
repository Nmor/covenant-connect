import { Injectable } from '@nestjs/common';
import { randomBytes } from 'node:crypto';

export type Session = {
  token: string;
  userId: string;
  createdAt: Date;
  expiresAt: Date;
};

@Injectable()
export class SessionStore {
  private readonly sessions = new Map<string, Session>();

  create(userId: string, ttlSeconds: number): Session {
    const token = randomBytes(48).toString('hex');
    const now = new Date();
    const expiresAt = new Date(now.getTime() + ttlSeconds * 1000);

    const session: Session = {
      token,
      userId,
      createdAt: now,
      expiresAt
    };

    this.sessions.set(token, session);
    return session;
  }

  get(token: string): Session | null {
    const session = this.sessions.get(token);
    if (!session) {
      return null;
    }

    if (session.expiresAt.getTime() < Date.now()) {
      this.sessions.delete(token);
      return null;
    }

    return session;
  }

  revoke(token: string): void {
    this.sessions.delete(token);
  }
}
