import { Body, Controller, Get, Param, Patch, Post } from '@nestjs/common';

import type { EmailProvider } from '@covenant-connect/shared';

import { EmailService } from './email.service';

@Controller('email')
export class EmailController {
  constructor(private readonly email: EmailService) {}

  @Get('providers')
  listProviders(): Promise<EmailProvider[]> {
    return this.email.listProviders();
  }

  @Post('providers')
  upsertProvider(
    @Body() body: { id?: string; type: EmailProvider['type']; name: string; credentials: Record<string, string>; isActive?: boolean }
  ): Promise<EmailProvider> {
    return this.email.upsertProvider(body.id ?? null, body);
  }

  @Patch('providers/:id/activate')
  activate(@Param('id') id: string): Promise<EmailProvider> {
    return this.email.activate(id);
  }

  @Post('send')
  send(@Body() body: { to: string; subject: string; html: string }): Promise<{ provider: EmailProvider }> {
    return this.email.sendMail(body.to, body.subject, body.html);
  }
}
