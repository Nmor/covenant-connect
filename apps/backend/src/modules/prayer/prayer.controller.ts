import { Body, Controller, Get, Param, Patch, Post } from '@nestjs/common';
import type { PaginatedResult, PrayerRequest } from '@covenant-connect/shared';

import { PrayerService } from './prayer.service';

@Controller('prayer')
export class PrayerController {
  constructor(private readonly prayer: PrayerService) {}

  @Post('requests')
  create(
    @Body()
    body: { requesterName: string; message: string; requesterEmail?: string; requesterPhone?: string; memberId?: string }
  ): Promise<PrayerRequest> {
    return this.prayer.create(body);
  }

  @Get('requests')
  list(): Promise<PaginatedResult<PrayerRequest>> {
    return this.prayer.list();
  }

  @Patch('requests/:id')
  update(
    @Param('id') id: string,
    @Body() body: Partial<Pick<PrayerRequest, 'status' | 'followUpAt'>>
  ): Promise<PrayerRequest> {
    return this.prayer.update(id, body);
  }
}
