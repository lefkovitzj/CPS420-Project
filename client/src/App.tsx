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
  const [page, setPage] = useState<Page>(pageFromPath);

  if (page === 'register') {
    return <RegisterPage />;
  }

  if (page === 'login') {
    return <LoginPage />;
  }


  return (
    <main>
      <h1>CPS420 Client</h1>

      <p>React frontend is running.</p>

      <button onClick={() => setCount(count + 1)}>Count: {count}</button>

      <p>
        <a
          href="/register"
          onClick={(e) => {
            e.preventDefault();
            setPage('register');
          }}
        >
          Create an Account
        </a>
      </p>

      <p>
        <a
          href="/login"
          onClick={(e) => {
            e.preventDefault();
            setPage('login');
          }}
        >
          Log in
        </a>
      </p>
      
    </main>
  );


}
