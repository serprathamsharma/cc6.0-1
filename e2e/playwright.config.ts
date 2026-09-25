import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  timeout: 120_000,
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
  },
  reporter: [['html', { open: 'never' }], ['list']],
})
