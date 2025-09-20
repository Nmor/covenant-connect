import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';

import { AccountsModule } from '../accounts/accounts.module';
import { AuthController } from './auth.controller';
import { AuthService } from './auth.service';
import { SessionStore } from './session.store';

@Module({
  imports: [ConfigModule, AccountsModule],
  controllers: [AuthController],
  providers: [AuthService, SessionStore],
  exports: [AuthService]
})
export class AuthModule {}
