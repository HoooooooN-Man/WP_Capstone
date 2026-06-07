import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './app'),
      },
    },
    server: {
      port: 5173,
      proxy: {
        // 뉴스/게시판 API (8000) — /api/v1/news, /api/v1/board 는 ML 보다 먼저 매칭
        '/api/v1/news':  { target: env.VITE_API_AUTH || 'http://localhost:8000', changeOrigin: true },
        '/api/v1/board': { target: env.VITE_API_AUTH || 'http://localhost:8000', changeOrigin: true },
        // ML API (8001) — 나머지 /api/v1/*
        '/api/v1': {
          target: env.VITE_API_ML || 'http://localhost:8001',
          changeOrigin: true,
        },
        '/ws/prices': {
          target: (env.VITE_API_ML || 'http://localhost:8001').replace('http', 'ws'),
          ws: true,
          changeOrigin: true,
        },
        // Auth/Board API (8000) — /auth, /users, /events, /internal
        '/auth':     { target: env.VITE_API_AUTH || 'http://localhost:8000', changeOrigin: true },
        '/users':    { target: env.VITE_API_AUTH || 'http://localhost:8000', changeOrigin: true },
        '/events':   { target: env.VITE_API_AUTH || 'http://localhost:8000', changeOrigin: true },
        '/internal': { target: env.VITE_API_AUTH || 'http://localhost:8000', changeOrigin: true },
      },
    },
  };
});
