import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico'],
      manifest: {
        name: 'WP_Capstone - AI 주식 분석',
        short_name: 'WP Capstone',
        description: 'ML 기반 주식 추천 및 분석 서비스',
        theme_color: '#161C40',
        background_color: '#0F1117',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        icons: [
          { src: '/favicon.ico', sizes: '64x64', type: 'image/x-icon' },
          { src: '/pwa-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/pwa-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
      },
      workbox: {
        // static: Cache First, API: Network First
        runtimeCaching: [
          {
            urlPattern: /^https?:\/\/.*\/stocks\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-stocks',
              networkTimeoutSeconds: 5,
              expiration: { maxEntries: 50, maxAgeSeconds: 60 },
            },
          },
          {
            urlPattern: /^https?:\/\/.*\/(versions|sectors)/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'api-static',
              expiration: { maxEntries: 20, maxAgeSeconds: 300 },
            },
          },
        ],
      },
    }),
  ],
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
        target: 'http://localhost:8000',
        changeOrigin: true,
        //rewrite: (path) => path.replace(/^\/api/, ''), api를 제거하고 보낼거면 주석제거
      },
    },
  },
})