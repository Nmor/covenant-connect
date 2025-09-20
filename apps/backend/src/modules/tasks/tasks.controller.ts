import { Body, Controller, Get, Post } from '@nestjs/common';

import type { QueueJob } from '@covenant-connect/shared';

import { TasksService } from './tasks.service';

@Controller('tasks')
export class TasksController {
  constructor(private readonly tasks: TasksService) {}

  @Get()
  list(): Promise<QueueJob[]> {
    return this.tasks.list();
  }

  @Post()
  enqueue(@Body() body: { name: string; payload: Record<string, unknown> }): Promise<QueueJob> {
    return this.tasks.enqueue(body.name, body.payload);
  }
}
