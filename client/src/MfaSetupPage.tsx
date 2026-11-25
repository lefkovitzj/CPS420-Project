import { QRCodeSVG } from 'qrcode.react';
import { useState } from 'react';

type MfaSetupProps = {
  challengeToken: string;
  provisioningUri?: string;
  purpose: 'register' | 'login';
  onLogin?: () => void;
};

export default function MfaSetupPage({ challengeToken, provisioningUri, purpose, onLogin }: MfaSetupProps) {
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const isSetup = purpose === 'register' || Boolean(provisioningUri);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setSuccess('');

    const url = purpose === 'register'
      ? '/api/auth/register/verify'
      : '/api/auth/login/verify';

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ challenge_token: challengeToken, otp }),
      });

      if (response.ok) {
        const data = await response.json().catch(() => null);

        // Login setup case: no token, sign in again
        if (data?.status === 'mfa_configured') {
          setSuccess('Authenticator set up. Please sign in again.');
          setTimeout(() => { window.location.href = '/login'; }, 1500);
          return;
        }

        // Login verify case: token back
        if (data?.access_token) {
          localStorage.setItem('access_token', data.access_token);
          setSuccess('Account logged in.');
          onLogin?.();
          return;
        }

        // Register verify case: 201, account created
        setSuccess('Account created! Redirecting to login...');
        setTimeout(() => { window.location.href = '/login'; }, 1500);
        return;
      }

      if (response.status === 401) {
        setError('Incorrect or already used authenticator code.');
      } else {
        setError('Verification failed. Please try again.');
      }
    } 
    catch {
      setError('Could not reach the server.');
    }
  }

  return (
    <main className="auth-card">
      <p className="eyebrow">Study Group Matcher</p>
      <h1>{isSetup ? 'Set up two-factor authentication' : 'Enter your two-factor code'}</h1>
      <p className="auth-description">
        {isSetup
          ? 'Scan this QR code with your authenticator app, then enter the six-digit code it shows.'
          : 'Enter the code your authenticator app shows.'}
      </p>

      {provisioningUri && (
        <QRCodeSVG
          className="mfa-qr-code"
          value={provisioningUri}
          title="Authenticator setup QR code"
          size={200}
          marginSize={4}
        />
      )}

      <form className="auth-form" onSubmit={handleSubmit}>
        <label className="form-field">
          Authenticator code
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            placeholder="123456"
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
          />
        </label>
        <button type="submit" className="primary-button">
          Verify code
        </button>
          {success && <p className="form-message form-message--success" role="status">{success}</p>}
          {error && <p className="form-message form-message--error" role="alert">{error}</p>}
      </form>
          </main>
  );
}
