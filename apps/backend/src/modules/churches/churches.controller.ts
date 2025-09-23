import { Body, Controller, Get, Param, Patch, Post } from '@nestjs/common';
import type { Church } from '@covenant-connect/shared';

import { ChurchesService } from './churches.service';

type CreateChurchRequest = {
  name: string;
  timezone: string;
  country?: string | null;
  state?: string | null;
  city?: string | null;
 codex/confirm-removal-of-python-implementations-ih9bbr
  settings?: Record<string, unknown> | null;
  settings?: Record<string, unknown>;
     main
};

type UpdateChurchRequest = Partial<CreateChurchRequest>;

@Controller('churches')
export class ChurchesController {
  constructor(private readonly churches: ChurchesService) {}

  @Post()
  create(@Body() body: CreateChurchRequest): Promise<Church> {
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
  update(@Param('id') id: string, @Body() body: UpdateChurchRequest): Promise<Church> {
    return this.churches.update(id, body);
  }
}
