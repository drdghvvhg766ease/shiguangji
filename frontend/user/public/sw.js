/* 时光迹 Service Worker：只缓存应用外壳与静态资源，接口数据一律走网络 */
const VERSION = 'sgj-v1'
const SHELL_CACHE = `${VERSION}-shell`
const ASSET_CACHE = `${VERSION}-assets`
const SHELL_ASSETS = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/icons/apple-touch-icon.png',
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll(SHELL_ASSETS))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => !key.startsWith(VERSION)).map((key) => caches.delete(key))),
      )
      .then(() => self.clients.claim()),
  )
})

const ASSET_PATTERN = /\.(?:js|css|mjs|woff2?|ttf|otf|png|jpe?g|webp|avif|svg|ico|webmanifest)$/i

self.addEventListener('fetch', (event) => {
  const request = event.request
  if (request.method !== 'GET') return

  let url
  try {
    url = new URL(request.url)
  } catch {
    return
  }
  if (url.origin !== self.location.origin) return

  // 接口与鉴权请求不缓存，避免读到过期数据
  if (url.pathname.startsWith('/api/')) return

  // 页面导航：先网络，断网时回退到缓存的外壳
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone()
          caches.open(SHELL_CACHE).then((cache) => cache.put('/index.html', copy)).catch(() => {})
          return response
        })
        .catch(async () => {
          const cached = (await caches.match('/index.html')) || (await caches.match('/'))
          return (
            cached ||
            new Response('<h1>暂时无法连接</h1><p>请在网络恢复后重新打开时光迹。</p>', {
              status: 503,
              headers: { 'Content-Type': 'text/html; charset=utf-8' },
            })
          )
        }),
    )
    return
  }

  // 静态资源：缓存优先 + 后台更新
  if (ASSET_PATTERN.test(url.pathname)) {
    event.respondWith(
      caches.open(ASSET_CACHE).then(async (cache) => {
        const cached = await cache.match(request)
        const network = fetch(request)
          .then((response) => {
            if (response && response.ok) cache.put(request, response.clone())
            return response
          })
          .catch(() => null)
        return cached || (await network) || Response.error()
      }),
    )
  }
})
