import { Controller, Get } from '@nestjs/common';
import { ApiOkResponse, ApiOperation, ApiTags } from '@nestjs/swagger';

import { ReportsService } from './reports.service';
import { DashboardResponseDto } from './dto/dashboard-response.dto';

@ApiTags('Reports')
@Controller('reports')
export class ReportsController {
  constructor(private readonly reports: ReportsService) {}

  @ApiOperation({ operationId: 'getDashboardReport', summary: 'Retrieve KPI metrics for the dashboard view.' })
  @ApiOkResponse({ type: DashboardResponseDto })
  @Get('dashboard')
  dashboard(): Promise<{ kpis: { label: string; value: number; change?: number }[] }> {
    return this.reports.getDashboard();
  }
}
