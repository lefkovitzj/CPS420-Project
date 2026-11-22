import { useState } from 'react';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSuccess('');
    setError('');

    try {
      // 201 - success, 
      // 422 - bad email/password
      // 409 - already registered
      const response = await fetch('/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
      });

      if (response.ok) {
        setSuccess('Account created! Redirecting to login...');
        
        //Timeout to display confirmation
        setTimeout(() => {
          try {
            window.location.href = '/login';
          } catch {
            // Redirect failures are not fatal, the success message is shown already.
          }
        }, 1500);

        return;
      }

      // 422 (bad email / password) or 409 (already registered)
      let message = 'Registration failed';
      try {
          const data = await response.json();

          if (typeof data.detail === 'string') {
              message = data.detail;
          } 
          else if (Array.isArray(data.detail) && data.detail[0]?.msg) {
              message = data.detail[0].msg.replace('Value error, ', '');
          }
      } catch {
        // Ignore bad error bodies and use the default message.
      }
      setError(message);
    }
    catch {
      setError('Could not reach the server.');
    }
  }             

  return (
    <main className="auth-card">
      <p className="eyebrow">CPS420</p>
      <h1>Create Account</h1>
      <p className="auth-description">Create your account to get started.</p>

      <form className="auth-form" onSubmit={handleSubmit}>
          <label className="form-field"> Email
            <input type="email"
                aria-describedby="registration-email-hint"
                value={email}
                onChange={(e) => setEmail(e.target.value)}/>
          </label>
          <p className="field-hint" id="registration-email-hint">Use your @udayton.edu email address.</p>

          <label className="form-field"> Password
            <input type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}/>
          </label>

        <button className="primary-button" type="submit">Create Account</button>

        {success && <p className="form-message form-message--success" role="status">{success}</p>}
        {error && <p className="form-message form-message--error" role="alert">{error}</p>}

      </form>

      <p className="auth-footer">
        Already have an account? <a href="/login">Log in</a>.
      </p>
    </main>
  );
}
