// login page for app; code based off code from registration page

import { useState } from 'react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setSuccess('');
    setError('');

    try {
      // The server uses OAuth2PasswordRequestForm, so credentials must be
      // sent as form data with the email in the "username" field.
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: email, password }).toString(),
      });

      if (response.ok) {
        const data = await response.json().catch(() => null);
        if (data?.access_token) {
          localStorage.setItem('access_token', data.access_token);
        }
        setSuccess('Account logged in.');
        return;
      }

      // error 401: wrong password/wrong login
      if (response.status === 401) {
        setError('Incorrect email or password.');
      } else {
        setError('Login failed. Please try again.');
      }
    } catch {
      setError('Could not reach the server.');
    }
  }

  return (
    <main className="auth-card">
      <p className="eyebrow">CPS420</p>
      <h1>Login</h1>
      <p className="auth-description">Welcome back. Sign in to continue.</p>

      <form className="auth-form" onSubmit={handleLogin}>
        <label className="form-field"> Email
          <input
            type="email"
            placeholder="Email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>

        <label className="form-field"> Password
          <input
            type="password"
            placeholder="Password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>

        <button className="primary-button" type="submit">Log in</button>

        {success && <p className="form-message form-message--success" role="status">{success}</p>}
        {error && <p className="form-message form-message--error" role="alert">{error}</p>}
      </form>

      <p className="auth-footer">
        If you do not have an account, <a href="/register">please register</a>.
      </p>
    </main>
  );
}
