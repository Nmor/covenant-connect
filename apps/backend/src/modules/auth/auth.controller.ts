import { Body, Controller, Get, Param, Post, Query } from '@nestjs/common';

import type { Provider, UserAccount } from '@covenant-connect/shared';

import { AuthService } from './auth.service';
import { LoginDto } from './dto/login.dto';
import { ProviderCallbackDto } from './dto/provider-callback.dto';
import { RegisterDto } from './dto/register.dto';
import { StartSocialLoginDto } from './dto/start-social-login.dto';
import type { Session } from './session.store';

@Controller('auth')
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  @Post('register')
  async register(@Body() dto: RegisterDto): Promise<{ account: UserAccount; session: Session }> {
    return this.authService.register(dto);
  }

  @Post('login')
  async login(@Body() dto: LoginDto): Promise<{ account: UserAccount; session: Session }> {
    return this.authService.login(dto.email, dto.password);
  }

  @Post('logout')
  async logout(@Body('token') token: string): Promise<{ success: boolean }> {
    await this.authService.logout(token);
    return { success: true };
  }

  @Get('session/:token')
  async getSession(@Param('token') token: string): Promise<UserAccount | null> {
    return this.authService.resolveSession(token);
  }

  @Get('providers/:provider/authorize')
  async startProviderLogin(
    @Param('provider') provider: string,
    @Query() query: StartSocialLoginDto
  ): Promise<{ authorizationUrl: string; state: string }> {
    return this.authService.startProviderLogin(this.mapProvider(provider), query.redirectUri, query.state);
  }

  @Post('providers/:provider/callback')
  async providerCallback(
    @Param('provider') provider: string,
    @Body() body: ProviderCallbackDto
  ): Promise<{ account: UserAccount; session: Session; redirectUri?: string }> {
    // TODO: Replace with real provider integration that exchanges `code` for a profile.
    const mockProfile = {
      providerId: body.code,
      email: `${body.code}@${provider}.oauth`,
      firstName: provider.charAt(0).toUpperCase() + provider.slice(1),
      lastName: 'User'
    };

    return this.authService.completeProviderLogin(
      this.mapProvider(provider),
      mockProfile,
      body.state
    );
  }

  private mapProvider(provider: string): Provider {
    if (provider === 'google' || provider === 'facebook' || provider === 'apple' || provider === 'password') {
      return provider;
    }

    throw new Error(`Unsupported provider: ${provider}`);
  }
}
