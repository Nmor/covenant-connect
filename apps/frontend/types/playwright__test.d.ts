export interface Locator {
  click(): Promise<void>;
  fill(value: string): Promise<void>;
  getByText(text: string | RegExp): Locator;
}

export interface Page {
  goto(url: string): Promise<void>;
  getByRole(role: string, options?: Record<string, unknown>): Locator;
  getByText(text: string | RegExp, options?: Record<string, unknown>): Locator;
  getByLabel(label: string, options?: Record<string, unknown>): Locator;
}

type TestCallback = (args: { page: Page }) => Promise<void> | void;

declare module '@playwright/test' {
  export const devices: Record<string, Record<string, unknown>>;
  export function defineConfig<T>(config: T): T;

  interface TestAPI {
    (name: string, fn: TestCallback): void;
    describe(name: string, fn: () => void): void;
  }

  export const test: TestAPI;

  export function expect<T>(actual: T): {
    toBeVisible(): void;
    toHaveCount(count: number): void;
    toBeTruthy(): void;
  };
}
