const ensureLeadingSlash = (path: string): string => (path.startsWith('/') ? path : `/${path}`);

const normalizeBaseUrl = (input: string | undefined): string => {
  const trimmed = input?.trim();
  if (!trimmed) {
    return 'http://localhost:8000';
  }

  return trimmed.replace(/\/$/, '');
};

const API_BASE_URL = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);

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

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${ensureLeadingSlash(path)}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init.headers ?? {})
    },
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

export async function getDashboardReport(): Promise<DashboardResponse> {
  return request<DashboardResponse>('/reports/dashboard');
}

export async function getHomeContent(): Promise<HomeContentResponse> {
  return request<HomeContentResponse>('/content/home');
}

export async function getUpcomingEvents(limit = 3): Promise<EventsResponse> {
  const search = new URLSearchParams({ page: '1', pageSize: String(limit) });
  return request<EventsResponse>(`/events?${search.toString()}`);
}

export { API_BASE_URL };
