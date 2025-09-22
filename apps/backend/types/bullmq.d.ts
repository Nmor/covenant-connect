declare module 'bullmq' {
  export type JobsOptions = Record<string, unknown>;
  export type RepeatOptions = { pattern?: string; jobId?: string } & Record<string, unknown>;

  export type Job<T = unknown> = {
    id?: string | number;
    jobId?: string | number;
    name: string;
    data: T;
    timestamp?: number;
    delay?: number;
  };

  export class Queue<T = unknown> {
    constructor(name: string, options?: Record<string, unknown>);
    add(name: string, data: T, options?: JobsOptions): Promise<Job<T>>;
    addBulk?(jobs: Array<{ name: string; data: T; opts?: JobsOptions }>): Promise<Job<T>[]>;
    getRepeatableJobs(): Promise<Array<{ id?: string; key?: string; pattern?: string }>>;
    removeRepeatableByKey(key: string | undefined): Promise<void>;
    getJobs(types: string[]): Promise<Job<T>[]>;
    waitUntilReady(): Promise<void>;
    close(): Promise<void>;
  }

  export class Worker<T = unknown> {
    constructor(name: string, processor: (job: Job<T>) => Promise<unknown>, options?: Record<string, unknown>);
    on(event: string, handler: (...args: any[]) => void): void;
    close(): Promise<void>;
  }
}
