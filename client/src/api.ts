export type ApiError = Error & { status?: number };

export async function apiRequest(path: string, options?: RequestInit): Promise<Response> {
  const headers = new Headers(options?.headers);
  const token = localStorage.getItem('access_token');
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(`/api${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === 'string' ? body.detail : 'The request failed.';
    const message = response.status === 401 ? 'Please log in again.' : detail;
    throw Object.assign(new Error(message), { status: response.status });
  }
  return response;
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await apiRequest(path, options);
  return response.json();
}
