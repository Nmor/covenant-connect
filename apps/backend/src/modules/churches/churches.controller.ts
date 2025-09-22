import { Body, Controller, Get, Param, Patch, Post } from '@nestjs/common';
import type { Church } from '@covenant-connect/shared';

import { ChurchesService } from './churches.service';

@Controller('churches')
export class ChurchesController {
  constructor(private readonly churches: ChurchesService) {}

  @Post()
  create(@Body() body: { name: string; timezone: string; country?: string; state?: string; city?: string }): Promise<Church> {
    return this.churches.create(body);
  }

  @Get()
  list(): Promise<Church[]> {
    return this.churches.list();
  }

  @Get(':id')
  getById(@Param('id') id: string): Promise<Church> {
    return this.churches.getById(id);
  }

  @Patch(':id')
  update(@Param('id') id: string, @Body() body: Partial<Church>): Promise<Church> {
    return this.churches.update(id, body);
  }
}
