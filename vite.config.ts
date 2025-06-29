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
    },
    optimizeDeps: {
      exclude: ['@tailwindcss/vite']
    }
  };
});
