import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { api } from './api';
import AdminPage from './AdminPage';

vi.mock('./api', () => ({ api: vi.fn() }));
afterEach(() => vi.resetAllMocks());

const admin = { id: 'first', email: 'admin@udayton.edu', is_admin: true };
const terms = [{ code: '202680', description: 'Fall 2026' }];

it('removes dashboard controls when a role change revokes the current admin’s access', async () => {
  let demoted = false;
  vi.mocked(api).mockImplementation(async (path, options) => {
    if (path === '/admin/users') {
      if (demoted) throw Object.assign(new Error('Administrator access required'), { status: 403 });
      return [admin];
    }
    if (options?.method === 'PATCH' && path === '/admin/users/first/role') {
      demoted = true;
      return { ...admin, is_admin: false };
    }
    if (path === '/admin/imports/terms') return terms;
    if (path === '/admin/imports/latest') return null;
    throw new Error(`Unexpected request: ${path}`);
  });
  const user = userEvent.setup();
  render(<AdminPage />);
  await user.click(await screen.findByRole('button', { name: /Remove admin access from/ }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Administrator access required');
  expect(screen.queryByText(admin.email)).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Start import' })).not.toBeInTheDocument();
});

it('follows the existing import to completion when another admin starts the term first', async () => {
  const job = { id: 7, status: 'running', term_code: '202680', finished_at: null };
  let checks = 0;
  vi.mocked(api).mockImplementation(async path => {
    if (path === '/admin/users') return [admin];
    if (path === '/admin/imports/terms') return terms;
    if (path === '/admin/imports/latest') return null;
    if (path === '/admin/imports') throw Object.assign(new Error('Already running'), { status: 409 });
    if (path === '/admin/imports/latest?term_code=202680') return job;
    if (path === '/admin/imports/7') {
      checks++;
      return checks === 1 ? job : { ...job, status: 'succeeded', section_count: 25 };
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  const user = userEvent.setup();
  render(<AdminPage />);
  const start = await screen.findByRole('button', { name: 'Start import' });
  await waitFor(() => expect(start).toBeEnabled());
  await user.click(start);
  expect(await screen.findByText('Importing Fall 2026…')).toBeVisible();
  expect(start).toBeDisabled();
  expect(await screen.findByText('Imported 25 sections for Fall 2026.', {}, { timeout: 5000 })).toBeVisible();
  expect(start).toBeEnabled();
});
