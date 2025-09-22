import { Transform, Type } from 'class-transformer';
import {
  IsDefined,
  IsIn,
  IsNotEmpty,
  IsNumber,
  IsObject,
  IsOptional,
  IsPositive,
  IsString
} from 'class-validator';

import type { Donation } from '@covenant-connect/shared';

const DONATION_PROVIDERS: Donation['provider'][] = ['paystack', 'fincra', 'stripe', 'flutterwave'];

export class CreateDonationDto {
  @IsDefined()
  @Type(() => Number)
  @IsNumber({ allowNaN: false })
  @IsPositive()
  amount!: number;

  @IsDefined()
  @IsString()
  @IsNotEmpty()
  currency!: string;

  @IsDefined()
  @IsString()
  @IsIn(DONATION_PROVIDERS)
  provider!: Donation['provider'];

  @Transform(({ value }) => (value === null ? undefined : value))
  @IsOptional()
  @IsString()
  @IsNotEmpty()
  memberId?: string;

  @Transform(({ value }) => (value === null ? undefined : value))
  @IsOptional()
  @IsObject()
  metadata?: Record<string, unknown>;
}
