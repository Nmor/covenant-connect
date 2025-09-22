declare global {
  interface JestMatchers {
    toEqual(expected: unknown): void;
    toBe(value: unknown): void;
    toHaveBeenCalledWith(...args: unknown[]): void;
    toHaveBeenCalledTimes(count: number): void;
    toHaveBeenCalled(): void;
    toMatchObject(partial: unknown): void;
  }

  interface JestExpect {
    (actual: unknown): JestMatchers & {
      rejects: { toBeInstanceOf(expected: unknown): void };
    };
    objectContaining<T>(value: T): T;
    arrayContaining<T>(values: T[]): T[];
  }

  const expect: JestExpect;

  function describe(name: string, fn: () => void): void;
  function beforeEach(fn: () => void | Promise<void>): void;
  function it(name: string, fn: () => void | Promise<void>): void;

  namespace jest {
    type Mock<T = any, Y extends any[] = any[]> = ((...args: Y) => T) & {
      mockResolvedValue(value: T extends Promise<infer R> ? R : unknown): void;
      mockRejectedValue(value: unknown): void;
      mockReturnValue(value: T): void;
      mockReset(): void;
    };

    type Mocked<T> = {
      [K in keyof T]: T[K] extends (...args: infer A) => infer R ? Mock<R, A> : T[K];
    };

    interface Matchers<R> {
      toBe(value: any): R;
    }

    function fn<T extends (...args: any[]) => any>(implementation?: T): Mock<ReturnType<T>, Parameters<T>>;
  }
}

export {};
