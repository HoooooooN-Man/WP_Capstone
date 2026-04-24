import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      // '@'를 '/src' 폴더로 연결 (경로 깔끔하게 관리)
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        //rewrite: (path) => path.replace(/^\/api/, ''), api를 제거하고 보낼거면 주석제거
      },
    },
  },
})