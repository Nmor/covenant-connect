import { Body, Controller, Get, Param, Patch, Post, Query } from '@nestjs/common';
import type { Donation, PaginatedResult } from '@covenant-connect/shared';

import { DonationsService } from './donations.service';

@Controller('donations')
export class DonationsController {
  constructor(private readonly donations: DonationsService) {}

  @Get()
  list(
    @Query('page') page = '1',
    @Query('pageSize') pageSize = '25'
  ): Promise<PaginatedResult<Donation>> {
    return this.donations.list({
      page: Number.parseInt(page, 10),
      pageSize: Number.parseInt(pageSize, 10)
    });
  }

  @Post()
  create(
    @Body()
    body: { amount: number; currency: string; provider: Donation['provider']; memberId?: string | null }
  ): Promise<Donation> {
    return this.donations.create(body);
  }

  @Patch(':id/status')
  updateStatus(
    @Param('id') id: string,
    @Body() body: { status: Donation['status']; metadata?: Record<string, unknown> }
  ): Promise<Donation> {
    return this.donations.updateStatus(id, body);
  }
}
