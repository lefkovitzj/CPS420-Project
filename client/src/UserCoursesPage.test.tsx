import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import UserCoursesPage from './UserCoursesPage';

const course = { id: 1, subject: 'CPS', course_number: '420' };

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

it.each([204, 404])('loads once and removes the saved row when DELETE returns %i', async status => {
  localStorage.setItem('access_token', 'test-token');
  const fetch = vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(Response.json([course]))
    .mockResolvedValueOnce(new Response(null, { status }));
  const user = userEvent.setup();
  render(<UserCoursesPage />);

  const remove = await screen.findByRole('button', { name: 'Remove CPS 420' });
  expect(fetch).toHaveBeenCalledTimes(1);
  await user.click(remove);
  expect(await screen.findByRole('status')).toHaveTextContent('CPS 420 is no longer in your courses.');
  expect(screen.queryByRole('button', { name: 'Remove CPS 420' })).toBeNull();
  expect(screen.getByRole('link', { name: 'Browse courses' })).toHaveAttribute('href', '/courses');

  expect(fetch).toHaveBeenCalledTimes(2);
  for (const [url, options] of fetch.mock.calls) {
    expect(url).toBe('/api/profile/courses');
    expect(new Headers(options?.headers).get('Authorization')).toBe('Bearer test-token');
  }
  expect(fetch.mock.calls[1][1]).toMatchObject({
    method: 'DELETE',
    body: JSON.stringify({ subject: 'CPS', course_number: '420' }),
  });
});

it('keeps the saved course and offers sign-in if the session expires before removal', async () => {
  vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(Response.json([course]))
    .mockResolvedValueOnce(new Response(null, { status: 401 }));
  const user = userEvent.setup();
  render(<UserCoursesPage />);

  await user.click(await screen.findByRole('button', { name: 'Remove CPS 420' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Please log in again.');
  expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/login');
  expect(screen.getByRole('button', { name: 'Remove CPS 420' })).toBeEnabled();
});
