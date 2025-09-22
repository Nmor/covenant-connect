import { Body, Controller, Get, Post, Put } from '@nestjs/common';
import type { HomeContent, PaginatedResult, Sermon } from '@covenant-connect/shared';

import { ContentService } from './content.service';

@Controller('content')
export class ContentController {
  constructor(private readonly content: ContentService) {}

  @Get('home')
  getHome(): Promise<HomeContent> {
    return this.content.getHome();
  }

  @Put('home')
  updateHome(@Body() body: Partial<HomeContent>): Promise<HomeContent> {
    return this.content.updateHome(body);
  }

  @Get('sermons')
  listSermons(): Promise<PaginatedResult<Sermon>> {
    return this.content.listSermons();
  }

  @Post('sermons')
  addSermon(@Body() sermon: Sermon): Promise<{ success: boolean }> {
    return this.content.addSermon(sermon).then(() => ({ success: true }));
  }
}
