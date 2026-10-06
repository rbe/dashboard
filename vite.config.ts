import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import { handleDashboardApi } from './scripts/dashboard-api.mjs'

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'local-dashboard-api',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          const pathname = req.url?.split('?')[0]
          if (pathname !== '/api/dashboard') {
            next()
            return
          }
          handleDashboardApi(req, res)
        })
      },
    },
  ],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    watch: {
      ignored: ['**/data/dashboard.md', '**/data/dashboard.md.tmp'],
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts', 'scripts/**/*.test.mjs'],
  },
})
