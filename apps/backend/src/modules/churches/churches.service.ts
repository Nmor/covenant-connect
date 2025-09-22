import { Injectable, NotFoundException } from '@nestjs/common';
import { randomUUID } from 'node:crypto';
import type { Church } from '@covenant-connect/shared';

type CreateChurchInput = {
  name: string;
  timezone: string;
  country?: string;
  state?: string;
  city?: string;
  settings?: Record<string, unknown>;
};

type UpdateChurchInput = Partial<CreateChurchInput>;

@Injectable()
export class ChurchesService {
  private readonly churches = new Map<string, Church>();

  async create(input: CreateChurchInput): Promise<Church> {
    const now = new Date();
    const church: Church = {
      id: randomUUID(),
      name: input.name,
      timezone: input.timezone,
      country: input.country,
      state: input.state,
      city: input.city,
      settings: input.settings ?? {},
      createdAt: now,
      updatedAt: now
    };

    this.churches.set(church.id, church);
    return church;
  }

  async list(): Promise<Church[]> {
    return Array.from(this.churches.values());
  }

  async getById(churchId: string): Promise<Church> {
    const church = this.churches.get(churchId);
    if (!church) {
      throw new NotFoundException('Church not found');
    }

    return church;
  }

  async update(churchId: string, input: UpdateChurchInput): Promise<Church> {
    const existing = await this.getById(churchId);

    const updated: Church = {
      ...existing,
      ...input,
      settings: { ...existing.settings, ...(input.settings ?? {}) },
      updatedAt: new Date()
    };

    this.churches.set(updated.id, updated);
    return updated;
  }
}
