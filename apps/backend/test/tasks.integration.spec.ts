import 'reflect-metadata';

import { spawn } from 'node:child_process';
import { once } from 'node:events';

import { ConfigService } from '@nestjs/config';
import { Test, type TestingModule } from '@nestjs/testing';
import { Prisma } from '@prisma/client';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

import { TasksModule } from '../src/modules/tasks/tasks.module';
import { TasksService } from '../src/modules/tasks/tasks.service';
import { TaskJobNames } from '../src/modules/tasks/task.constants';
import { AutomationService } from '../src/modules/tasks/workers/automation.service';
import { EmailService } from '../src/modules/email/email.service';
import { PrismaService } from '../src/prisma/prisma.service';

type AutomationRecord = {
  id: number;
  name: string;
  trigger: string;
  isActive: boolean;
  steps: Array<ReturnType<typeof createAutomationStep>>;
};

const createAutomationStep = () => ({
  id: 101,
  automationId: 1,
  title: 'Email Admins',
  actionType: 'email',
  channel: null,
  department: null,
  order: 0,
  delayMinutes: 0,
  config: {
    recipientMode: 'admins',
    subject: 'New Prayer from {{ prayerRequest.requesterName }}',
    body: 'Message: {{ prayerRequest.message }}'
  },
  createdAt: new Date('2024-01-01T00:00:00.000Z'),
  updatedAt: new Date('2024-01-01T00:00:00.000Z')
});

class StubPrismaService {
  private readonly automationRecord: AutomationRecord;
  private readonly automationStepRecord: ReturnType<typeof createAutomationStep> & {
    automation: AutomationRecord;
  };

  constructor() {
    const step = createAutomationStep();
    this.automationRecord = {
      id: 1,
      name: 'Notify Admins',
      trigger: 'prayer_submitted',
      isActive: true,
      steps: [step]
    };

    this.automationStepRecord = {
      ...step,
      automation: this.automationRecord
    };
  }

  public readonly prayerRequest = {
    findUnique: async ({ where }: { where: { id: number } }) => {
      if (where.id !== 1) {
        return null;
      }
      return {
        id: 1,
        requesterName: 'Jane Doe',
        requesterEmail: 'jane@example.com',
        requesterPhone: '555-1000',
        message: 'Please pray for my family.',
        isPublic: false,
        createdAt: new Date('2024-01-05T12:00:00.000Z')
      };
    }
  };

  public readonly user = {
    findMany: async ({ where }: { where?: Record<string, unknown>; select?: { email?: boolean } }) => {
      if (where && 'isAdmin' in where) {
        return [
          { email: 'admin1@example.com' },
          { email: 'admin2@example.com' }
        ];
      }
      return [];
    },
    findUnique: async () => null
  };

  public readonly automation = {
    findMany: async (args: Prisma.AutomationFindManyArgs) => {
      if (args.select?.id) {
        return [{ id: this.automationRecord.id }];
      }

      if (args.include?.steps) {
        return [
          {
            ...this.automationRecord,
            steps: this.automationRecord.steps
          }
        ];
      }

      return [];
    }
  };

  public readonly automationStep = {
    findUnique: async ({ where }: Prisma.AutomationStepFindUniqueArgs) => {
      if (where?.id !== this.automationStepRecord.id) {
        return null;
      }
      return this.automationStepRecord;
    }
  };

  public readonly event = { findUnique: async () => null };
  public readonly sermon = { findUnique: async () => null };
  public readonly attendanceRecord = { findMany: async () => [] };
  public readonly volunteerRole = { findMany: async () => [] };
  public readonly volunteerAssignment = { findMany: async () => [] };
  public readonly donation = {
    aggregate: async () => ({ _sum: { amount: new Prisma.Decimal(0) } })
  };
  public readonly member = { count: async () => 0 };
  public readonly ministryDepartment = { findMany: async () => [] };
}

const waitFor = async (predicate: () => Promise<boolean> | boolean, timeout = 5000, interval = 50) => {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (await predicate()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, interval));
  }
  throw new Error('Condition not met within timeout');
};

describe('TasksModule integration', () => {
  let redisProcess: ReturnType<typeof spawn> | null;
  const redisPort = 6380;
  let prisma: StubPrismaService;
  let email: { sendMail: ReturnType<typeof vi.fn> };
  let moduleRef: TestingModule;
  let tasks: TasksService;
  let automations: AutomationService;

  beforeAll(async () => {
    redisProcess = spawn('redis-server', ['--port', redisPort.toString(), '--appendonly', 'no'], {
      stdio: ['ignore', 'pipe', 'pipe']
    });

    const ready = new Promise<void>((resolve, reject) => {
      redisProcess?.stdout?.on('data', (chunk) => {
        if (chunk.toString().includes('Ready to accept connections')) {
          resolve();
        }
      });
      redisProcess?.stderr?.on('data', (chunk) => {
        const text = chunk.toString();
        if (text.includes('already in use')) {
          reject(new Error(text));
        }
      });
      redisProcess?.once('error', reject);
      redisProcess?.once('exit', (code) => {
        if (code !== 0) {
          reject(new Error(`Redis process exited with code ${code}`));
        }
      });
    });

    await ready;

    const redisUrl = `redis://127.0.0.1:${redisPort}`;
    process.env.QUEUE_DRIVER = 'redis';
    process.env.REDIS_URL = redisUrl;
    process.env.QUEUE_MAX_ATTEMPTS = '1';
    process.env.KPI_DIGEST_CRON = '0 0 1 1 *';
    process.env.FOLLOW_UP_CRON = '0 0 1 1 *';
  });

  afterAll(async () => {
    if (redisProcess) {
      redisProcess.kill();
      await once(redisProcess, 'exit');
      redisProcess = null;
    }
  });

  beforeEach(async () => {
    prisma = new StubPrismaService();
    email = {
      sendMail: vi.fn().mockResolvedValue({ provider: { id: 'stub', name: 'stub', type: 'smtp' } })
    };

    const configStub = new ConfigService({
      automation: {
        queue: { driver: 'redis', redisUrl: `redis://127.0.0.1:${redisPort}`, defaultAttempts: 1 },
        schedules: { kpiDigestCron: '0 0 1 1 *', followUpCron: '0 0 1 1 *' }
      }
    });

    moduleRef = await Test.createTestingModule({
      imports: [TasksModule],
      providers: [{ provide: ConfigService, useValue: configStub }]
    })
      .overrideProvider(PrismaService)
      .useValue(prisma)
      .overrideProvider(EmailService)
      .useValue(email)
      .compile();

    automations = moduleRef.get(AutomationService);
    tasks = moduleRef.get(TasksService);

    await moduleRef.init();
  });

  afterEach(async () => {
    if (moduleRef) {
      await moduleRef.close();
    }
    vi.restoreAllMocks();
  });

  it('processes automation jobs via the BullMQ worker', async () => {
    const triggered = await automations.trigger('prayer_submitted', { prayerRequestId: 1 });
    expect(triggered).toBe(1);

    await waitFor(async () => email.sendMail.mock.calls.length > 0);

    const [payload] = email.sendMail.mock.calls.at(-1) ?? [];
    expect(payload).toBeDefined();
    expect(payload.to).toEqual(['admin1@example.com', 'admin2@example.com']);
    expect(payload.subject).toContain('New Prayer');
    expect(payload.text).toContain('Please pray for my family.');

    const jobs = await tasks.list();
    const repeatableJobs = jobs.filter((job) => job.id?.startsWith('repeat:'));
    const scheduledNames = repeatableJobs.map((job) => job.name).sort();
    expect(scheduledNames).toEqual(
      [
        TaskJobNames.DepartmentKpiDigest,
        TaskJobNames.ExecutiveKpiDigest,
        TaskJobNames.FollowUpScan
      ].sort()
    );

    const pendingJobs = jobs.filter((job) => !job.id?.startsWith('repeat:'));
    expect(pendingJobs).toEqual([]);
  });
});
