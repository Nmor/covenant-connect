import { Body, Controller, Get, Param, Patch, Post, Query, Res } from '@nestjs/common';
import { Response } from 'express';
import type { Event, PaginatedResult } from '@covenant-connect/shared';
import { ApiOkResponse, ApiOperation, ApiQuery, ApiTags } from '@nestjs/swagger';

import { EventsService } from './events.service';
import { EventsResponseDto } from './dto/events-response.dto';
import { EventDto } from './dto/event.dto';

@ApiTags('Events')
@Controller('events')
export class EventsController {
  constructor(private readonly events: EventsService) {}

  @ApiOperation({ operationId: 'getEvents', summary: 'List upcoming events with pagination.' })
  @ApiQuery({ name: 'page', required: false, type: Number, example: 1 })
  @ApiQuery({ name: 'pageSize', required: false, type: Number, example: 25 })
  @ApiOkResponse({ type: EventsResponseDto })
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

  @ApiOkResponse({ type: EventDto })
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

  @ApiOkResponse({ type: EventDto })
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
