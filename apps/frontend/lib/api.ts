const ensureLeadingSlash = (path: string): string => (path.startsWith('/') ? path : `/${path}`);

const normalizeBaseUrl = (input: string | undefined): string => {
  const trimmed = input?.trim();
  if (!trimmed) {
    return 'http://localhost:8000';
  }

  return trimmed.replace(/\/$/, '');
};

export const API_BASE_URL = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly statusText: string,
    public readonly detail?: unknown
  ) {
    super(
      detail
        ? `API request failed with status ${status} ${statusText}: ${
            typeof detail === 'string' ? detail : JSON.stringify(detail)
          }`
        : `API request failed with status ${status} ${statusText}`
    );
    this.name = 'ApiError';
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Accept', headers.get('Accept') ?? 'application/json');

  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE_URL}${ensureLeadingSlash(path)}`, {
    ...init,
    headers,
    cache: init.cache ?? 'no-store'
  });

  const rawBody = await response.text();
  let data: unknown = rawBody.length ? rawBody : null;

  if (rawBody.length) {
    try {
      data = JSON.parse(rawBody);
    } catch (error) {
      // Non-JSON payloads fall back to the raw string response.
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, response.statusText, data ?? undefined);
  }

  return data as T;
}

export type DashboardKpi = {
  label: string;
  value: number;
  change?: number;
};

export type DashboardResponse = {
  kpis: DashboardKpi[];
};

export type HomeContentResponse = {
  heroTitle: string;
  heroSubtitle: string;
  highlights: string[];
  nextSteps: { label: string; url: string }[];
};

export type PaginatedResponse<T> = {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
};

export type EventSummary = {
  id: string;
  title: string;
  startsAt: string;
  endsAt: string;
  timezone: string;
  location: string;
  recurrenceRule?: string;
  tags?: string[];
};

export type EventsResponse = PaginatedResponse<EventSummary>;

export type DonationRecord = {
  id: string;
  memberId: string | null;
  amount: number;
  currency: string;
  provider: 'paystack' | 'fincra' | 'stripe' | 'flutterwave';
  status: 'pending' | 'completed' | 'failed' | 'refunded';
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
};

export type DonationsResponse = PaginatedResponse<DonationRecord>;

export type PrayerRequestRecord = {
  id: string;
  requesterName: string;
  requesterEmail?: string;
  requesterPhone?: string;
  message: string;
  memberId?: string;
  status: 'new' | 'assigned' | 'praying' | 'answered';
  followUpAt?: string;
  createdAt: string;
  updatedAt: string;
};

export type PrayerRequestsResponse = PaginatedResponse<PrayerRequestRecord>;

export async function getDashboardReport(): Promise<DashboardResponse> {
  return apiRequest<DashboardResponse>('/reports/dashboard');
}

export async function getHomeContent(): Promise<HomeContentResponse> {
  return apiRequest<HomeContentResponse>('/content/home');
}

export async function getUpcomingEvents(limit = 3): Promise<EventsResponse> {
  return getEvents({ page: 1, pageSize: limit });
}

export async function getEvents({
  page = 1,
  pageSize = 25
}: {
  page?: number;
  pageSize?: number;
} = {}): Promise<EventsResponse> {
  const search = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });
  return apiRequest<EventsResponse>(`/events?${search.toString()}`);
}

export async function getDonations({
  page = 1,
  pageSize = 25
}: {
  page?: number;
  pageSize?: number;
} = {}): Promise<DonationsResponse> {
  const search = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });
  return apiRequest<DonationsResponse>(`/donations?${search.toString()}`);
}

export async function getPrayerRequests(): Promise<PrayerRequestsResponse> {
  return apiRequest<PrayerRequestsResponse>('/prayer/requests');
}
