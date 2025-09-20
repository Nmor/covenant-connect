import { Injectable } from '@nestjs/common';
import { randomUUID } from 'node:crypto';

import type { QueueJob } from '@covenant-connect/shared';

@Injectable()
export class TasksService {
  private readonly jobs: QueueJob[] = [];

  async enqueue(name: string, payload: Record<string, unknown>): Promise<QueueJob> {
    const job: QueueJob = {
      id: randomUUID(),
      name,
      payload,
      scheduledAt: new Date()
    };

    this.jobs.push(job);
    return job;
  }

  async list(): Promise<QueueJob[]> {
    return this.jobs;
  }
}
