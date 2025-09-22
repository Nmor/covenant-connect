import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';

import { AccountsModule } from '../accounts/accounts.module';
import { AuthController } from './auth.controller';
import { AuthService } from './auth.service';
import {
  AUTH_PROVIDER_STRATEGIES,
  AppleOAuthProvider,
  FacebookOAuthProvider,
  GoogleOAuthProvider
} from './providers';
import { SessionStore } from './session.store';

@Module({
  imports: [ConfigModule, AccountsModule],
  controllers: [AuthController],
  providers: [
    AuthService,
    SessionStore,
    GoogleOAuthProvider,
    FacebookOAuthProvider,
    AppleOAuthProvider,
    {
      provide: AUTH_PROVIDER_STRATEGIES,
      useFactory: (
        google: GoogleOAuthProvider,
        facebook: FacebookOAuthProvider,
        apple: AppleOAuthProvider
      ) => [google, facebook, apple],
      inject: [GoogleOAuthProvider, FacebookOAuthProvider, AppleOAuthProvider]
    }
  ],
  exports: [AuthService]
})
export class AuthModule {}
