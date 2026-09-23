import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/images': {
        target: 'https://hrfhf8qlce.execute-api.ap-southeast-2.amazonaws.com',
        changeOrigin: true,
        secure: false, // Helps avoid local SSL certificate issues
      }
    },
  },
  envDir: '..',
  envPrefix: ["VITE_"]
})
