import { registerAs } from '@nestjs/config';

type StorageDrivers = 's3' | 'local';

type StorageConfig = {
  driver: StorageDrivers;
  s3?: {
    bucket: string;
    region: string;
    accessKeyId: string;
    secretAccessKey: string;
  };
  local?: {
    directory: string;
  };
};

export const storageConfig = registerAs<StorageConfig>('storage', () => {
  const driver = (process.env.STORAGE_DRIVER ?? 'local') as StorageDrivers;

  if (driver === 's3') {
    return {
      driver,
      s3: {
        bucket: process.env.AWS_S3_BUCKET ?? '',
        region: process.env.AWS_REGION ?? 'us-east-1',
        accessKeyId: process.env.AWS_ACCESS_KEY_ID ?? '',
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY ?? ''
      }
    } satisfies StorageConfig;
  }

  return {
    driver: 'local',
    local: {
      directory: process.env.LOCAL_STORAGE_DIR ?? './uploads'
    }
  } satisfies StorageConfig;
});
