import { IsNotEmpty, IsObject, IsString } from 'class-validator';

export class CreateIntegrationSettingDto {
  @IsString()
  @IsNotEmpty()
  provider!: string;

  @IsObject()
  config!: Record<string, string>;
}
