import { useState } from 'react';
import LoginPage from './LoginPage';
import RegisterPage from './RegisterPage';

type Page = 'home' | 'register' | 'login';

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
  const page = pageFromPath();

  if (page === 'register') {
    return <RegisterPage />;
  }

  if (page === 'login') {
    return <LoginPage />;
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
