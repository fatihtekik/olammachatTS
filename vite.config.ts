import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig(async () => {
  // Dynamically import the tailwindcss plugin (ESM module)
  const { default: tailwindcss } = await import('@tailwindcss/vite');

  return {
    plugins: [
      react(),
      tailwindcss(),
    ],
    server: {
      port: 3000,
      open: true,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
      watch: {
        ignored: [
          '**/backend/**',
          '**/*.db',
          '**/*.db-journal',
          '**/*.db-wal',
          '**/.env',
          '**/.env.*',
          '**/node_modules/**',
          '**/.git/**',
          '**/trigger_logs/**'
        ],
        usePolling: false
      },
      hmr: {
        overlay: false
      }
    },
    optimizeDeps: {
      exclude: ['@tailwindcss/vite']
    }
  };
});
