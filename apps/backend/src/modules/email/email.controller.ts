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
    @Body()
    body: {
      id?: string;
      type: EmailProvider['type'];
      name: string;
      credentials: Record<string, string>;
      isActive?: boolean;
    }
  ): Promise<EmailProvider> {
    return this.email.upsertProvider(body.id ?? null, {
      type: body.type,
      name: body.name,
      credentials: body.credentials,
      isActive: body.isActive
    });
  }

  @Patch('providers/:id/activate')
  activate(@Param('id') id: string): Promise<EmailProvider> {
    return this.email.activate(id);
  }

  @Post('send')
  send(
    @Body()
    body: {
      to: string | string[];
      subject: string;
      html?: string;
      text?: string;
      from?: string;
      replyTo?: string;
    }
  ): Promise<{ provider: EmailProvider }> {
    return this.email.sendMail({
      to: body.to,
      subject: body.subject,
      html: body.html,
      text: body.text,
      from: body.from,
      replyTo: body.replyTo
    });
  }
}
