import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

import MfaSetupPage from './MfaSetupPage';

function mockResponse(status: number, body: unknown = {}): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

async function fillAndSubmit(user: ReturnType<typeof userEvent.setup>, otp: string) {
  await user.type(screen.getByLabelText('Authenticator code'), otp);
  await user.click(screen.getByRole('button', { name: 'Verify code' }));
}

const cases = [
  {
    name: 'Register verification creates the account',
    purpose: 'register' as const,
    status: 201,
    body: { id: '1', email: 'foo@udayton.edu', created_at: '2026-01-01T00:00:00Z' },
    otp: '123456',
    role: 'status',
    text: 'Account created! Redirecting to login...',
    token: undefined,
  },
  {
    name: 'Login verification stores the token',
    purpose: 'login' as const,
    status: 200,
    body: { access_token: 'abc123', token_type: 'bearer' },
    otp: '123456',
    role: 'status',
    text: 'Account logged in.',
    token: 'abc123',
  },
  {
    name: 'Login setup asks to sign in again',
    purpose: 'login' as const,
    status: 200,
    body: { status: 'mfa_configured' },
    otp: '123456',
    role: 'status',
    text: 'Authenticator set up. Please sign in again.',
    token: undefined,
  },
  {
    name: 'Wrong code shows an error',
    purpose: 'register' as const,
    status: 401,
    body: {},
    otp: '000000',
    role: 'alert',
    text: 'Incorrect or already used authenticator code.',
    token: undefined,
  },
];

describe('MfaSetupPage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it.each(cases)('$name', async ({ purpose, status, body, otp, role, text, token }) => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(mockResponse(status, body));
    const user = userEvent.setup();
    render(<MfaSetupPage challengeToken="test-token" purpose={purpose} />);

    await fillAndSubmit(user, otp);

    expect(await screen.findByRole(role)).toHaveTextContent(text);
    if (token) {
      expect(localStorage.getItem('access_token')).toBe(token);
    }
  });

  it('Shows an error when the server cannot be reached', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network error'));
    const user = userEvent.setup();
    render(<MfaSetupPage challengeToken="test-token" purpose="register" />);

    await fillAndSubmit(user, '123456');

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not reach the server.');
  });
});
