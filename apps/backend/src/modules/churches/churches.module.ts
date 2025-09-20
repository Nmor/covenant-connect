import { Module } from '@nestjs/common';

import { ChurchesController } from './churches.controller';
import { ChurchesService } from './churches.service';

@Module({
  controllers: [ChurchesController],
  providers: [ChurchesService],
  exports: [ChurchesService]
})
export class ChurchesModule {}
