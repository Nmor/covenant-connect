import { Body, Controller, Get, Headers, Param, Patch, Post, Query, Req } from '@nestjs/common';
import type { Donation, PaginatedResult } from '@covenant-connect/shared';
import type { Request } from 'express';

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

  @Post('webhooks/paystack')
  async handlePaystackWebhook(
    @Req() req: Request & { rawBody?: Buffer | string },
    @Body() payload: unknown,
    @Headers('x-paystack-signature') signature?: string
  ): Promise<{ status: 'updated' | 'ignored' }> {
    const rawBody = this.extractRawBody(req);
    const result = await this.donations.handlePaystackWebhook(payload, {
      rawBody,
      signature: signature ?? null,
      headers: req.headers
    });

    return { status: result.wasUpdated ? 'updated' : 'ignored' };
  }

  @Post('webhooks/fincra')
  async handleFincraWebhook(
    @Req() req: Request & { rawBody?: Buffer | string },
    @Body() payload: unknown,
    @Headers('x-fincra-signature') signature?: string
  ): Promise<{ status: 'updated' | 'ignored' }> {
    const rawBody = this.extractRawBody(req);
    const result = await this.donations.handleFincraWebhook(payload, {
      rawBody,
      signature: signature ?? null,
      headers: req.headers
    });

    return { status: result.wasUpdated ? 'updated' : 'ignored' };
  }

  @Post('webhooks/stripe')
  async handleStripeWebhook(
    @Req() req: Request & { rawBody?: Buffer | string },
    @Body() payload: unknown,
    @Headers('stripe-signature') signature?: string
  ): Promise<{ status: 'updated' | 'ignored' }> {
    const rawBody = this.extractRawBody(req);
    const result = await this.donations.handleStripeWebhook(payload, {
      rawBody,
      signature: signature ?? null,
      headers: req.headers
    });

    return { status: result.wasUpdated ? 'updated' : 'ignored' };
  }

  @Post('webhooks/flutterwave')
  async handleFlutterwaveWebhook(
    @Req() req: Request & { rawBody?: Buffer | string },
    @Body() payload: unknown,
    @Headers('verif-hash') signature?: string
  ): Promise<{ status: 'updated' | 'ignored' }> {
    const rawBody = this.extractRawBody(req);
    const result = await this.donations.handleFlutterwaveWebhook(payload, {
      rawBody,
      signature: signature ?? null,
      headers: req.headers
    });

    return { status: result.wasUpdated ? 'updated' : 'ignored' };
  }

  private extractRawBody(req: Request & { rawBody?: Buffer | string }): string {
    if (Buffer.isBuffer(req.rawBody)) {
      return req.rawBody.toString('utf8');
    }

    if (typeof req.rawBody === 'string') {
      return req.rawBody;
    }

    if (req.body && typeof req.body === 'string') {
      return req.body;
    }

    return JSON.stringify(req.body ?? {});
  }
}
