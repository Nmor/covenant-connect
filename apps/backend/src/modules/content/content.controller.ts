import { Body, Controller, Get, Post, Put } from '@nestjs/common';
import { ApiOkResponse, ApiOperation, ApiTags } from '@nestjs/swagger';
import type { HomeContent, PaginatedResult, Sermon } from '@covenant-connect/shared';

import { ContentService } from './content.service';
import { HomeContentDto } from './dto/home-content.dto';

@ApiTags('Content')
@Controller('content')
export class ContentController {
  constructor(private readonly content: ContentService) {}

  @ApiOperation({ operationId: 'getHomeContent', summary: 'Fetch marketing content for the public home page.' })
  @ApiOkResponse({ type: HomeContentDto })
  @Get('home')
  getHome(): Promise<HomeContent> {
    return this.content.getHome();
  }

  @ApiOkResponse({ type: HomeContentDto })
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
