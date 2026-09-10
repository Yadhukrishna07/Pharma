import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/batches': 'http://localhost:8000',
      '/returns': 'http://localhost:8000',
      '/disputes': 'http://localhost:8000',
      '/destruction': 'http://localhost:8000',
      '/certificates': 'http://localhost:8000',
      '/audit': 'http://localhost:8000',
      '/alerts': 'http://localhost:8000',
      '/dashboard': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
});
