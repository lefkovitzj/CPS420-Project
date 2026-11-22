import { useCallback, useEffect, useState } from 'react';
import { api } from './api';
import ImportPanel from './ImportPanel';
import './admin.css';

type Account = { id: string; email: string; is_admin: boolean };

export default function AdminPage({ onAccessDenied }: { onAccessDenied?: () => void }) {
  const [users, setUsers] = useState<Account[] | null>(null);
  const [denied, setDenied] = useState('');
  const [error, setError] = useState('');
  const [updated, setUpdated] = useState('');
  const [saving, setSaving] = useState('');
  const [attempt, setAttempt] = useState(0);

  const checkAccess = useCallback((failure: Error & { status?: number }) => {
    if (failure.status !== 401 && failure.status !== 403) return false;
    setUsers(null);
    setDenied(failure.message);
    onAccessDenied?.();
    return true;
  }, [onAccessDenied]);

  useEffect(() => {
    const controller = new AbortController();
    setError('');
    api<Account[]>('/admin/users', { signal: controller.signal })
      .then(rows => { if (!controller.signal.aborted) setUsers(rows); })
      .catch(e => { if (!controller.signal.aborted && !checkAccess(e)) setError(e.message); });
    return () => controller.abort();
  }, [attempt, checkAccess]);

  async function changeRole(user: Account) {
    setSaving(user.id);
    setUpdated('');
    setError('');
    try {
      await api<Account>(`/admin/users/${user.id}/role`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_admin: !user.is_admin }),
      });
      // Reauthorize before showing the list again, including after changing our own role.
      setUsers(await api<Account[]>('/admin/users'));
      setUpdated(`Role updated for ${user.email}.`);
    } catch (e) {
      const failure = e as Error;
      if (!checkAccess(failure)) setError(failure.message);
    } finally {
      setSaving('');
    }
  }

  return (
    <main className="auth-card admin-dashboard">
      <h1>Admin dashboard</h1>
      {denied ? <p role="alert">{denied} <a href="/login">Log in</a></p> : <>
        <section aria-labelledby="admin-users">
          <h2 id="admin-users">User management</h2>
          {error && <div role="alert" className="form-message form-message--error">
            {error} <button type="button" onClick={() => setAttempt(a => a + 1)}>Refresh users</button>
          </div>}
          {updated && <p role="status">{updated}</p>}
          {!users && !error && <p role="status">Loading users…</p>}
          {users && <ul className="admin-users">
            {users.map(user => <li key={user.id}>
              <div><strong>{user.email}</strong><span>{user.is_admin ? 'Administrator' : 'Student'}</span></div>
              <button type="button" disabled={Boolean(saving)} className="secondary-button"
                aria-label={`${user.is_admin ? 'Remove admin access from' : 'Give admin access to'} ${user.email}`}
                onClick={() => changeRole(user)}>
                {saving === user.id ? 'Saving…' : user.is_admin ? 'Remove admin access' : 'Make admin'}
              </button>
            </li>)}
          </ul>}
        </section>
        {users && <ImportPanel checkAccess={checkAccess} />}
      </>}
    </main>
  );
}
