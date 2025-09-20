import 'reflect-metadata';

import { Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { NestFactory } from '@nestjs/core';
import helmet from 'helmet';

import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule, {
    bufferLogs: true
  });

  const configService = app.get(ConfigService);
  const port = configService.get<number>('application.http.port', 8000);
  const corsOrigins = configService.get<string[]>('application.http.cors', []);

  app.useLogger(app.get(Logger));
  app.use(helmet());
  app.enableCors({
    origin: corsOrigins,
    credentials: true
  });

  await app.listen(port);
  Logger.log(`Covenant Connect API listening on port ${port}`, 'Bootstrap');
}

bootstrap().catch((error) => {
  Logger.error('Fatal error during Nest bootstrap', error.stack);
  process.exit(1);
});
