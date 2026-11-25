import { useEffect, useState } from 'react';
import { api, apiRequest, type ApiError } from './api';

type SavedCourse = { id: number; subject: string; course_number: string };

export default function UserCoursesPage() {
  const [courses, setCourses] = useState<SavedCourse[] | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [removing, setRemoving] = useState<number | null>(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    api<SavedCourse[]>('/profile/courses', { signal: controller.signal })
      .then(rows => { if (!controller.signal.aborted) setCourses(rows); })
      .catch(e => { if (!controller.signal.aborted) setError(e); });
    return () => controller.abort();
  }, []);

  async function removeCourse({ id, subject, course_number }: SavedCourse) {
    setRemoving(id);
    setError(null);
    setMessage('');
    try {
      await apiRequest('/profile/courses', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject, course_number }),
      });
    } catch (e) {
      const failure: ApiError = e instanceof Error ? e : new Error('Could not remove the course.');
      if (failure.status !== 404) {
        setError(failure);
        return;
      }
    } finally {
      setRemoving(null);
    }
    setCourses(rows => rows && rows.filter(course => course.id !== id));
    setMessage(`${subject} ${course_number} is no longer in your courses.`);
  }

  return (
    <main className="auth-card course-page">
      <h1>My courses</h1>
      {courses === null && !error && <p role="status">Loading your courses…</p>}
      {error && <p role="alert" className="form-message form-message--error">
        {error.message} {error.status === 401 && <a href="/login">Log in</a>}
      </p>}
      {message && <p role="status">{message}</p>}
      {courses?.length === 0 && <p>Your course list is empty. <a href="/courses">Browse courses</a></p>}
      {courses && courses.length > 0 && <ul>
        {courses.map(course => <li key={course.id}>
          {course.subject} {course.course_number}
          <button type="button" className="secondary-button" disabled={removing !== null}
            aria-label={`Remove ${course.subject} ${course.course_number}`}
            onClick={() => removeCourse(course)}>
            {removing === course.id ? 'Removing…' : 'Remove'}
          </button>
        </li>)}
      </ul>}
    </main>
  );
}
