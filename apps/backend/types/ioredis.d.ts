declare module 'ioredis' {
  export type RedisOptions = Record<string, unknown>;

  export class Redis {
    constructor(...args: Array<string | RedisOptions | number | null>);
    duplicate(): Redis;
    quit(): Promise<void>;
  }

  export default Redis;
}
