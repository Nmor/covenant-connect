import { Injectable, NotFoundException } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import type { Event as EventModel } from '@prisma/client';
import { randomUUID } from 'node:crypto';
import type { Event, EventSegment, PaginatedResult, Pagination } from '@covenant-connect/shared';

import { PrismaService } from '../../prisma/prisma.service';

type CreateEventInput = {
  title: string;
  description?: string;
  startsAt: Date;
  endsAt: Date;
  timezone: string;
  recurrenceRule?: string;
  tags?: string[];
  location: string;
  segments?: Omit<EventSegment, 'id'>[];
};

type UpdateEventInput = Partial<CreateEventInput> & {
  segments?: Array<Partial<EventSegment> & Omit<EventSegment, 'id'>>;
};

@Injectable()
export class EventsService {
  constructor(private readonly prisma: PrismaService) {}

  async create(input: CreateEventInput): Promise<Event> {
    const segments = this.ensureSegmentsWithIds(input.segments ?? []);
    const created = await this.prisma.event.create({
      data: {
        title: input.title,
        description: input.description,
        startDate: input.startsAt,
        endDate: input.endsAt,
        timezone: input.timezone,
        recurrenceRule: input.recurrenceRule,
        serviceSegments: segments,
        ministryTags: input.tags ?? [],
        location: input.location
      }
    });

    return this.toDomain(created);
  }

  async list(pagination: Pagination): Promise<PaginatedResult<Event>> {
    const skip = (pagination.page - 1) * pagination.pageSize;
    const take = pagination.pageSize;

    const [events, total] = await this.prisma.$transaction([
      this.prisma.event.findMany({
        skip,
        take,
        orderBy: { startDate: 'asc' }
      }),
      this.prisma.event.count()
    ]);

    return {
      data: events.map((event) => this.toDomain(event)),
      total,
      page: pagination.page,
      pageSize: pagination.pageSize
    };
  }

  async update(eventId: string, input: UpdateEventInput): Promise<Event> {
    const id = this.parseId(eventId);
    const existing = await this.prisma.event.findUnique({ where: { id } });
    if (!existing) {
      throw new NotFoundException('Event not found');
    }

    const segments = input.segments
      ? this.ensureSegmentsWithIds(input.segments)
      : this.parseSegments(existing.serviceSegments);

    const updated = await this.prisma.event.update({
      where: { id },
      data: {
        title: input.title ?? existing.title,
        description: input.description ?? existing.description,
        startDate: input.startsAt ?? existing.startDate,
        endDate: input.endsAt ?? existing.endDate,
        timezone: input.timezone ?? existing.timezone,
        recurrenceRule: input.recurrenceRule ?? existing.recurrenceRule,
        serviceSegments: segments,
        ministryTags: input.tags ?? (existing.ministryTags as string[]),
        location: input.location ?? existing.location
      }
    });

    return this.toDomain(updated);
  }

  async toICalendar(): Promise<string> {
    const events = await this.prisma.event.findMany();
    const lines = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//Covenant Connect//EN'
    ];

    for (const event of events) {
      const domain = this.toDomain(event);
      lines.push('BEGIN:VEVENT');
      lines.push(`UID:${domain.id}`);
      lines.push(`SUMMARY:${domain.title}`);
      if (domain.description) {
        lines.push(`DESCRIPTION:${domain.description}`);
      }
      lines.push(`DTSTART:${this.formatDate(domain.startsAt)}`);
      lines.push(`DTEND:${this.formatDate(domain.endsAt)}`);
      if (domain.location) {
        lines.push(`LOCATION:${domain.location}`);
      }
      if (domain.recurrenceRule) {
        lines.push(`RRULE:${domain.recurrenceRule}`);
      }
      lines.push('END:VEVENT');
    }

    lines.push('END:VCALENDAR');
    return lines.join('\n');
  }

  private toDomain(event: EventModel): Event {
    return {
      id: event.id.toString(),
      title: event.title,
      description: event.description ?? undefined,
      startsAt: event.startDate,
      endsAt: event.endDate,
      timezone: event.timezone,
      recurrenceRule: event.recurrenceRule ?? undefined,
      segments: this.parseSegments(event.serviceSegments),
      tags: (event.ministryTags as string[]) ?? [],
      location: event.location ?? undefined,
      createdAt: event.createdAt,
      updatedAt: event.updatedAt
    };
  }

  private parseSegments(value: Prisma.JsonValue): EventSegment[] {
    if (!Array.isArray(value)) {
      return [];
    }

    return value
      .map((item) => {
        if (typeof item !== 'object' || item === null) {
          return null;
        }

        const segment = item as Record<string, unknown>;
        const id = typeof segment.id === 'string' ? segment.id : randomUUID();
        const name = typeof segment.name === 'string' ? segment.name : 'Segment';
        const startOffsetMinutes = Number.isFinite(Number(segment.startOffsetMinutes))
          ? Number(segment.startOffsetMinutes)
          : 0;
        const durationMinutes = Number.isFinite(Number(segment.durationMinutes))
          ? Number(segment.durationMinutes)
          : 0;
        const ownerId = typeof segment.ownerId === 'string' ? segment.ownerId : null;

        return {
          id,
          name,
          startOffsetMinutes,
          durationMinutes,
          ownerId
        } satisfies EventSegment;
      })
      .filter((segment): segment is EventSegment => Boolean(segment));
  }

  private ensureSegmentsWithIds(
    segments: Array<Partial<EventSegment> & Omit<EventSegment, 'id'> | Omit<EventSegment, 'id'>>
  ): EventSegment[] {
    return segments.map((segment) => ({
      id: typeof segment.id === 'string' ? segment.id : randomUUID(),
      name: segment.name,
      startOffsetMinutes: segment.startOffsetMinutes,
      durationMinutes: segment.durationMinutes,
      ownerId: segment.ownerId ?? null
    }));
  }

  private formatDate(value: Date): string {
    return value.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
  }

  private parseId(id: string): number {
    const parsed = Number.parseInt(id, 10);
    if (Number.isNaN(parsed)) {
      throw new NotFoundException('Event not found');
    }

    return parsed;
  }
}
