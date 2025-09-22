export type Provider = 'google' | 'facebook' | 'apple' | 'password';

export type UserAccount = {
  id: string;
  email: string;
  passwordHash?: string;
  firstName: string;
  lastName: string;
  avatarUrl?: string;
  createdAt: Date;
  updatedAt: Date;
  roles: string[];
  providers: ProviderIdentity[];
};

export type ProviderIdentity = {
  provider: Provider;
  providerId: string;
  accessToken?: string;
  refreshToken?: string;
  expiresAt?: Date | null;
};

export type MemberProfile = {
  id: string;
  userId: string;
  phone?: string;
  address?: string;
  dateOfBirth?: string;
  gender?: 'male' | 'female' | 'unspecified';
  nextSteps: string[];
  createdAt: Date;
  updatedAt: Date;
};

export type Donation = {
  id: string;
  memberId: string | null;
  amount: number;
  currency: string;
  provider: 'paystack' | 'fincra' | 'stripe' | 'flutterwave';
  status: 'pending' | 'completed' | 'failed' | 'refunded';
  metadata: Record<string, unknown>;
  createdAt: Date;
  updatedAt: Date;
};

export type EventSegment = {
  id: string;
  name: string;
  startOffsetMinutes: number;
  durationMinutes: number;
  ownerId: string | null;
};

export type Event = {
  id: string;
  title: string;
  description?: string;
  startsAt: Date;
  endsAt: Date;
  timezone: string;
  recurrenceRule?: string;
  segments: EventSegment[];
  tags: string[];
  location: string;
  createdAt: Date;
  updatedAt: Date;
};

export type PrayerRequest = {
  id: string;
  requesterName: string;
  requesterEmail?: string;
  requesterPhone?: string;
  message: string;
  memberId?: string;
  status: 'new' | 'assigned' | 'praying' | 'answered';
  followUpAt?: Date;
  createdAt: Date;
  updatedAt: Date;
};

export type Automation = {
  id: string;
  name: string;
  trigger: string;
  isActive: boolean;
  steps: AutomationStep[];
};

export type AutomationStep = {
  id: string;
  type: 'email' | 'sms' | 'task' | 'webhook';
  configuration: Record<string, unknown>;
  delaySeconds: number;
};

export type EmailProviderType = 'ses' | 'mailgun' | 'smtp';

export type EmailProvider = {
  id: string;
  type: EmailProviderType;
  name: string;
  credentials: Record<string, string>;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
};

export type DashboardKpi = {
  label: string;
  value: number;
  change?: number;
};

export type Sermon = {
  id: string;
  title: string;
  speaker: string;
  description?: string;
  mediaUrl?: string;
  recordedAt?: Date;
};

export type HomeContent = {
  heroTitle: string;
  heroSubtitle: string;
  highlights: string[];
  nextSteps: { label: string; url: string }[];
};

export type VolunteerAssignment = {
  id: string;
  eventId: string;
  memberId: string;
  role: string;
  status: 'confirmed' | 'pending' | 'declined';
};

export type IntegrationSetting = {
  id: number;
  provider: string;
  config: Record<string, string>;
  createdAt: Date;
  updatedAt: Date;
};

export type Church = {
  id: string;
  name: string;
  timezone: string;
  country?: string;
  state?: string;
  city?: string;
  settings: Record<string, unknown>;
  createdAt: Date;
  updatedAt: Date;
};

export type NotificationPreference = {
  memberId: string;
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
