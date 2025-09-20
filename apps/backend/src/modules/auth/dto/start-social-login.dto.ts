import { IsOptional, IsString, IsUrl } from 'class-validator';

export class StartSocialLoginDto {
  @IsOptional()
  @IsUrl({ require_protocol: true })
  redirectUri?: string;

  @IsOptional()
  @IsString()
  state?: string;
}
