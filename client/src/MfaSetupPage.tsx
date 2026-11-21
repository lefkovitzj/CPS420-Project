import { useState } from 'react';

type MfaSetupProps = {
  challengeToken: string;
  provisioningUri?: string;
  purpose: 'register' | 'login';
};

export default function MfaSetupPage({ challengeToken, provisioningUri, purpose }: MfaSetupProps) {
  const [otp, setOtp] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
  }

  

  return (
    <main className="auth-card">
      <p className="eyebrow">Study Group Matcher</p>
      <h1>Set up two-factor authentication</h1>
      <p className="auth-description">
        Add this account to your authenticator app, then enter the code it shows.
      </p>
      {provisioningUri && (
        <p className="form-message">{provisioningUri}</p>
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
      </form>
          </main>
  );
}
