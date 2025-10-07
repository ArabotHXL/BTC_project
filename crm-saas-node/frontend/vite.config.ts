import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  base: '/crm/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@crm-saas/shared': path.resolve(__dirname, '../shared/types'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5001,
    allowedHosts: ['.repl.co', '.replit.dev'],
    hmr: {
      clientPort: 443,
    },
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
      },
    },
  },
});
