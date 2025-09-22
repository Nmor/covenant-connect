import type { INestApplication } from '@nestjs/common';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';

export const OPENAPI_DOCUMENT_PATH = 'docs';

function buildDocumentConfig() {
  return new DocumentBuilder()
    .setTitle('Covenant Connect API')
    .setDescription('OpenAPI documentation for the Covenant Connect backend services.')
    .setVersion('1.0.0')
    .build();
}

export function createOpenApiDocument(app: INestApplication) {
  return SwaggerModule.createDocument(app, buildDocumentConfig());
}

export function setupSwagger(app: INestApplication) {
  const document = createOpenApiDocument(app);
  SwaggerModule.setup(OPENAPI_DOCUMENT_PATH, app, document, {
    swaggerOptions: {
      persistAuthorization: true
    }
  });

  return document;
}
