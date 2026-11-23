import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { api } from './api';
import AdminPage from './AdminPage';

vi.mock('./api', () => ({ api: vi.fn() }));
afterEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
});

const admin = { id: 'first', email: 'admin@udayton.edu', is_admin: true };
const terms = [{ code: '202680', description: 'Fall 2026' }];

it('only offers role changes for other users and removes controls if access is revoked', async () => {
  vi.mocked(api).mockImplementation(async (path, options) => {
    if (path === '/admin/users') {
      return [admin, { id: 'second', email: 'second@udayton.edu', is_admin: true }];
    }
    if (options?.method === 'PATCH' && path === '/admin/users/second/role') {
      throw Object.assign(new Error('Administrator access required'), { status: 403 });
    }
    if (path === '/admin/imports/terms') return terms;
    if (path === '/admin/imports/latest?term_code=202680') return null;
    throw new Error(`Unexpected request: ${path}`);
  });
  const user = userEvent.setup();
  render(<AdminPage currentUserId={admin.id} />);
  const changeOther = await screen.findByRole('button', { name: 'Remove admin access from second@udayton.edu' });
  expect(screen.queryByRole('button', { name: `Remove admin access from ${admin.email}` })).not.toBeInTheDocument();
  await user.click(changeOther);
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
    if (path === '/admin/imports') throw Object.assign(new Error('Already running'), { status: 409 });
    if (path === '/admin/imports/latest?term_code=202680') {
      checks++;
      if (checks === 1) return null;
      return checks === 2 ? job : { ...job, status: 'succeeded', section_count: 25 };
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  const user = userEvent.setup();
  render(<AdminPage currentUserId={admin.id} />);
  const start = await screen.findByRole('button', { name: 'Start import' });
  await waitFor(() => expect(start).toBeEnabled());
  await user.click(start);
  expect(await screen.findByText('Importing Fall 2026…')).toBeVisible();
  expect(start).toBeDisabled();
  expect(await screen.findByText('Imported 25 sections for Fall 2026.', {}, { timeout: 5000 })).toBeVisible();
  expect(start).toBeEnabled();
});

it('resumes the selected term’s import after switching terms or reopening the dashboard', async () => {
  const spring = { code: '202710', description: 'Spring 2027' };
  const runningTerms = new Set<string>();
  vi.mocked(api).mockImplementation(async (path, options) => {
    if (path === '/admin/users') return [admin];
    if (path === '/admin/imports/terms') return [...terms, spring];
    if (path === '/admin/imports') {
      runningTerms.add(JSON.parse(String(options?.body)).term_code);
      return {};
    }
    const term = new URL(path, 'http://localhost').searchParams.get('term_code');
    if (term) return runningTerms.has(term) ? { status: 'running', term_code: term } : null;
    throw new Error(`Unexpected request: ${path}`);
  });
  const user = userEvent.setup();
  const firstVisit = render(<AdminPage currentUserId={admin.id} />);
  const start = await screen.findByRole('button', { name: 'Start import' });
  const select = screen.getByLabelText('Academic term');
  await waitFor(() => expect(start).toBeEnabled());
  await user.click(start);
  expect(await screen.findByText('Importing Fall 2026…')).toBeVisible();
  await user.selectOptions(select, spring.code);
  await waitFor(() => expect(start).toBeEnabled());
  await user.click(start);
  expect(await screen.findByText('Importing Spring 2027…')).toBeVisible();
  firstVisit.unmount();
  render(<AdminPage currentUserId={admin.id} />);
  expect(await screen.findByText('Importing Spring 2027…')).toBeVisible();
  await user.selectOptions(screen.getByLabelText('Academic term'), terms[0].code);
  expect(await screen.findByText('Importing Fall 2026…')).toBeVisible();
  expect(screen.getByRole('button', { name: 'Start import' })).toBeDisabled();
  expect(screen.queryByText('Importing Spring 2027…')).not.toBeInTheDocument();
});
