import { Logger } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';

import { AppModule } from '../app.module';
import { createOpenApiDocument } from '../common/openapi';

process.env.SKIP_PRISMA_CONNECT = 'true';
process.env.SKIP_TASKS_QUEUE = 'true';

async function generateOpenApiSchema(): Promise<void> {
  console.log('Starting Nest application for OpenAPI generation...');
  const app = await NestFactory.create(AppModule, {
    logger: ['error', 'warn'],
    bufferLogs: true
  });

  try {
    console.log('Initializing Nest application context...');
    await app.init();
    console.log('Creating OpenAPI document...');
    const document = createOpenApiDocument(app);
    const outputPath = join(__dirname, '../../../openapi.json');
    await mkdir(dirname(outputPath), { recursive: true });
    await writeFile(outputPath, JSON.stringify(document, null, 2), 'utf8');
    const message = `OpenAPI schema written to ${outputPath}`;
    Logger.log(message, 'OpenAPIGenerator');
    console.log(message);
  } finally {
    await app.close();
  }
}

generateOpenApiSchema().catch((error) => {
  Logger.error('Failed to generate OpenAPI schema', error.stack, 'OpenAPIGenerator');
  console.error(error);
  process.exit(1);
});
