import { ApiProperty } from '@nestjs/swagger';

import { PrayerRequestDto } from './prayer-request.dto';

export class PrayerRequestsResponseDto {
  @ApiProperty({ type: () => [PrayerRequestDto] })
  data!: PrayerRequestDto[];

  @ApiProperty({ example: 12 })
  total!: number;

  @ApiProperty({ example: 1 })
  page!: number;

  @ApiProperty({ example: 25 })
  pageSize!: number;
}
