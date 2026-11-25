import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import CoursesPage from './CoursesPage';

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

it('labels imported terms and searches with the selected Banner code', async () => {
  const request = vi.spyOn(globalThis, 'fetch').mockImplementation(async path => {
    if (path === '/api/courses/terms') return Response.json(['202753', '202710', '202706', '202680', '201752', '201799']);
    return Response.json([]);
  });
  const user = userEvent.setup();
  render(<CoursesPage isAdmin={false} />);

  const select = await screen.findByRole('combobox', { name: 'Term' });
  expect(screen.getAllByRole('option').map(option => option.textContent)).toEqual([
    'Summer 2027', 'Spring 2027', 'Spring 2027 - Intersession', 'Fall 2026', 'Summer 2017 - 2nd Session', '201799',
  ]);
  await user.selectOptions(select, 'Spring 2027 - Intersession');
  expect(request).toHaveBeenCalledWith('/api/courses?term=202706&q=', expect.anything());
});

const course = { id: 42, subject: 'BIO', course_number: '151', title: 'Biology' };

function serveCatalog(addResponse: Response) {
  localStorage.setItem('access_token', 'student-token');
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async path => {
    if (path === '/api/courses/terms') return Response.json(['202710']);
    if (path === '/api/profile/courses') return addResponse;
    const query = new URL(String(path), window.location.origin).searchParams.get('q');
    return Response.json(query === '' || query === 'BIO' ? [course] : []);
  });
}

async function searchAndAdd() {
  const user = userEvent.setup();
  render(<CoursesPage isAdmin={false} />);
  await user.type(await screen.findByRole('searchbox'), 'BIO');
  await user.selectOptions(await screen.findByRole('combobox', { name: 'Select a course' }), 'BIO 151 — Biology');
  await user.click(screen.getByRole('button', { name: 'Add class' }));
}

it('adds the catalog selection to the signed-in user’s list', async () => {
  const request = serveCatalog(Response.json({ id: 1, course_id: course.id }, { status: 201 }));
  await searchAndAdd();

  expect(await screen.findByText('BIO 151 added to your courses.')).toBeVisible();
  expect(request).toHaveBeenCalledWith('/api/courses?term=202710&q=BIO', expect.anything());
  const options = request.mock.calls.find(([path]) => path === '/api/profile/courses')?.[1];
  expect(options?.method).toBe('POST');
  expect(new Headers(options?.headers).get('Authorization')).toBe('Bearer student-token');
  expect(JSON.parse(String(options?.body))).toEqual({ subject: 'BIO', course_number: '151' });
});

it.each([
  [401, 'Not authenticated', 'Please log in again.'],
  [404, 'Course not found.', 'Course not found.'],
  [409, 'Course is already in your profile.', 'Course is already in your profile.'],
] as const)('shows the appropriate message for a %i add response', async (status, detail, message) => {
  serveCatalog(Response.json({ detail }, { status }));
  await searchAndAdd();
  expect(await screen.findByRole('alert')).toHaveTextContent(message);
});

it('explains when a search finds no matches and offers no add action', async () => {
  serveCatalog(Response.json({}));
  const user = userEvent.setup();
  render(<CoursesPage isAdmin={false} />);
  expect(await screen.findByRole('option', { name: 'BIO 151 — Biology' })).toBeInTheDocument();
  await user.type(await screen.findByRole('searchbox'), 'CPS 999');
  expect(await screen.findByText('No matching courses.')).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Add class' })).not.toBeInTheDocument();
});
