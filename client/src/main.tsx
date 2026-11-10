import { useState } from 'react';
import { createRoot } from 'react-dom/client';

function App() {
  const [count, setCount] = useState(0);

  return (
    <main>
      <h1>CPS420 Client</h1>
      <p>React frontend is running.</p>
      <button onClick={() => setCount(count + 1)}>Count: {count}</button>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(<App />);
