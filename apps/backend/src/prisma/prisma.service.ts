import { Injectable, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PrismaClient } from '@prisma/client';

@Injectable()
export class PrismaService extends PrismaClient implements OnModuleInit, OnModuleDestroy {
  constructor(configService: ConfigService) {
    const databaseUrl =
      configService.get<string>('database.url') ??
      configService.get<string>('application.databaseUrl') ??
      'postgresql://postgres@localhost:5432/covenant_dev?schema=public';

    super({
      datasources: {
        db: {
          url: databaseUrl
        }
      }
    });
  }

  async onModuleInit(): Promise<void> {
    await this.$connect();
  }

  async onModuleDestroy(): Promise<void> {
    await this.$disconnect();
  }
}
