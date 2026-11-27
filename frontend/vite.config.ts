import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendDir = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  root: frontendDir,
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/etl': 'http://127.0.0.1:8000' },
  },
  build: {
    outDir: resolve(frontendDir, '../app/static/react'),
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        entryFileNames: 'app.js',
        chunkFileNames: 'chunks/[name].js',
        assetFileNames: 'app[extname]',
      },
    },
  },
});
