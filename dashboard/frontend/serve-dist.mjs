import http from 'node:http'
import { createReadStream, existsSync } from 'node:fs'
import { stat } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const distDir = path.join(__dirname, 'dist')
const port = Number(process.env.PORT || 5173)
const host = process.env.HOST || '127.0.0.1'
const backendUrl = new URL(process.env.BACKEND_URL || 'http://127.0.0.1:8000')

const mimeTypes = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
}

function proxyToBackend(req, res) {
  const target = new URL(req.url, backendUrl)
  const proxyReq = http.request(
    target,
    {
      method: req.method,
      headers: {
        ...req.headers,
        host: backendUrl.host,
      },
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 502, proxyRes.headers)
      proxyRes.pipe(res)
    },
  )

  proxyReq.on('error', (error) => {
    res.writeHead(502, { 'content-type': 'application/json; charset=utf-8' })
    res.end(JSON.stringify({ error: `Backend proxy failed: ${error.message}` }))
  })

  req.pipe(proxyReq)
}

function safeFilePath(requestPath) {
  const decodedPath = decodeURIComponent(requestPath.split('?')[0])
  const normalized = path.normalize(decodedPath).replace(/^(\.\.[/\\])+/, '')
  const filePath = path.join(distDir, normalized === '/' ? 'index.html' : normalized)
  return filePath.startsWith(distDir) ? filePath : path.join(distDir, 'index.html')
}

async function serveFile(req, res) {
  let filePath = safeFilePath(req.url || '/')

  if (!existsSync(filePath) || (await stat(filePath)).isDirectory()) {
    filePath = path.join(distDir, 'index.html')
  }

  const ext = path.extname(filePath)
  res.writeHead(200, { 'content-type': mimeTypes[ext] || 'application/octet-stream' })
  createReadStream(filePath).pipe(res)
}

if (!existsSync(path.join(distDir, 'index.html'))) {
  console.error('Missing dist/index.html. Run `npm run build` before `npm run serve`.')
  process.exit(1)
}

const server = http.createServer((req, res) => {
  if (req.url?.startsWith('/api/') || req.url?.startsWith('/screenshots')) {
    proxyToBackend(req, res)
    return
  }

  serveFile(req, res).catch((error) => {
    res.writeHead(500, { 'content-type': 'text/plain; charset=utf-8' })
    res.end(error.message)
  })
})

server.listen(port, host, () => {
  console.log(`Frontend preview running at http://${host}:${port}`)
  console.log(`Proxying API requests to ${backendUrl.origin}`)
})
