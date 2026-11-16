import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
import { loadEnv } from 'vite';
import { defineConfig } from 'vitest/config';

export default defineConfig(({ mode }) => {
  // Read the root .env only for the server-side proxy; nothing is exposed to React.
  const env = loadEnv(mode, fileURLToPath(new URL('..', import.meta.url)), ['HOST', 'BACKEND_PORT']);
  const bindHost = env.HOST || '127.0.0.1';
  // Wildcard bind addresses must become a concrete address for the connection.
  const host = ['0.0.0.0', '::', '[::]'].includes(bindHost) ? '127.0.0.1' : bindHost;
  const hostname = host.includes(':') && !host.startsWith('[') ? `[${host}]` : host;

  return {
    plugins: [react()],
    server: {
      // Vite preview also uses these proxy rules.
      proxy: {
        '/api/': {
          target: `http://${hostname}:${env.BACKEND_PORT || '5000'}`,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\//, '/'),
        },
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'json', 'json-summary', 'lcov'],
        include: ['src/**/*.{ts,tsx}'],
        exclude: ['src/main.tsx', 'src/test/**', 'src/**/*.test.{ts,tsx}'],
      },
    },
  };
});
