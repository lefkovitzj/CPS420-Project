export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  const token = localStorage.getItem('access_token');
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(`/api${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = response.status === 401 ? 'Please log in again.' : 'The request failed.';
    throw Object.assign(new Error(typeof body?.detail === 'string' && response.status !== 401 ? body.detail : message), { status: response.status });
  }
  return response.json();
}
