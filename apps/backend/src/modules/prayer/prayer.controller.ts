import { Body, Controller, Get, Param, Patch, Post } from '@nestjs/common';
import type { PaginatedResult, PrayerRequest } from '@covenant-connect/shared';
import { ApiOkResponse, ApiOperation, ApiTags } from '@nestjs/swagger';

import { PrayerService } from './prayer.service';
import { PrayerRequestDto } from './dto/prayer-request.dto';
import { PrayerRequestsResponseDto } from './dto/prayer-requests-response.dto';

@ApiTags('Prayer')
@Controller('prayer')
export class PrayerController {
  constructor(private readonly prayer: PrayerService) {}

  @ApiOkResponse({ type: PrayerRequestDto })
  @ApiOperation({ operationId: 'createPrayerRequest', summary: 'Create a new prayer request.' })
  @Post('requests')
  create(
    @Body()
    body: { requesterName: string; message: string; requesterEmail?: string; requesterPhone?: string; memberId?: string }
  ): Promise<PrayerRequest> {
    return this.prayer.create(body);
  }

  @ApiOperation({ operationId: 'getPrayerRequests', summary: 'List prayer requests for follow-up.' })
  @ApiOkResponse({ type: PrayerRequestsResponseDto })
  @Get('requests')
  list(): Promise<PaginatedResult<PrayerRequest>> {
    return this.prayer.list();
  }

  @ApiOkResponse({ type: PrayerRequestDto })
  @Patch('requests/:id')
  update(
    @Param('id') id: string,
    @Body() body: Partial<Pick<PrayerRequest, 'status' | 'followUpAt'>>
  ): Promise<PrayerRequest> {
    return this.prayer.update(id, body);
  }
}
