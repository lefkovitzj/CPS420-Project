import { useEffect, useReducer, useState } from 'react';
import { api, type ApiError } from './api';
import AdminPage from './AdminPage';
import CoursesPage from './CoursesPage';
import LoginPage from './LoginPage';
import RegisterPage from './RegisterPage';
import MfaSetupPage from './MfaSetupPage';
import UserCoursesPage from './UserCoursesPage';

type Page = 'home' | 'register' | 'login' | 'courses' | 'admin' | 'usercourses';
type Account = { id: string; is_admin: boolean };

type MfaChallenge = {
  challengeToken: string;
  provisioningUri?: string;
  purpose: 'register' | 'login';
};

function goHomeAfterLogin() {
  window.location.replace('/');
}

function pageFromPath(): Page {
  if (window.location.pathname === '/login') {
    return 'login';
  }

  if (window.location.pathname === '/register') {
    return 'register';
  }

  if (['/courses', '/addcourse'].includes(window.location.pathname)) return 'courses';
  if (window.location.pathname === '/usercourses') return 'usercourses';
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
  const [account, setAccount] = useState<Account | null>();
  const [sessionVersion, refreshAccount] = useReducer((version: number) => version + 1, 0);
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState('');
  const [mfa, setMfa] = useState<MfaChallenge | null>(null);
  const token = localStorage.getItem('access_token');
  // The course API can use the token while /auth/me loads the user's role.
  const hasSession = Boolean(token) && account !== null;

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    api<Account>('/auth/me', { signal: controller.signal })
      .then(user => { if (!controller.signal.aborted) setAccount(user); })
      .catch((error: ApiError) => {
        if (!controller.signal.aborted) setAccount(error.status === 401 ? null : undefined);
      });
    return () => controller.abort();
  }, [sessionVersion, token]);

  async function logOut() {
    if (!window.confirm('Are you sure you want to log out?')) return;
    setLoggingOut(true);
    setLogoutError('');
    try {
      const response = await fetch('/api/auth/logout', { method: 'POST' });
      if (!response.ok) throw new Error();
      localStorage.removeItem('access_token');
      window.location.replace('/login');
    } catch {
      setLogoutError('Could not log out. Please try again.');
      setLoggingOut(false);
    }
  }

  if (mfa) {
    return (
      <MfaSetupPage
        challengeToken={mfa.challengeToken}
        provisioningUri={mfa.provisioningUri}
        purpose={mfa.purpose}
        onLogin={goHomeAfterLogin}
      />
    );
  }

  return (
    <div className="app-shell">
      <nav className="site-nav" aria-label="Main navigation">
        <a href="/" aria-current={page === 'home' ? 'page' : undefined}>Home</a>
        <a href="/courses" aria-current={page === 'courses' ? 'page' : undefined}>Browse courses</a>
        {hasSession && <a href="/usercourses" aria-current={page === 'usercourses' ? 'page' : undefined}>My courses</a>}
        {hasSession && account?.is_admin && <a href="/admin" aria-current={page === 'admin' ? 'page' : undefined}>Admin dashboard</a>}
        {hasSession
          ? <button type="button" onClick={logOut} disabled={loggingOut}>Log out</button>
          : <a href="/login" aria-current={page === 'login' ? 'page' : undefined}>Log in</a>}
      </nav>
      {logoutError && <p role="alert">{logoutError}</p>}
      {page === 'home' && <HomePage signedOut={!hasSession} />}
      {page === 'register' && <RegisterPage onMfaRequired={(challenge) => setMfa({ ...challenge, purpose: 'register' })} />}
      {(page === 'courses' || page === 'usercourses') && !hasSession && (
        <main className="auth-card">
          <h1>{page === 'courses' ? 'Course catalog' : 'My courses'}</h1>
          <p><a href="/login">Log in</a> to browse and manage your courses.</p>
        </main>
      )}
      {page === 'courses' && hasSession && <CoursesPage isAdmin={account?.is_admin === true} />}
      {page === 'usercourses' && hasSession && <UserCoursesPage />}
      {page === 'login' && (
        <LoginPage
          onLogin={goHomeAfterLogin}
          onMfaRequired={(challenge) => setMfa({ ...challenge, purpose: 'login' })}
        />
      )}
      {page === 'admin' && <AdminPage currentUserId={account?.id} onAccessDenied={refreshAccount} />}
    </div>
  );
}
