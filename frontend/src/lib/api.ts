/**
 * Standardized API Client for Plexudo Backend (/api/v1/*)
 * - Automatically sends HttpOnly session cookies (credentials: 'include')
 * - Injects X-CSRF-Token on mutating requests (POST, PATCH, DELETE)
 * - Never leaks or relies on localStorage for authentication authority
 */

let memoryCsrfToken: string | null = null;

export function setCsrfToken(token: string | null) {
  memoryCsrfToken = token;
}

export function getCsrfToken(): string | null {
  return memoryCsrfToken;
}

export class ApiError extends Error {
  status: number;
  detail: any;

  constructor(status: number, detail: any) {
    super(typeof detail === 'string' ? detail : JSON.stringify(detail));
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = endpoint.startsWith('/') ? endpoint : `/api/v1/${endpoint}`;
  
  const headers = new Headers(options.headers || {});
  
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  // Inject CSRF token on mutating requests if present
  if (['POST', 'PATCH', 'PUT', 'DELETE'].includes(options.method?.toUpperCase() || '') && memoryCsrfToken) {
    headers.set('X-CSRF-Token', memoryCsrfToken);
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include', // Ensures HttpOnly session cookies are transmitted
  });

  if (response.status === 204) {
    return {} as T;
  }

  const isJson = response.headers.get('content-type')?.includes('application/json');
  const data = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const detail = isJson ? (data.detail || data.message || data) : data;
    throw new ApiError(response.status, detail);
  }

  return data as T;
}

export const api = {
  get: <T>(endpoint: string, options?: RequestInit) => request<T>(endpoint, { ...options, method: 'GET' }),
  post: <T>(endpoint: string, body?: any, options?: RequestInit) =>
    request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  patch: <T>(endpoint: string, body?: any, options?: RequestInit) =>
    request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  delete: <T>(endpoint: string, options?: RequestInit) => request<T>(endpoint, { ...options, method: 'DELETE' }),
};
