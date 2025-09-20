import { Body, Controller, Get, Param, Patch, Post, Query, Res } from '@nestjs/common';
import { Response } from 'express';

import type { Event, PaginatedResult } from '@covenant-connect/shared';

import { EventsService } from './events.service';

@Controller('events')
export class EventsController {
  constructor(private readonly events: EventsService) {}

  @Get()
  list(
    @Query('page') page = '1',
    @Query('pageSize') pageSize = '25'
  ): Promise<PaginatedResult<Event>> {
    return this.events.list({
      page: Number.parseInt(page, 10),
      pageSize: Number.parseInt(pageSize, 10)
    });
  }

  @Post()
  create(
    @Body()
    body: {
      title: string;
      description?: string;
      startsAt: string;
      endsAt: string;
      timezone: string;
      recurrenceRule?: string;
      tags?: string[];
      location: string;
    }
  ): Promise<Event> {
    return this.events.create({
      ...body,
      startsAt: new Date(body.startsAt),
      endsAt: new Date(body.endsAt)
    });
  }

  @Patch(':id')
  update(
    @Param('id') id: string,
    @Body() body: Partial<{ title: string; description: string; startsAt: string; endsAt: string; tags: string[] }>
  ): Promise<Event> {
    return this.events.update(id, {
      ...body,
      startsAt: body.startsAt ? new Date(body.startsAt) : undefined,
      endsAt: body.endsAt ? new Date(body.endsAt) : undefined
    });
  }

  @Get('calendar.ics')
  async downloadCalendar(@Res() res: Response): Promise<void> {
    const calendar = await this.events.toICalendar();
    res.setHeader('Content-Type', 'text/calendar');
    res.send(calendar);
  }
}
