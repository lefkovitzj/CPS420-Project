// Direct navigation carries the dashboard cookie. Ask the API for the same
// authorization decision that nginx enforces when serving the production build.
import type { Connect, Plugin } from 'vite';

export function adminGate(backend: string): Plugin {
  const guard: Connect.NextHandleFunction = async (request, response, next) => {
    const path = request.url?.split('?')[0];
    if (path !== '/admin' && path !== '/admin/') return next();
    response.setHeader('Cache-Control', 'no-store');
    try {
      const check = await fetch(`${backend}/admin/access`, {
        headers: { cookie: request.headers.cookie || '' },
        signal: AbortSignal.timeout(5000),
      });
      if (check.status === 204) return next();
      response.statusCode = [401, 403].includes(check.status) ? check.status : 503;
    } catch {
      response.statusCode = 503;
    }
    const messages: Record<number, string> = { 401: 'Please log in to view the dashboard.', 403: 'Administrator access required.' };
    response.end(messages[response.statusCode] || 'Dashboard unavailable.');
  };
  return {
    name: 'admin-page-access',
    configureServer(server) { server.middlewares.use(guard); },
    configurePreviewServer(server) { server.middlewares.use(guard); },
  };
}
