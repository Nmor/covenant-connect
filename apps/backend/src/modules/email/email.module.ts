import { Module } from '@nestjs/common';

import { EmailController } from './email.controller';
import { EmailService } from './email.service';
import { EmailProviderFactory } from './providers/email-provider.factory';

@Module({
  controllers: [EmailController],
  providers: [EmailService, EmailProviderFactory],
  exports: [EmailService]
})
export class EmailModule {}
