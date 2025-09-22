import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class EventSegmentDto {
  @ApiProperty({ example: 'seg-1' })
  id!: string;

  @ApiProperty({ example: 'Worship' })
  name!: string;

  @ApiProperty({ example: 0 })
  startOffsetMinutes!: number;

  @ApiProperty({ example: 30 })
  durationMinutes!: number;

  @ApiProperty({ nullable: true, example: 'member-1' })
  ownerId!: string | null;
}

export class EventDto {
  @ApiProperty({ example: 'evt-123' })
  id!: string;

  @ApiProperty({ example: 'Sunday Gathering' })
  title!: string;

  @ApiPropertyOptional({ example: 'An uplifting worship experience.' })
  description?: string;

  @ApiProperty({ format: 'date-time', example: '2024-03-01T18:00:00.000Z' })
  startsAt!: string;

  @ApiProperty({ format: 'date-time', example: '2024-03-01T20:00:00.000Z' })
  endsAt!: string;

  @ApiProperty({ example: 'America/New_York' })
  timezone!: string;

  @ApiPropertyOptional({ example: 'RRULE:FREQ=WEEKLY;COUNT=4' })
  recurrenceRule?: string;

  @ApiProperty({ type: () => [EventSegmentDto] })
  segments!: EventSegmentDto[];

  @ApiProperty({ type: () => [String] })
  tags!: string[];

  @ApiProperty({ example: 'Main auditorium' })
  location!: string;

  @ApiProperty({ format: 'date-time' })
  createdAt!: string;

  @ApiProperty({ format: 'date-time' })
  updatedAt!: string;
}
