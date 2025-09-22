import { ApiProperty } from '@nestjs/swagger';

import { EventDto } from './event.dto';

export class EventsResponseDto {
  @ApiProperty({ type: () => [EventDto] })
  data!: EventDto[];

  @ApiProperty({ example: 42 })
  total!: number;

  @ApiProperty({ example: 1 })
  page!: number;

  @ApiProperty({ example: 25 })
  pageSize!: number;
}
