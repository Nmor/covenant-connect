-- CreateTable
CREATE TABLE "public"."email_providers" (
    "id" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "credentials" JSONB NOT NULL DEFAULT '{}',
    "is_active" BOOLEAN NOT NULL DEFAULT FALSE,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "email_providers_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "email_providers_is_active_idx" ON "public"."email_providers"("is_active");
