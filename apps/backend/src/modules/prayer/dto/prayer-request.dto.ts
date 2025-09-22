import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class PrayerRequestDto {
  @ApiProperty({ example: 'prayer-1' })
  id!: string;

  @ApiProperty({ example: 'John Doe' })
  requesterName!: string;

  @ApiPropertyOptional({ example: 'john@example.com' })
  requesterEmail?: string;

  @ApiPropertyOptional({ example: '+15555551234' })
  requesterPhone?: string;

  @ApiProperty({ example: 'Please pray for healing.' })
  message!: string;

  @ApiPropertyOptional({ example: 'member-1' })
  memberId?: string;

  @ApiProperty({ enum: ['new', 'assigned', 'praying', 'answered'], example: 'assigned' })
  status!: 'new' | 'assigned' | 'praying' | 'answered';

  @ApiPropertyOptional({ format: 'date-time', example: '2024-03-10T15:00:00.000Z' })
  followUpAt?: string;

  @ApiProperty({ format: 'date-time' })
  createdAt!: string;

  @ApiProperty({ format: 'date-time' })
  updatedAt!: string;
}
