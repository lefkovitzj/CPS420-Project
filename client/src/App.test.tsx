import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from './App';

describe('App', () => {
  afterEach(() => {
    window.history.replaceState(null, '', '/');
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('renders the heading and status message', () => {
    render(<App />);

    expect(screen.getByRole('heading', { name: 'CPS420 Client' })).toBeInTheDocument();
    expect(screen.getByText('React frontend is running.')).toBeInTheDocument();
  });

  it('increments the count when the button is clicked', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: 'Count: 0' }));

    expect(screen.getByRole('button', { name: 'Count: 1' })).toBeInTheDocument();
  });

  it.each([true, false])('restores the empty catalog navigation for an existing session (admin: %s)', async isAdmin => {
    window.history.replaceState(null, '', '/courses');
    localStorage.setItem('access_token', 'existing-token');
    vi.spyOn(globalThis, 'fetch').mockImplementation(async path => {
      if (path === '/api/auth/me') return Response.json({ is_admin: isAdmin });
      if (path === '/api/courses/terms') return Response.json([]);
      throw new Error(`Unexpected request: ${path}`);
    });
    render(<App />);

    expect(await screen.findByText('No courses have been imported yet.')).toBeVisible();
    const nav = within(screen.getByRole('navigation', { name: 'Main navigation' }));
    expect(nav.queryByRole('link', { name: 'Log in' })).not.toBeInTheDocument();
    if (isAdmin) {
      expect(nav.getByRole('link', { name: 'Admin dashboard' })).toHaveAttribute('href', '/admin');
      expect(screen.getByRole('link', { name: 'View import status' })).toHaveAttribute('href', '/admin#admin-imports');
    } else {
      expect(nav.queryByRole('link', { name: 'Admin dashboard' })).not.toBeInTheDocument();
      expect(screen.queryByRole('link', { name: 'View import status' })).not.toBeInTheDocument();
    }
  });
});
