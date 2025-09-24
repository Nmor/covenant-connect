export type {
  Prisma,
  PrismaClient,
  User,
  Member,
  AccountProvider,
  Donation,
  Event,
  PrayerRequest,
  Automation,
  AutomationStep,
  VolunteerAssignment,
  IntegrationSetting,
  Sermon,
} from './generated/prisma';

import type {
  AccountProvider,
  User,
  Member,
  EmailProvider as PrismaEmailProvider,
  Church as PrismaChurch,
} from './generated/prisma';

export type Provider = 'google' | 'facebook' | 'apple' | 'password';

export type ProviderIdentity = AccountProvider;
export type UserAccount = User;
export type MemberProfile = Member;
export type EmailProvider = PrismaEmailProvider;

export type Church = Omit<
  PrismaChurch,
  'id' | 'address' | 'country' | 'state' | 'city' | 'settings'
> & {
  id: string;
  address?: string;
  country?: string;
  state?: string;
  city?: string;
  settings: Record<string, unknown>;
};

export type EventSegment = {
  id: string;
  name: string;
  startOffsetMinutes: number;
  durationMinutes: number;
  ownerId: string | null;
};

export type EmailProviderType = 'ses' | 'mailgun' | 'smtp';

export type DashboardKpi = {
  label: string;
  value: number;
  change?: number;
};

export type HomeContent = {
  heroTitle: string;
  heroSubtitle: string;
  highlights: string[];
  nextSteps: { label: string; url: string }[];
};

export type NotificationPreference = {
  memberId: Member['id'];
  email: boolean;
  sms: boolean;
  push: boolean;
};

export type Pagination = {
  page: number;
  pageSize: number;
};

export type PaginatedResult<T> = {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
};

export type DateRange = {
  start: Date;
  end: Date;
};

export type SearchQuery = {
  term?: string;
  tags?: string[];
  dateRange?: DateRange;
};

export type Attachment = {
  id: string;
  filename: string;
  mimeType: string;
  size: number;
  url: string;
};

export type QueueJob = {
  id: string;
  name: string;
  payload: Record<string, unknown>;
  scheduledAt: Date;
};
