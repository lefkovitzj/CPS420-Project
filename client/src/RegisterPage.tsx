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
      const response = await fetch('http://127.0.0.1:5000/auth/register', {
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
      }
      setError(message);
    }
    catch {
      setError('Could not reach the server.');
    }
  }             

  return (
    <main>

      <h1>Create Account</h1>

      <form onSubmit={handleSubmit}>
          <label> Email
            <input type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}/>
          </label>

          <label> Password
            <input type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}/>
          </label>

        <button type="submit">Create Account</button>

        {success && <p role="status">{success}</p>}
        {error && <p role="alert">{error}</p>}

      </form>

    </main>
  );
}