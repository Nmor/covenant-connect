import { ApiProperty } from '@nestjs/swagger';

export class DonationDto {
  @ApiProperty({ example: 'don-1' })
  id!: string;

  @ApiProperty({ nullable: true, example: 'member-1', type: String })
  memberId!: string | null;

  @ApiProperty({ example: 125 })
  amount!: number;

  @ApiProperty({ example: 'USD' })
  currency!: string;

  @ApiProperty({ enum: ['paystack', 'fincra', 'stripe', 'flutterwave'], example: 'stripe' })
  provider!: 'paystack' | 'fincra' | 'stripe' | 'flutterwave';

  @ApiProperty({ enum: ['pending', 'completed', 'failed', 'refunded'], example: 'completed' })
  status!: 'pending' | 'completed' | 'failed' | 'refunded';

  @ApiProperty({ type: 'object', additionalProperties: true })
  metadata!: Record<string, unknown>;

  @ApiProperty({ format: 'date-time' })
  createdAt!: string;

  @ApiProperty({ format: 'date-time' })
  updatedAt!: string;
}
