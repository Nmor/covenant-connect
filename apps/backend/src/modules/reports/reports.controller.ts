import { Controller, Get } from '@nestjs/common';

import { ReportsService } from './reports.service';

@Controller('reports')
export class ReportsController {
  constructor(private readonly reports: ReportsService) {}

  @Get('dashboard')
  dashboard(): Promise<{ kpis: { label: string; value: number; change?: number }[] }> {
    return this.reports.getDashboard();
  }
}
