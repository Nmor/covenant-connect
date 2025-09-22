import { Transform } from 'class-transformer';
import { IsIn, IsNotEmpty, IsObject, IsOptional, IsString } from 'class-validator';
import type { Donation } from '@covenant-connect/shared';

const DONATION_STATUSES: Donation['status'][] = ['pending', 'completed', 'failed', 'refunded'];

export class UpdateDonationStatusDto {
  @IsString()
  @IsNotEmpty()
  @IsIn(DONATION_STATUSES)
  status!: Donation['status'];

  @Transform(({ value }) => (value === null ? undefined : value))
  @IsOptional()
  @IsObject()
  metadata?: Record<string, unknown>;
}
