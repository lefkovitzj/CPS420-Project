import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import AddCoursePage from './AddCoursePage'

function mockResponse(status: number, body: unknown = {}): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

async function fillAndSubmit(
  user: ReturnType<typeof userEvent.setup>,
  subject: string,
  course_number: string
) {
  await user.type(screen.getByLabelText('Subject'), subject);
  await user.type(screen.getByLabelText('Course Number'), course_number);
  await user.click(screen.getByRole('button', { name: 'Add Course' }));
}

describe('AddCoursePage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('it adds a course to the user profile', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
     
    const user = userEvent.setup();
    render(<AddCoursePage />);

    await fillAndSubmit(user, 'BIO', '151');

    expect(await screen.findByRole('status')).toHaveTextContent('Course added!');
    
   
  });

  it('shows an error for invalid course id', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(mockResponse(401));
    const user = userEvent.setup();
    render(<AddCoursePage />);
    //wrong course id
    await fillAndSubmit(user, 'BIO', '100000');

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid Course ID');
  });
it('shows an error for invalid subject',async()=>{
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(mockResponse(401));
    const user = userEvent.setup();
    render(<AddCoursePage />);
    //wrong course id
    await fillAndSubmit(user, 'BOBBY', '151');

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid Course ID');
})
  it('shows an error when the server cannot be reached', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network error'));
    const user = userEvent.setup();
    render(<AddCoursePage />);

    await fillAndSubmit(user, 'BIO', '151');

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not reach the server.');
  });
});
