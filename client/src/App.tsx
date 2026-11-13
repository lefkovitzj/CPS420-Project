import { useState } from 'react';
import RegisterPage from './RegisterPage';

export default function App() {
  const [count, setCount] = useState(0);
  const [showRegister, setShowRegister] = useState(false);

  if (showRegister) {
    return <RegisterPage />;
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
            setShowRegister(true);
          }}
        >
          Create an Account
        </a>
      </p>
      
    </main>
  );


}
