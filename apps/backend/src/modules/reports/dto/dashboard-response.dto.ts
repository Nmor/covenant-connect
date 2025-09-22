import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class DashboardKpiDto {
  @ApiProperty({ example: 'Total Giving' })
  label!: string;

  @ApiProperty({ example: 1250 })
  value!: number;

  @ApiPropertyOptional({ example: 12.5 })
  change?: number;
}

export class DashboardResponseDto {
  @ApiProperty({ type: () => [DashboardKpiDto] })
  kpis!: DashboardKpiDto[];
}
