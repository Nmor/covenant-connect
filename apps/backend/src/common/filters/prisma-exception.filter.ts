import { ArgumentsHost, BadRequestException, Catch, ConflictException, ExceptionFilter, NotFoundException } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import type { Request, Response } from 'express';

@Catch(Prisma.PrismaClientKnownRequestError)
export class PrismaExceptionFilter implements ExceptionFilter {
  catch(exception: Prisma.PrismaClientKnownRequestError, host: ArgumentsHost): void {
    let error: BadRequestException | ConflictException | NotFoundException;

    switch (exception.code) {
      case 'P2002':
        error = new ConflictException('A record with the provided details already exists.');
        break;
      case 'P2025':
        error = new NotFoundException('The requested resource could not be found.');
        break;
      default:
        error = new BadRequestException('An unexpected database error occurred.');
    }

    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();
    const status = error.getStatus();

    response.status(status).json({
      statusCode: status,
      message: error.message,
      error: error.name,
      path: request.url,
      timestamp: new Date().toISOString()
    });
  }
}
