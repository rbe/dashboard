import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import { handleDashboardApi } from './server/dashboard-api.mjs'

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
    include: [
      'src/**/*.test.ts',
      'scripts/**/*.test.mjs',
      'server/**/*.test.mjs',
      'shared/**/*.test.ts',
      'client/src/**/*.test.ts',
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'json-summary', 'lcov'],
      reportsDirectory: 'build/coverage',
      include: ['src/**', 'scripts/**', 'server/**', 'shared/validate.mjs', 'client/src/**'],
      exclude: ['**/*.test.*'],
    },
  },
})
