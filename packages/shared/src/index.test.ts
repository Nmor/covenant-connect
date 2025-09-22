import { describe, expect, it } from 'vitest';

import { type PaginatedResult } from './index';

describe('shared type utilities', () => {
  it('creates a strongly typed paginated result', () => {
    const result: PaginatedResult<string> = {
      data: ['alpha', 'omega'],
      total: 2,
      page: 1,
      pageSize: 10,
    };

    expect(result).toMatchObject({
      data: ['alpha', 'omega'],
      total: 2,
      page: 1,
      pageSize: 10,
    });
  });
});
