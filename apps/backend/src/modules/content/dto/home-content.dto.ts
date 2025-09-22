import { ApiProperty } from '@nestjs/swagger';

export class HomeNextStepDto {
  @ApiProperty({ example: 'Launch admin console' })
  label!: string;

  @ApiProperty({ example: '/dashboard' })
  url!: string;
}

export class HomeContentDto {
  @ApiProperty({ example: 'Plan services and care pathways with ease' })
  heroTitle!: string;

  @ApiProperty({ example: 'The TypeScript rewrite ships with modular services for worship planning, assimilation, and giving.' })
  heroSubtitle!: string;

  @ApiProperty({ type: () => [String] })
  highlights!: string[];

  @ApiProperty({ type: () => [HomeNextStepDto] })
  nextSteps!: HomeNextStepDto[];
}
