import { useEffect, useState } from 'react';
import { api } from './api';

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
  const [courses, setCourses] = useState<Course[]>([]);
  const [selected, setSelected] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api<string[]>('/courses/terms').then((values) => {
      if (!active) return;
      setTerms(values);
      setTerm(values[0] || '');
      if (!values.length) setLoading(false);
    }).catch((e: Error) => { if (active) { setError(e.message); setLoading(false); } });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!term) return;
    const controller = new AbortController();
    setError('');
    setLoading(true);
    setSelected('');
    setCourses([]);
    api<Course[]>(`/courses?${new URLSearchParams({ term, q: query })}`, { signal: controller.signal })
      .then((rows) => { if (!controller.signal.aborted) setCourses(rows); })
      .catch((e: Error) => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [term, query]);

  return (
    <main className="auth-card">
      <h1>Course catalog</h1>
      <div className="auth-form">
        {terms.length > 0 && <>
          <label className="form-field">Term
            <select value={term} onChange={e => setTerm(e.target.value)}>
              {terms.map(code => <option key={code} value={code}>{termLabel(code)}</option>)}
            </select>
          </label>
          <label className="form-field">Search courses
            <input type="search" placeholder="Subject, number, or title" value={query} onChange={e => setQuery(e.target.value)} />
          </label>
        </>}
        {loading && <p role="status">Loading courses…</p>}
        {error && <p role="alert">{error}</p>}
        {!loading && !error && !courses.length && <p>
          {terms.length ? 'No matching courses.' : 'No courses have been imported yet.'}
          {!terms.length && isAdmin && <> <a href="/admin#admin-imports">View import status</a></>}
        </p>}
        {courses.length > 0 && <label className="form-field">Select a course
          <select value={selected} onChange={e => setSelected(e.target.value)}>
            <option value="">Choose a course</option>
            {courses.map(c => <option key={c.id} value={c.id}>{c.subject} {c.course_number} — {c.title}</option>)}
          </select>
        </label>}
      </div>
    </main>
  );
}
