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

  constructor() {
    this.seedSampleEvents();
  }

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

  private seedSampleEvents(): void {
    if (this.events.size > 0) {
      return;
    }

    const base = new Date();
    const offset = (date: Date, { days = 0, hours = 0, minutes = 0 }: { days?: number; hours?: number; minutes?: number }) =>
      new Date(date.getTime() + (((days * 24 + hours) * 60 + minutes) * 60 * 1000));

    const seeds: Array<{
      title: string;
      description: string;
      startOffset: { days: number; hours: number; minutes?: number };
      endOffset: { days: number; hours: number; minutes?: number };
      location: string;
      recurrenceRule?: string;
      tags?: string[];
      segments?: Array<Omit<EventSegment, 'id'>>;
    }> = [
      {
        title: 'Sunday Worship Service',
        description: 'Join us for corporate worship, teaching, and prayer.',
        startOffset: { days: 2, hours: 9, minutes: 30 },
        endOffset: { days: 2, hours: 11, minutes: 15 },
        location: 'Main Sanctuary',
        recurrenceRule: 'FREQ=WEEKLY;BYDAY=SU',
        tags: ['worship', 'in-person'],
        segments: [
          { name: 'Team Prayer', startOffsetMinutes: -30, durationMinutes: 20, ownerId: null },
          { name: 'Sound Check', startOffsetMinutes: -10, durationMinutes: 10, ownerId: 'member-adeola' }
        ]
      },
      {
        title: 'Youth Bible Study',
        description: 'Weekly gathering for students to study Scripture and build friendships.',
        startOffset: { days: 4, hours: 18 },
        endOffset: { days: 4, hours: 19, minutes: 30 },
        location: 'Youth Center',
        tags: ['students', 'discipleship']
      },
      {
        title: 'Community Outreach',
        description: 'Serving at the downtown food bank with our outreach team.',
        startOffset: { days: 7, hours: 9 },
        endOffset: { days: 7, hours: 12 },
        location: 'Downtown Food Bank',
        tags: ['outreach', 'volunteers']
      },
      {
        title: 'Prayer & Worship Night',
        description: 'An extended evening of worship, testimony, and intercession.',
        startOffset: { days: 14, hours: 19 },
        endOffset: { days: 14, hours: 21 },
        location: 'Chapel',
        tags: ['worship', 'prayer'],
        segments: [{ name: 'Prayer Teams', startOffsetMinutes: 0, durationMinutes: 120, ownerId: 'member-johnson' }]
      }
    ];

    for (const seed of seeds) {
      const startsAt = offset(base, seed.startOffset);
      const endsAt = offset(base, seed.endOffset);
      const now = new Date();
      const segments: EventSegment[] = (seed.segments ?? []).map((segment) => ({
        ...segment,
        id: randomUUID()
      }));

      const event: Event = {
        id: randomUUID(),
        title: seed.title,
        description: seed.description,
        startsAt,
        endsAt,
        timezone: 'America/New_York',
        recurrenceRule: seed.recurrenceRule,
        segments,
        tags: seed.tags ?? [],
        location: seed.location,
        createdAt: now,
        updatedAt: now
      };

      this.events.set(event.id, event);
    }
  }
}
