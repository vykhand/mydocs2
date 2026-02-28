import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'
import http from 'node:http'
import https from 'node:https'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Follow 307 redirects server-side so the browser never sees
        // cross-origin redirects to Azure Blob Storage SAS URLs.
        selfHandleResponse: true,
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes, req, res) => {
            const status = proxyRes.statusCode || 200
            if ((status === 307 || status === 302 || status === 301) && proxyRes.headers.location) {
              // Follow the redirect server-side
              const redirectUrl = proxyRes.headers.location
              const client = redirectUrl.startsWith('https') ? https : http
              client.get(redirectUrl, (upstreamRes) => {
                // Forward status and headers (except hop-by-hop)
                const headers = { ...upstreamRes.headers }
                delete headers['transfer-encoding']
                res.writeHead(upstreamRes.statusCode || 200, headers)
                upstreamRes.pipe(res)
              }).on('error', (err) => {
                console.error('Proxy redirect follow error:', err.message)
                res.writeHead(502)
                res.end('Proxy redirect failed')
              })
            } else {
              // Pass through non-redirect responses as-is
              res.writeHead(status, proxyRes.headers)
              proxyRes.pipe(res)
            }
          })
        },
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
