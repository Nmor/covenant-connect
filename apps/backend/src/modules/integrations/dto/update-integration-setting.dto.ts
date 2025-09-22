import { IsNotEmpty, IsObject, IsOptional, IsString } from 'class-validator';

export class UpdateIntegrationSettingDto {
  @IsOptional()
  @IsString()
  @IsNotEmpty()
  provider?: string;

  @IsOptional()
  @IsObject()
  config?: Record<string, string>;
}
