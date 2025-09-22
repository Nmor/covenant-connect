import { ApiProperty } from '@nestjs/swagger';

import { DonationDto } from './donation.dto';

export class DonationsResponseDto {
  @ApiProperty({ type: () => [DonationDto] })
  data!: DonationDto[];

  @ApiProperty({ example: 120 })
  total!: number;

  @ApiProperty({ example: 1 })
  page!: number;

  @ApiProperty({ example: 25 })
  pageSize!: number;
}
