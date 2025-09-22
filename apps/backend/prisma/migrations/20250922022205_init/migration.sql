-- CreateTable
CREATE TABLE "public"."users" (
    "id" SERIAL NOT NULL,
    "username" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "password_hash" TEXT,
    "first_name" TEXT,
    "last_name" TEXT,
    "avatar_url" TEXT,
    "is_admin" BOOLEAN NOT NULL DEFAULT false,
    "roles" TEXT[] DEFAULT ARRAY['member']::TEXT[],
    "notification_preferences" JSONB NOT NULL DEFAULT '{}',
    "auth_provider" TEXT,
    "auth_provider_id" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."households" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "primary_email" TEXT,
    "primary_phone" TEXT,
    "address_line1" TEXT,
    "address_line2" TEXT,
    "city" TEXT,
    "state" TEXT,
    "postal_code" TEXT,
    "notes" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "households_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."members" (
    "id" SERIAL NOT NULL,
    "first_name" TEXT NOT NULL,
    "last_name" TEXT,
    "email" TEXT NOT NULL,
    "phone" TEXT,
    "birth_date" DATE,
    "gender" TEXT,
    "marital_status" TEXT,
    "membership_status" TEXT NOT NULL DEFAULT 'guest',
    "assimilation_stage" TEXT,
    "campus" TEXT,
    "milestones" JSONB NOT NULL DEFAULT '{}',
    "notes" TEXT,
    "preferred_contact_method" TEXT,
    "joined_at" DATE,
    "last_interaction_at" TIMESTAMP(3),
    "next_follow_up_date" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INTEGER,
    "household_id" INTEGER,

    CONSTRAINT "members_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."account_providers" (
    "id" SERIAL NOT NULL,
    "user_id" INTEGER NOT NULL,
    "provider" TEXT NOT NULL,
    "provider_id" TEXT NOT NULL,
    "access_token" TEXT,
    "refresh_token" TEXT,
    "expires_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "account_providers_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."care_interactions" (
    "id" SERIAL NOT NULL,
    "member_id" INTEGER NOT NULL,
    "interaction_type" TEXT NOT NULL,
    "interaction_date" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "notes" TEXT,
    "follow_up_required" BOOLEAN NOT NULL DEFAULT false,
    "follow_up_date" TIMESTAMP(3),
    "created_by_id" INTEGER,
    "source" TEXT,
    "extra_data" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "care_interactions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."prayer_requests" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "email" TEXT,
    "phone" TEXT,
    "request" TEXT NOT NULL,
    "member_id" TEXT,
    "status" TEXT NOT NULL DEFAULT 'new',
    "follow_up_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "is_public" BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT "prayer_requests_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."ministry_departments" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "lead_id" INTEGER,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ministry_departments_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."volunteer_roles" (
    "id" SERIAL NOT NULL,
    "department_id" INTEGER NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "coordinator_id" INTEGER,
    "needed_volunteers" INTEGER NOT NULL DEFAULT 1,
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "volunteer_roles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."volunteer_assignments" (
    "id" SERIAL NOT NULL,
    "role_id" INTEGER NOT NULL,
    "volunteer_id" INTEGER NOT NULL,
    "event_id" INTEGER,
    "start_date" DATE,
    "end_date" DATE,
    "notes" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "volunteer_assignments_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."events" (
    "id" SERIAL NOT NULL,
    "title" TEXT NOT NULL,
    "description" TEXT,
    "start_date" TIMESTAMP(3) NOT NULL,
    "end_date" TIMESTAMP(3) NOT NULL,
    "timezone" TEXT NOT NULL DEFAULT 'UTC',
    "location" TEXT,
    "campus" TEXT,
    "recurrence_rule" TEXT,
    "recurrence_end_date" TIMESTAMP(3),
    "service_segments" JSONB NOT NULL DEFAULT '[]',
    "ministry_tags" JSONB NOT NULL DEFAULT '[]',
    "department_id" INTEGER,
    "volunteer_role_id" INTEGER,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "events_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."sermons" (
    "id" SERIAL NOT NULL,
    "title" TEXT NOT NULL,
    "description" TEXT,
    "preacher" TEXT,
    "date" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "media_url" TEXT,
    "media_type" TEXT,

    CONSTRAINT "sermons_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."gallery" (
    "id" SERIAL NOT NULL,
    "title" TEXT,
    "image_url" TEXT NOT NULL,
    "description" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "gallery_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."churches" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "address" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "churches_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."donations" (
    "id" SERIAL NOT NULL,
    "member_id" INTEGER,
    "email" TEXT,
    "amount" DECIMAL(10,2) NOT NULL,
    "currency" TEXT NOT NULL DEFAULT 'USD',
    "reference" TEXT,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "payment_method" TEXT NOT NULL,
    "transaction_id" TEXT,
    "error_message" TEXT,
    "payment_info" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "donations_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."service_integrations" (
    "id" SERIAL NOT NULL,
    "service" TEXT NOT NULL,
    "provider" TEXT NOT NULL,
    "display_name" TEXT NOT NULL,
    "config" JSONB NOT NULL DEFAULT '{}',
    "is_active" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "service_integrations_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."settings" (
    "id" SERIAL NOT NULL,
    "business_name" TEXT NOT NULL DEFAULT 'Covenant Connect',
    "logo_url" TEXT,
    "theme_preference" TEXT NOT NULL DEFAULT 'dark',
    "addresses" JSONB NOT NULL DEFAULT '[]',
    "social_media_links" JSONB NOT NULL DEFAULT '{}',
    "contact_info" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "settings_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."automations" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "trigger" TEXT NOT NULL,
    "description" TEXT,
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "default_channel" TEXT,
    "target_department" TEXT,
    "trigger_filters" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "automations_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."automation_steps" (
    "id" SERIAL NOT NULL,
    "automation_id" INTEGER NOT NULL,
    "title" TEXT,
    "action_type" TEXT NOT NULL,
    "channel" TEXT,
    "department" TEXT,
    "order" INTEGER NOT NULL DEFAULT 0,
    "delay_minutes" INTEGER NOT NULL DEFAULT 0,
    "config" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "automation_steps_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."facilities" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "location" TEXT,
    "capacity" INTEGER NOT NULL DEFAULT 0,
    "description" TEXT,
    "is_active" BOOLEAN NOT NULL DEFAULT true,

    CONSTRAINT "facilities_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."resources" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "category" TEXT,
    "quantity_available" INTEGER NOT NULL DEFAULT 1,
    "description" TEXT,
    "facility_id" INTEGER,
    "is_active" BOOLEAN NOT NULL DEFAULT true,

    CONSTRAINT "resources_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."facility_reservations" (
    "id" SERIAL NOT NULL,
    "event_id" INTEGER NOT NULL,
    "facility_id" INTEGER NOT NULL,
    "ministry_name" TEXT NOT NULL,
    "start_time" TIMESTAMP(3) NOT NULL,
    "end_time" TIMESTAMP(3) NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'requested',

    CONSTRAINT "facility_reservations_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."resource_allocations" (
    "id" SERIAL NOT NULL,
    "reservation_id" INTEGER NOT NULL,
    "resource_id" INTEGER NOT NULL,
    "quantity_requested" INTEGER NOT NULL DEFAULT 1,
    "quantity_approved" INTEGER,
    "notes" TEXT,

    CONSTRAINT "resource_allocations_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."attendance_records" (
    "id" SERIAL NOT NULL,
    "event_id" INTEGER NOT NULL,
    "role_id" INTEGER,
    "volunteer_id" INTEGER,
    "check_in_time" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expected_attendees" INTEGER,
    "checked_in_count" INTEGER NOT NULL DEFAULT 0,
    "notes" TEXT,

    CONSTRAINT "attendance_records_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "public"."sessions" (
    "token" TEXT NOT NULL,
    "user_id" INTEGER NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expires_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "sessions_pkey" PRIMARY KEY ("token")
);

-- CreateIndex
CREATE UNIQUE INDEX "users_username_key" ON "public"."users"("username");

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "public"."users"("email");

-- CreateIndex
CREATE UNIQUE INDEX "uq_users_provider_identity" ON "public"."users"("auth_provider", "auth_provider_id");

-- CreateIndex
CREATE UNIQUE INDEX "members_email_key" ON "public"."members"("email");

-- CreateIndex
CREATE UNIQUE INDEX "members_user_id_key" ON "public"."members"("user_id");

-- CreateIndex
CREATE UNIQUE INDEX "uq_account_providers_identity" ON "public"."account_providers"("provider", "provider_id");

-- CreateIndex
CREATE UNIQUE INDEX "ministry_departments_name_key" ON "public"."ministry_departments"("name");

-- CreateIndex
CREATE UNIQUE INDEX "donations_reference_key" ON "public"."donations"("reference");

-- CreateIndex
CREATE UNIQUE INDEX "donations_transaction_id_key" ON "public"."donations"("transaction_id");

-- CreateIndex
CREATE UNIQUE INDEX "uq_service_provider" ON "public"."service_integrations"("service", "provider");

-- AddForeignKey
ALTER TABLE "public"."members" ADD CONSTRAINT "members_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."members" ADD CONSTRAINT "members_household_id_fkey" FOREIGN KEY ("household_id") REFERENCES "public"."households"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."account_providers" ADD CONSTRAINT "account_providers_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."care_interactions" ADD CONSTRAINT "care_interactions_member_id_fkey" FOREIGN KEY ("member_id") REFERENCES "public"."members"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."care_interactions" ADD CONSTRAINT "care_interactions_created_by_id_fkey" FOREIGN KEY ("created_by_id") REFERENCES "public"."users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."ministry_departments" ADD CONSTRAINT "ministry_departments_lead_id_fkey" FOREIGN KEY ("lead_id") REFERENCES "public"."users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."volunteer_roles" ADD CONSTRAINT "volunteer_roles_department_id_fkey" FOREIGN KEY ("department_id") REFERENCES "public"."ministry_departments"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."volunteer_roles" ADD CONSTRAINT "volunteer_roles_coordinator_id_fkey" FOREIGN KEY ("coordinator_id") REFERENCES "public"."users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."volunteer_assignments" ADD CONSTRAINT "volunteer_assignments_role_id_fkey" FOREIGN KEY ("role_id") REFERENCES "public"."volunteer_roles"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."volunteer_assignments" ADD CONSTRAINT "volunteer_assignments_volunteer_id_fkey" FOREIGN KEY ("volunteer_id") REFERENCES "public"."users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."volunteer_assignments" ADD CONSTRAINT "volunteer_assignments_event_id_fkey" FOREIGN KEY ("event_id") REFERENCES "public"."events"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."events" ADD CONSTRAINT "events_department_id_fkey" FOREIGN KEY ("department_id") REFERENCES "public"."ministry_departments"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."events" ADD CONSTRAINT "events_volunteer_role_id_fkey" FOREIGN KEY ("volunteer_role_id") REFERENCES "public"."volunteer_roles"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."donations" ADD CONSTRAINT "donations_member_id_fkey" FOREIGN KEY ("member_id") REFERENCES "public"."members"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."automation_steps" ADD CONSTRAINT "automation_steps_automation_id_fkey" FOREIGN KEY ("automation_id") REFERENCES "public"."automations"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."resources" ADD CONSTRAINT "resources_facility_id_fkey" FOREIGN KEY ("facility_id") REFERENCES "public"."facilities"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."facility_reservations" ADD CONSTRAINT "facility_reservations_event_id_fkey" FOREIGN KEY ("event_id") REFERENCES "public"."events"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."facility_reservations" ADD CONSTRAINT "facility_reservations_facility_id_fkey" FOREIGN KEY ("facility_id") REFERENCES "public"."facilities"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."resource_allocations" ADD CONSTRAINT "resource_allocations_reservation_id_fkey" FOREIGN KEY ("reservation_id") REFERENCES "public"."facility_reservations"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."resource_allocations" ADD CONSTRAINT "resource_allocations_resource_id_fkey" FOREIGN KEY ("resource_id") REFERENCES "public"."resources"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."attendance_records" ADD CONSTRAINT "attendance_records_event_id_fkey" FOREIGN KEY ("event_id") REFERENCES "public"."events"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."attendance_records" ADD CONSTRAINT "attendance_records_role_id_fkey" FOREIGN KEY ("role_id") REFERENCES "public"."volunteer_roles"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."attendance_records" ADD CONSTRAINT "attendance_records_volunteer_id_fkey" FOREIGN KEY ("volunteer_id") REFERENCES "public"."users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "public"."sessions" ADD CONSTRAINT "sessions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- Seed essential configuration rows
INSERT INTO "public"."settings" ("id", "business_name", "theme_preference", "addresses", "social_media_links", "contact_info")
VALUES (1, 'Covenant Connect', 'dark', '[]'::jsonb, '{}'::jsonb, '{}'::jsonb)
ON CONFLICT ("id") DO NOTHING;

INSERT INTO "public"."churches" ("id", "name", "address")
VALUES (1, 'Covenant Connect Church', '123 Covenant Way')
ON CONFLICT ("id") DO NOTHING;
