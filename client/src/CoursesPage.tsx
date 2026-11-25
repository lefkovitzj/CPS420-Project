import { useEffect, useState } from 'react';
import { api, apiRequest, type ApiError } from './api';

type Course = { id: number; subject: string; course_number: string; title: string };

// Dayton's Banner term codes combine the calendar year and a two-digit session.
function termLabel(code: string): string {
  const year = code.slice(0, 4);
  switch (code.slice(4)) {
    case '06': return `Spring ${year} - Intersession`;
    case '10': return `Spring ${year}`;
    case '52': return `Summer ${year} - 2nd Session`;
    case '53': return `Summer ${year}`;
    case '80': return `Fall ${year}`;
    default: return code;
  }
}

export default function CoursesPage({ isAdmin }: { isAdmin: boolean }) {
  const [terms, setTerms] = useState<string[]>([]);
  const [term, setTerm] = useState('');
  const [query, setQuery] = useState('');
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [selected, setSelected] = useState('');
  const [error, setError] = useState<ApiError | null>(null);
  const [adding, setAdding] = useState(false);
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    api<string[]>('/courses/terms', { signal: controller.signal }).then(values => {
      if (controller.signal.aborted) return;
      setTerms(values);
      setTerm(values[0] || '');
      if (!values.length) setCourses([]);
    }).catch((e: ApiError) => { if (!controller.signal.aborted) setError(e); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!term) return;
    const controller = new AbortController();
    setError(null);
    setSuccess('');
    setSelected('');
    setCourses(null);
    api<Course[]>(`/courses?${new URLSearchParams({ term, q: query })}`, { signal: controller.signal })
      .then((rows) => { if (!controller.signal.aborted) setCourses(rows); })
      .catch((e: ApiError) => { if (!controller.signal.aborted) setError(e); });
    return () => controller.abort();
  }, [term, query]);

  async function addCourse() {
    const course = courses?.find(row => String(row.id) === selected);
    if (!course || adding) return;
    setAdding(true);
    setError(null);
    setSuccess('');
    try {
      await apiRequest('/profile/courses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject: course.subject, course_number: course.course_number }),
      });
      setSuccess(`${course.subject} ${course.course_number} added to your courses.`);
      setSelected('');
    } catch (error) {
      setError(error instanceof Error ? error : new Error('Could not add the course.'));
    } finally {
      setAdding(false);
    }
  }

  return (
    <main className="auth-card course-page">
      <h1>Course catalog</h1>
      <div className="auth-form">
        {terms.length > 0 && <>
          <label className="form-field">Term
            <select value={term} disabled={adding} onChange={e => setTerm(e.target.value)}>
              {terms.map(code => <option key={code} value={code}>{termLabel(code)}</option>)}
            </select>
          </label>
          <label className="form-field">Search courses
            <input type="search" placeholder="Subject, number, or title" value={query} disabled={adding} onChange={e => setQuery(e.target.value)} />
          </label>
        </>}
        {courses === null && !error && <p role="status">Loading courses…</p>}
        {error && <p role="alert">{error.message} {error.status === 401 && <a href="/login">Log in</a>}</p>}
        {courses?.length === 0 && <p role="status">
          {terms.length ? 'No matching courses.' : 'No courses have been imported yet.'}
          {!terms.length && isAdmin && <> <a href="/admin#admin-imports">View import status</a></>}
        </p>}
        {courses && courses.length > 0 && <>
          <label className="form-field">Select a course
            <select value={selected} disabled={adding} onChange={e => {
              setSelected(e.target.value);
              setError(null);
              setSuccess('');
            }}>
              <option value="">Choose a course</option>
              {courses.map(c => <option key={c.id} value={c.id}>{c.subject} {c.course_number} — {c.title}</option>)}
            </select>
          </label>
          <button type="button" className="primary-button" disabled={!selected || adding} onClick={addCourse}>
            {adding ? 'Adding…' : 'Add class'}
          </button>
        </>}
        {success && <p className="form-message form-message--success" role="status">{success}</p>}
      </div>
    </main>
  );
}
