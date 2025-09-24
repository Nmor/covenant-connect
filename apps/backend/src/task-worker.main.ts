import 'reflect-metadata';

import { Logger } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';

import { AppModule } from './app.module';

async function bootstrapWorker() {
  process.env.SKIP_TASKS_QUEUE = process.env.SKIP_TASKS_QUEUE ?? 'false';

  const app = await NestFactory.createApplicationContext(AppModule, {
    bufferLogs: true
  });

  const logger = app.get(Logger);
  logger.log('Covenant Connect task worker initialised', 'TaskWorkerBootstrap');

  const handleShutdown = async (signal: NodeJS.Signals) => {
    logger.log(`Received ${signal}; shutting down task worker`, 'TaskWorkerBootstrap');
    await app.close();
    process.exit(0);
  };

  process.on('SIGINT', handleShutdown);
  process.on('SIGTERM', handleShutdown);
}

bootstrapWorker().catch((error) => {
  Logger.error('Fatal error during task worker bootstrap', (error as Error)?.stack ?? String(error));
  process.exit(1);
});
