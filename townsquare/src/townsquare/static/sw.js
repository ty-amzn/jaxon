const CACHE='town-square-v7';
const SHELL=['/feed/ui','/feed/icon-192.svg','/feed/static/styles.css','/feed/static/app.js'];
const FONT_RE=/fonts\.googleapis\.com|fonts\.gstatic\.com/;
const API_RE=/\/feed\/(posts|channels)/;

self.addEventListener('install',e=>{
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));
});

self.addEventListener('activate',e=>{
  e.waitUntil(caches.keys().then(ks=>Promise.all(
    ks.filter(k=>k!==CACHE).map(k=>caches.delete(k))
  )).then(()=>self.clients.claim()));
});

self.addEventListener('fetch',e=>{
  const url=new URL(e.request.url);
  // Network-first for API calls
  if(API_RE.test(url.pathname)){
    e.respondWith(
      fetch(e.request).then(r=>{
        const cl=r.clone();
        caches.open(CACHE).then(c=>c.put(e.request,cl));
        return r;
      }).catch(()=>caches.match(e.request))
    );
    return;
  }
  // Cache-first for fonts, icons, and static assets
  if(FONT_RE.test(url.hostname)||url.pathname.startsWith('/feed/icon')||url.pathname.startsWith('/feed/static/')){
    e.respondWith(
      caches.match(e.request).then(r=>r||fetch(e.request).then(nr=>{
        const cl=nr.clone();
        caches.open(CACHE).then(c=>c.put(e.request,cl));
        return nr;
      }))
    );
    return;
  }
  // Shell (the UI page itself) — network-first with cache fallback
  e.respondWith(
    fetch(e.request).then(r=>{
      const cl=r.clone();
      caches.open(CACHE).then(c=>c.put(e.request,cl));
      return r;
    }).catch(()=>caches.match(e.request))
  );
});
