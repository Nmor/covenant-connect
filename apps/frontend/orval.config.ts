import { defineConfig } from 'orval';

export default defineConfig({
  covenantConnect: {
    input: '../backend/openapi.json',
    output: {
      target: './lib/generated/client.ts',
      schemas: './lib/generated/schemas',
      client: 'fetch',
      clean: true,
      override: {
        mutator: {
          path: './lib/http.ts',
          name: 'apiFetcher'
        }
      }
    }
  }
});
