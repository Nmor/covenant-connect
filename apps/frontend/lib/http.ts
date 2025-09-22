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

const isBodyInit = (value: unknown): value is BodyInit => {
  if (value === null || value === undefined) {
    return false;
  }

  if (typeof value === 'string' || value instanceof Blob || value instanceof FormData || value instanceof URLSearchParams) {
    return true;
  }

  if (typeof ArrayBuffer !== 'undefined' && (value instanceof ArrayBuffer || ArrayBuffer.isView(value))) {
    return true;
  }

  if (typeof ReadableStream !== 'undefined' && value instanceof ReadableStream) {
    return true;
  }

  return false;
};

const prepareBody = (body: unknown): BodyInit | undefined => {
  if (body === undefined || body === null) {
    return undefined;
  }

  if (isBodyInit(body)) {
    return body;
  }

  if (typeof body === 'object') {
    return JSON.stringify(body);
  }

  return String(body);
};

const buildQueryString = (query?: Record<string, unknown>): string => {
  if (!query) {
    return '';
  }

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) {
      continue;
    }

    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (item === undefined || item === null) {
          return;
        }
        params.append(key, String(item));
      });
      continue;
    }

    params.set(key, String(value));
  }

  const queryString = params.toString();
  return queryString ? `?${queryString}` : '';
};

export async function apiRequest<T>(path: string, init: RequestInit = {}, baseUrl: string = API_BASE_URL): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Accept', headers.get('Accept') ?? 'application/json');

  if (init.body && !headers.has('Content-Type') && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${baseUrl}${ensureLeadingSlash(path)}`, {
    ...init,
    headers,
    cache: init.cache ?? 'no-store'
  });

  const rawBody = await response.text();
  let data: unknown = rawBody.length ? rawBody : null;

  if (rawBody.length) {
    try {
      data = JSON.parse(rawBody);
    } catch {
      // Non-JSON payloads fall back to the raw string response.
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, response.statusText, data ?? undefined);
  }

  return data as T;
}

export type ApiFetcherInit<TRequest> = Omit<RequestInit, 'body'> & {
  body?: TRequest;
  query?: Record<string, unknown>;
  baseUrl?: string;
};

export async function apiFetcher<TResponse, TRequest = unknown>(
  url: string,
  init: ApiFetcherInit<TRequest> = {}
): Promise<Awaited<TResponse>> {
  const { query, body, baseUrl, ...rest } = init;
  const requestInit: RequestInit = { ...rest };
  const preparedBody = prepareBody(body);

  if (preparedBody !== undefined) {
    requestInit.body = preparedBody;
  }

  const queryString = buildQueryString(query);

  return apiRequest<Awaited<TResponse>>(
    `${url}${queryString}`,
    requestInit as RequestInit,
    baseUrl ?? API_BASE_URL
  );
}
