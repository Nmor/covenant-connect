-- AlterTable
ALTER TABLE "public"."churches"
ADD COLUMN     "timezone" TEXT,
ADD COLUMN     "country" TEXT,
ADD COLUMN     "state" TEXT,
ADD COLUMN     "city" TEXT,
ADD COLUMN     "settings" JSONB DEFAULT '{}'::jsonb,
ADD COLUMN     "updated_at" TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP;

UPDATE "public"."churches"
SET "timezone" = COALESCE("timezone", 'UTC'),
    "settings" = COALESCE("settings", '{}'::jsonb),
    "updated_at" = COALESCE("updated_at", CURRENT_TIMESTAMP);

ALTER TABLE "public"."churches"
ALTER COLUMN "timezone" SET NOT NULL,
ALTER COLUMN "settings" SET NOT NULL,
ALTER COLUMN "updated_at" SET NOT NULL;
