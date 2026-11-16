import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, afterEach } from 'vitest';

import RegisterPage from './RegisterPage';

const invalidCases = [
  { name: 'a non-UD email',
    email: 'foo@gmail.com',
    password: 'something123',
    error: 'Email must be a valid @udayton.edu address',
  },
  { name: 'a too small (< three character) password',
    email: 'foo1@udayton.edu',
    password: '12',
    error: 'Password must be 3 to 128 characters',
  },
  { name: 'a too large (> 128 character) password',
    email: 'foo2@udayton.edu',
    password: 'a'.repeat(129),
    error: 'Password must be 3 to 128 characters',
  },
];

const validCases = [
  { name: 'a three character password',
    email: 'foo@udayton.edu', 
    password: '123' 
  },

  { name: 'a 128 character password',
    email: 'foo2@udayton.edu', 
    password: 'a'.repeat(128) 
  },

  { name: 'a regular login',
    email: 'foo3@udayton.edu', 
    password: 'password123' 
  },
];

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
  await user.click(screen.getByRole('button', { name: 'Create Account' }));
}

describe('RegisterPage', () => {

  afterEach(() => {
      vi.restoreAllMocks();
  });

  it('renders the heading and status message', () => {
    render(<RegisterPage />);

    expect(screen.getByRole('heading', { name: 'Create Account' })).toBeInTheDocument();
    expect(screen.getByText('Email')).toBeInTheDocument();
    expect(screen.getByText('Password')).toBeInTheDocument();
  });

  it.each(invalidCases)('shows an error for $name', async ({ email, password, error }) => {
    // The server validates the input and returns 422 with a pydantic detail message.
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      mockResponse(422, { detail: [{ msg: `Value error, ${error}` }] })
    );

    const user = userEvent.setup();
    render(<RegisterPage />);

    await fillAndSubmit(user, email, password);
    expect(await screen.findByText(error)).toBeInTheDocument();
  });

  it.each(validCases)('succeeds with $name', async ({ email, password }) => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      mockResponse(201, {
        id: '00000000-0000-0000-0000-000000000000',
        email,
        created_at: '2026-01-01T00:00:00Z',
      })
    );

    const user = userEvent.setup();
    render(<RegisterPage />);

    await fillAndSubmit(user, email, password);

    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith(
            '/api/auth/register',
            expect.objectContaining({
                method: 'POST',
                body: JSON.stringify({ email, password }),
            })
        );
    });
    
  });

  it('shows an error when the server cannot be reached', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network error'));

    const user = userEvent.setup();
    render(<RegisterPage />);

    await fillAndSubmit(user, 'foo@udayton.edu', 'password123');

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not reach the server.');
  });

});
