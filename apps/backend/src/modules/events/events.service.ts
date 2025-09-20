import { Injectable, NotFoundException } from '@nestjs/common';
import { randomUUID } from 'node:crypto';

import type { Event, EventSegment, PaginatedResult, Pagination } from '@covenant-connect/shared';

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

type UpdateEventInput = Partial<CreateEventInput>;

@Injectable()
export class EventsService {
  private readonly events = new Map<string, Event>();

  async create(input: CreateEventInput): Promise<Event> {
    const now = new Date();
    const segments: EventSegment[] = (input.segments ?? []).map((segment) => ({
      ...segment,
      id: randomUUID()
    }));

    const event: Event = {
      id: randomUUID(),
      title: input.title,
      description: input.description,
      startsAt: input.startsAt,
      endsAt: input.endsAt,
      timezone: input.timezone,
      recurrenceRule: input.recurrenceRule,
      segments,
      tags: input.tags ?? [],
      location: input.location,
      createdAt: now,
      updatedAt: now
    };

    this.events.set(event.id, event);
    return event;
  }

  async list(pagination: Pagination): Promise<PaginatedResult<Event>> {
    const data = Array.from(this.events.values()).sort(
      (left, right) => left.startsAt.getTime() - right.startsAt.getTime()
    );

    const start = (pagination.page - 1) * pagination.pageSize;
    const end = start + pagination.pageSize;

    return {
      data: data.slice(start, end),
      total: data.length,
      page: pagination.page,
      pageSize: pagination.pageSize
    };
  }

  async update(eventId: string, input: UpdateEventInput): Promise<Event> {
    const existing = this.events.get(eventId);
    if (!existing) {
      throw new NotFoundException('Event not found');
    }

    const segments = input.segments
      ? input.segments.map((segment) => ({
          ...segment,
          id: segment.id ?? randomUUID()
        }))
      : existing.segments;

    const updated: Event = {
      ...existing,
      ...input,
      segments,
      tags: input.tags ?? existing.tags,
      updatedAt: new Date()
    };

    this.events.set(updated.id, updated);
    return updated;
  }

  async toICalendar(): Promise<string> {
    const lines = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//Covenant Connect//EN'
    ];

    for (const event of this.events.values()) {
      lines.push('BEGIN:VEVENT');
      lines.push(`UID:${event.id}`);
      lines.push(`SUMMARY:${event.title}`);
      if (event.description) {
        lines.push(`DESCRIPTION:${event.description}`);
      }
      lines.push(`DTSTART:${event.startsAt.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z')}`);
      lines.push(`DTEND:${event.endsAt.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z')}`);
      lines.push(`LOCATION:${event.location}`);
      if (event.recurrenceRule) {
        lines.push(`RRULE:${event.recurrenceRule}`);
      }
      lines.push('END:VEVENT');
    }

    lines.push('END:VCALENDAR');
    return lines.join('\n');
  }
}
