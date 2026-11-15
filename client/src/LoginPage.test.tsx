import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

import LoginPage from './LoginPage';

function mockResponse(status: number, body: unknown = {}): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

async function fillAndSubmit(
  user: ReturnType<typeof userEvent.setup>,
  email: string,
  password: string
) {
  await user.type(screen.getByLabelText('Email'), email);
  await user.type(screen.getByLabelText('Password'), password);
  await user.click(screen.getByRole('button', { name: 'Log in' }));
}

describe('LoginPage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sends credentials as form data and stores the token', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(mockResponse(200, { access_token: 'abc123', token_type: 'bearer' }));
    const user = userEvent.setup();
    render(<LoginPage />);

    await fillAndSubmit(user, 'foo@udayton.edu', 'password123');

    expect(await screen.findByRole('status')).toHaveTextContent('Account logged in.');
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:5000/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        username: 'foo@udayton.edu',
        password: 'password123',
      }).toString(),
    });
    expect(localStorage.getItem('access_token')).toBe('abc123');
  });

  it('shows an error for incorrect credentials', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(mockResponse(401));
    const user = userEvent.setup();
    render(<LoginPage />);

    await fillAndSubmit(user, 'foo@udayton.edu', 'wrongpassword');

    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password.');
  });

  it('shows an error when the server cannot be reached', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network error'));
    const user = userEvent.setup();
    render(<LoginPage />);

    await fillAndSubmit(user, 'foo@udayton.edu', 'password123');

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not reach the server.');
  });
});
