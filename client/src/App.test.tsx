import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import App from './App';

describe('App', () => {
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
});
