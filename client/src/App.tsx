import { useEffect, useReducer, useState } from 'react';
import { api } from './api';
import AdminPage from './AdminPage';
import CoursesPage from './CoursesPage';
import LoginPage from './LoginPage';
import RegisterPage from './RegisterPage';

type Page = 'home' | 'register' | 'login' | 'courses' | 'admin';

function pageFromPath(): Page {
  if (window.location.pathname === '/login') {
    return 'login';
  }

  if (window.location.pathname === '/register') {
    return 'register';
  }

  if (window.location.pathname === '/courses') return 'courses';
  if (['/admin', '/admin/'].includes(window.location.pathname)) return 'admin';
  return 'home';
}

function HomePage({ signedOut }: { signedOut: boolean }) {
  const [count, setCount] = useState(0);

  return (
    <main className="auth-card">
      <p className="eyebrow">Welcome</p>
      <h1>CPS420 Client</h1>

      <p className="auth-description">React frontend is running.</p>

      <button className="secondary-button" onClick={() => setCount(count + 1)}>Count: {count}</button>

      {signedOut && <p className="home-actions">
        <a className="primary-button" href="/register">Create an Account</a>
      </p>}
    </main>
  );
}

export default function App() {
  const page = pageFromPath();
  const [account, setAccount] = useState<{ is_admin: boolean } | null>();
  const [sessionVersion, refreshAccount] = useReducer((version: number) => version + 1, 0);

  useEffect(() => {
    if (!localStorage.getItem('access_token')) {
      setAccount(null);
      return;
    }
    const controller = new AbortController();
    api<{ is_admin: boolean }>('/auth/me', { signal: controller.signal })
      .then(user => { if (!controller.signal.aborted) setAccount(user); })
      .catch(() => { if (!controller.signal.aborted) setAccount(null); });
    return () => controller.abort();
  }, [sessionVersion]);

  return (
    <div className="app-shell">
      <nav className="site-nav" aria-label="Main navigation">
        <a href="/" aria-current={page === 'home' ? 'page' : undefined}>Home</a>
        <a href="/courses" aria-current={page === 'courses' ? 'page' : undefined}>Browse courses</a>
        {account?.is_admin && <a href="/admin" aria-current={page === 'admin' ? 'page' : undefined}>Admin dashboard</a>}
        {account === null && <a href="/login" aria-current={page === 'login' ? 'page' : undefined}>Log in</a>}
      </nav>
      {page === 'home' && <HomePage signedOut={account === null} />}
      {page === 'register' && <RegisterPage />}
      {page === 'login' && <LoginPage onLogin={refreshAccount} />}
      {page === 'courses' && <CoursesPage isAdmin={account?.is_admin === true} />}
      {page === 'admin' && <AdminPage onAccessDenied={refreshAccount} />}
    </div>
  );
}
