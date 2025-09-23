import { Body, Controller, Get, Post, Put, Query } from '@nestjs/common';
import { ApiOkResponse, ApiOperation, ApiQuery, ApiTags } from '@nestjs/swagger';
import type { HomeContent, PaginatedResult, Sermon } from '@covenant-connect/shared';

import { ContentService } from './content.service';
import { HomeContentDto } from './dto/home-content.dto';

type CreateSermonRequest = {
  title: string;
  description?: string | null;
  preacher?: string | null;
  date?: string | null;
  mediaUrl?: string | null;
  mediaType?: string | null;
};

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

  @ApiQuery({ name: 'page', required: false, type: Number, example: 1 })
  @ApiQuery({ name: 'pageSize', required: false, type: Number, example: 25 })
  @Get('sermons')
  listSermons(
    @Query('page') page = '1',
    @Query('pageSize') pageSize = '25'
  ): Promise<PaginatedResult<Sermon>> {
    return this.content.listSermons({
      page: Number.parseInt(page, 10),
      pageSize: Number.parseInt(pageSize, 10)
    });
  }

  @Post('sermons')
  addSermon(@Body() body: CreateSermonRequest): Promise<Sermon> {
    return this.content.addSermon({
      title: body.title,
      description: body.description ?? null,
      preacher: body.preacher ?? null,
      date: body.date ? new Date(body.date) : undefined,
      mediaUrl: body.mediaUrl ?? null,
      mediaType: body.mediaType ?? null
    });
  }
}
