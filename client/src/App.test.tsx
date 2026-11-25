import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from './App';

describe('App', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.replaceState(null, '', '/');
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('renders the heading and status message', () => {
    render(<App />);

    expect(screen.getByRole('heading', { name: 'CPS420 Client' })).toBeInTheDocument();
    expect(screen.getByText('React frontend is running.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Log out' })).not.toBeInTheDocument();
  });

  it('increments the count when the button is clicked', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: 'Count: 0' }));

    expect(screen.getByRole('button', { name: 'Count: 1' })).toBeInTheDocument();
  });

  it.each(['trusted browser', 'authenticator code'])('goes home after a successful login with a %s', async method => {
    window.history.replaceState(null, '', '/login');
    const replace = vi.fn();
    vi.stubGlobal('location', { ...window.location, replace });
    const request = vi.spyOn(globalThis, 'fetch');
    if (method === 'authenticator code') {
      request.mockResolvedValueOnce(Response.json({ challenge_token: 'challenge' }, { status: 202 }));
    }
    request.mockResolvedValueOnce(Response.json({ access_token: 'signed-in-token' }));
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText('Email'), 'student@udayton.edu');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.click(screen.getByRole('button', { name: 'Log in' }));
    if (method === 'authenticator code') {
      expect(replace).not.toHaveBeenCalled();
      await user.type(screen.getByLabelText('Authenticator code'), '123456');
      await user.click(screen.getByRole('button', { name: 'Verify code' }));
    }

    expect(localStorage.getItem('access_token')).toBe('signed-in-token');
    expect(replace).toHaveBeenCalledWith('/');
  });

  it('only logs out after the user confirms', async () => {
    window.history.replaceState(null, '', '/login');
    localStorage.setItem('access_token', 'existing-token');
    const request = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(Response.json({ id: 'current-user', is_admin: false }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    const confirm = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true);
    const user = userEvent.setup();
    render(<App />);
    const logOut = await screen.findByRole('button', { name: 'Log out' });
    request.mockClear();

    await user.click(logOut);
    expect(confirm).toHaveBeenCalledTimes(1);
    expect(request).not.toHaveBeenCalled();
    expect(localStorage.getItem('access_token')).toBe('existing-token');

    await user.click(logOut);
    expect(confirm).toHaveBeenCalledTimes(2);
    expect(request).toHaveBeenCalledWith('/api/auth/logout', { method: 'POST' });
    expect(localStorage.getItem('access_token')).toBeNull();
  });

  it('shows saved courses when account details are temporarily unavailable', async () => {
    window.history.replaceState(null, '', '/usercourses');
    localStorage.setItem('access_token', 'student-token');
    vi.spyOn(globalThis, 'fetch').mockImplementation(async path => {
      if (path === '/api/auth/me') return new Response(null, { status: 503 });
      if (path === '/api/profile/courses') return Response.json([{ id: 1, subject: 'CPS', course_number: '420' }]);
      throw new Error(`Unexpected request: ${path}`);
    });
    render(<App />);

    expect(await screen.findByRole('button', { name: 'Remove CPS 420' })).toBeVisible();
    expect(screen.queryByRole('link', { name: 'Log in' })).not.toBeInTheDocument();
  });

  it.each([true, false])('restores the empty catalog navigation for an existing session (admin: %s)', async isAdmin => {
    window.history.replaceState(null, '', '/courses');
    localStorage.setItem('access_token', 'existing-token');
    vi.spyOn(globalThis, 'fetch').mockImplementation(async path => {
      if (path === '/api/auth/me') return Response.json({ id: 'current-user', is_admin: isAdmin });
      if (path === '/api/courses/terms') return Response.json([]);
      throw new Error(`Unexpected request: ${path}`);
    });
    render(<App />);

    expect(await screen.findByText('No courses have been imported yet.')).toBeVisible();
    const nav = within(screen.getByRole('navigation', { name: 'Main navigation' }));
    expect(nav.queryByRole('link', { name: 'Log in' })).not.toBeInTheDocument();
    expect(nav.getByRole('button', { name: 'Log out' })).toBeEnabled();
    if (isAdmin) {
      expect(nav.getByRole('link', { name: 'Admin dashboard' })).toHaveAttribute('href', '/admin');
      expect(screen.getByRole('link', { name: 'View import status' })).toHaveAttribute('href', '/admin#admin-imports');
    } else {
      expect(nav.queryByRole('link', { name: 'Admin dashboard' })).not.toBeInTheDocument();
      expect(screen.queryByRole('link', { name: 'View import status' })).not.toBeInTheDocument();
    }
  });
});
