import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // FastAPI serves built files from /static; app routes fall back to index.html.
  build: { assetsDir: 'static' },
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
