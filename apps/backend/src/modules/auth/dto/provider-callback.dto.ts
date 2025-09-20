import { IsOptional, IsString } from 'class-validator';

export class ProviderCallbackDto {
  @IsString()
  code!: string;

  @IsOptional()
  @IsString()
  state?: string;
}
