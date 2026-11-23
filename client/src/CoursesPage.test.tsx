import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import CoursesPage from './CoursesPage';
import { api } from './api';

vi.mock('./api', () => ({ api: vi.fn() }));

it('labels imported terms and searches with the selected Banner code', async () => {
  vi.mocked(api).mockImplementation(async path => {
    if (path === '/courses/terms') return ['202753', '202710', '202706', '202680', '201752', '201799'];
    return [];
  });
  const user = userEvent.setup();
  render(<CoursesPage isAdmin={false} />);

  const select = await screen.findByRole('combobox', { name: 'Term' });
  expect(screen.getAllByRole('option').map(option => option.textContent)).toEqual([
    'Summer 2027', 'Spring 2027', 'Spring 2027 - Intersession', 'Fall 2026', 'Summer 2017 - 2nd Session', '201799',
  ]);
  await user.selectOptions(select, 'Spring 2027 - Intersession');
  expect(api).toHaveBeenCalledWith('/courses?term=202706&q=', expect.anything());
});
