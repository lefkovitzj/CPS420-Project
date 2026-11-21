import { useState } from 'react';
import LoginPage from './LoginPage';
import RegisterPage from './RegisterPage';
import MfaSetupPage from './MfaSetupPage';

type Page = 'home' | 'register' | 'login';

type MfaChallenge = {
  challengeToken: string;
  provisioningUri?: string;
  purpose: 'register' | 'login';
};


function pageFromPath(): Page {
  if (window.location.pathname === '/login') {
    return 'login';
  }

  if (window.location.pathname === '/register') {
    return 'register';
  }

  return 'home';
}

export default function App() {
  const [count, setCount] = useState(0);
  const [mfa, setMfa] = useState<MfaChallenge | null>(null);
  const page = pageFromPath();

  if (mfa) {
    return (
      <MfaSetupPage
        challengeToken={mfa.challengeToken}
        provisioningUri={mfa.provisioningUri}
        purpose={mfa.purpose}
      />
    );
  }

  if (page === 'register') {
    return <RegisterPage onMfaRequired={(challenge) => setMfa({ ...challenge, purpose: 'register' })} />;

  }

  if (page === 'login') {
    return <LoginPage onMfaRequired={(challenge) => setMfa({ ...challenge, purpose: 'login' })} />;
  }


  return (
    <main className="auth-card">
      <p className="eyebrow">Welcome</p>
      <h1>CPS420 Client</h1>

      <p className="auth-description">React frontend is running.</p>

      <button className="secondary-button" onClick={() => setCount(count + 1)}>Count: {count}</button>

      <nav className="home-actions" aria-label="Account">
        <a
          className="primary-button"
          href="/register"
        >
          Create an Account
        </a>
        <a
          className="secondary-button"
          href="/login"
        >
          Log in
        </a>
      </nav>
      
    </main>
  );


}
