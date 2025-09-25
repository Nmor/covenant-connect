import path from 'path';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  resolve: {
    alias: {
      '@covenant-connect/shared': path.resolve(__dirname, '../../packages/shared/src')
    }
  },
  test: {
    environment: 'node',
    include: ['test/**/*.spec.ts', 'test/**/*.test.ts', 'test/**/*.test.js'],
    globals: true,
    setupFiles: ['./test/setup.js'],
    hookTimeout: 120000,
    testTimeout: 120000,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov']
    }
  }
});
