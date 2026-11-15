import { createRoot } from 'react-dom/client';

import App from './App';
// @ts-expect-error CSS is handled by the bundler.
import './styles.css';

createRoot(document.getElementById('root')!).render(<App />);
