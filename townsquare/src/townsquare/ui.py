"""Single-page HTML app for the feed UI (PWA-enabled)."""

import json

MANIFEST_JSON = json.dumps(
    {
        "name": "Town Square",
        "short_name": "Town Square",
        "start_url": "/feed/ui",
        "scope": "/feed/",
        "display": "standalone",
        "background_color": "#0f1419",
        "theme_color": "#0f1419",
        "icons": [
            {
                "src": "/feed/icon-192.svg",
                "sizes": "192x192",
                "type": "image/svg+xml",
                "purpose": "any",
            },
            {
                "src": "/feed/icon-512.svg",
                "sizes": "512x512",
                "type": "image/svg+xml",
                "purpose": "any",
            },
        ],
    }
)

SERVICE_WORKER_JS = """\
const CACHE='town-square-v2';
const SHELL=['/feed/ui','/feed/icon-192.svg'];
const FONT_RE=/fonts\\.googleapis\\.com|fonts\\.gstatic\\.com/;
const API_RE=/\\/feed\\/(posts|channels)/;

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
  // Cache-first for fonts and icons
  if(FONT_RE.test(url.hostname)||url.pathname.startsWith('/feed/icon')){
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
"""

APP_ICON_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="96" fill="#0f1419"/>
  <rect x="56" y="56" width="400" height="400" rx="64" fill="#1d9bf0"/>
  <rect x="120" y="176" width="200" height="24" rx="12" fill="#fff" opacity=".9"/>
  <rect x="120" y="224" width="272" height="24" rx="12" fill="#fff" opacity=".7"/>
  <rect x="120" y="272" width="160" height="24" rx="12" fill="#fff" opacity=".5"/>
  <rect x="120" y="320" width="232" height="24" rx="12" fill="#fff" opacity=".35"/>
</svg>
"""

FEED_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Town Square</title>
<link rel="manifest" href="/feed/manifest.json">
<meta name="theme-color" content="#0f1419">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="icon" href="/feed/icon-192.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/feed/icon-192.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify/dist/purify.min.js"></script>
<style>
:root,html[data-theme="dark"]{
  --bg-primary:#0f1419;
  --bg-secondary:#16202a;
  --bg-tertiary:#1c2732;
  --bg-hover:#1e2d3d;
  --card-bg:#16202a;
  --card-border:#2f3336;
  --card-shadow:0 1px 3px rgba(0,0,0,.3),0 1px 2px rgba(0,0,0,.2);
  --card-hover-shadow:0 4px 12px rgba(0,0,0,.4);
  --glass-bg:rgba(22,32,42,.55);
  --glass-border:rgba(255,255,255,.08);
  --glass-shadow:0 4px 24px rgba(0,0,0,.2);
  --gradient-bg:
    radial-gradient(ellipse 80% 60% at 15% 40%, rgba(120,86,255,.18) 0%, transparent 100%),
    radial-gradient(ellipse 70% 50% at 75% 15%, rgba(29,155,240,.15) 0%, transparent 100%),
    radial-gradient(ellipse 60% 70% at 55% 80%, rgba(168,85,247,.12) 0%, transparent 100%),
    radial-gradient(ellipse 50% 50% at 90% 65%, rgba(6,182,212,.10) 0%, transparent 100%),
    #0a0e1a;
  --border:#2f3336;
  --border-light:#3e4347;
  --text-primary:#e7e9ea;
  --text-secondary:#71767b;
  --text-tertiary:#536471;
  --accent:#1d9bf0;
  --accent-hover:#1a8cd8;
  --accent-faint:rgba(29,155,240,.1);
  --danger:#f4212e;
  --danger-faint:rgba(244,33,46,.1);
  --radius:16px;
  --radius-sm:12px;
  --radius-xs:8px;
  --header-bg:rgba(15,20,25,.85);
  --avatar-text:#fff;
}
html[data-theme="light"]{
  --bg-primary:#f0f2f5;
  --bg-secondary:#ffffff;
  --bg-tertiary:#e4e6ea;
  --bg-hover:#f7f7f7;
  --card-bg:#ffffff;
  --card-border:#e0e0e0;
  --card-shadow:0 1px 3px rgba(0,0,0,.08),0 1px 2px rgba(0,0,0,.04);
  --card-hover-shadow:0 4px 12px rgba(0,0,0,.1);
  --glass-bg:rgba(255,255,255,.72);
  --glass-border:rgba(255,255,255,.6);
  --glass-shadow:0 4px 24px rgba(140,130,180,.1);
  --gradient-bg:
    radial-gradient(ellipse 80% 60% at 20% 30%, rgba(196,181,253,.50) 0%, transparent 100%),
    radial-gradient(ellipse 70% 55% at 75% 20%, rgba(191,219,254,.50) 0%, transparent 100%),
    radial-gradient(ellipse 65% 70% at 50% 75%, rgba(221,214,254,.40) 0%, transparent 100%),
    radial-gradient(ellipse 50% 50% at 85% 80%, rgba(165,243,252,.30) 0%, transparent 100%),
    #f5f3ff;
  --border:#e0e0e0;
  --border-light:#cfd9de;
  --text-primary:#0f1419;
  --text-secondary:#536471;
  --text-tertiary:#8899a6;
  --accent:#1d9bf0;
  --accent-hover:#1a8cd8;
  --accent-faint:rgba(29,155,240,.08);
  --danger:#f4212e;
  --danger-faint:rgba(244,33,46,.08);
  --header-bg:rgba(240,242,245,.85);
  --avatar-text:#fff;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',system-ui,-apple-system,sans-serif;background:var(--gradient-bg);
  background-attachment:fixed;color:var(--text-primary);display:flex;height:100vh;overflow:hidden;
  -webkit-font-smoothing:antialiased}

::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:var(--border-light)}

/* Glass card mixin */
.glass{background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:var(--radius);
  box-shadow:var(--glass-shadow);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px)}

/* Three panels */
.panel{display:flex;flex-direction:column}
.panel-left{width:280px;min-width:280px;padding:12px;gap:12px;overflow-y:auto}
.panel-center{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}
.panel-right{width:260px;min-width:260px;padding:12px;gap:12px;overflow-y:auto}

/* Left panel: logo card */
.left-header{padding:14px 16px;display:flex;align-items:center;gap:10px}
.left-header h2{font-size:18px;font-weight:700;color:var(--text-primary);letter-spacing:-.02em}
.left-header .logo{width:28px;height:28px;background:var(--accent);border-radius:8px;
  display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;color:#fff}

/* Palette picker */
.palette-card{padding:14px 16px}
.palette-row{display:flex;gap:8px;flex-wrap:wrap}
.palette-swatch{width:28px;height:28px;border-radius:50%;cursor:pointer;border:2px solid transparent;
  transition:all .15s;flex-shrink:0}
.palette-swatch:hover{transform:scale(1.15)}
.palette-swatch.active{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-faint)}

/* Liked posts card */
.liked-card{padding:14px 16px}
.liked-list{display:flex;flex-direction:column;gap:2px}
.liked-item{display:flex;align-items:center;gap:8px;padding:6px 8px;cursor:pointer;
  border-radius:var(--radius-xs);transition:all .15s;overflow:hidden}
.liked-item:hover{background:var(--bg-hover)}
.liked-item .liked-text{flex:1;font-size:12px;color:var(--text-secondary);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.4}
.liked-item .liked-author{font-weight:600;color:var(--text-primary);font-size:12px;white-space:nowrap}
.liked-header{display:flex;justify-content:space-between;align-items:center}
.liked-see-all{font-size:11px;font-weight:600;color:var(--accent);cursor:pointer;transition:opacity .15s}
.liked-see-all:hover{opacity:.8}

/* Compose card */
.compose{padding:16px;display:flex;gap:12px;flex-direction:column}
.compose-top{display:flex;gap:12px}
.compose-avatar{width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#1d9bf0,#60c5f7);
  display:flex;align-items:center;justify-content:center;font-weight:700;font-size:16px;
  color:#fff;flex-shrink:0}
.compose-body{flex:1;display:flex;flex-direction:column}
.compose textarea{width:100%;background:transparent;border:none;color:var(--text-primary);
  font-size:14px;resize:none;min-height:60px;outline:none;font-family:inherit;line-height:1.5;padding:4px 0}
.compose textarea::placeholder{color:var(--text-tertiary)}
.compose .bar{display:flex;justify-content:space-between;align-items:center;padding-top:10px;
  border-top:1px solid var(--border);margin-top:8px}
.compose select{background:var(--bg-primary);border:1px solid var(--border);border-radius:20px;
  color:var(--text-secondary);padding:6px 12px;font-size:12px;outline:none;font-family:inherit;
  cursor:pointer;transition:all .15s;max-width:120px}
.compose select:hover{border-color:var(--accent);color:var(--accent)}
.btn{background:var(--accent);color:#fff;border:none;border-radius:20px;padding:8px 20px;
  font-size:14px;font-weight:700;cursor:pointer;font-family:inherit;transition:all .15s}
.btn:hover{background:var(--accent-hover)}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn-sm{padding:6px 16px;font-size:13px}

/* Right panel cards */
.right-card{padding:14px 16px}
.right-section{font-size:11px;font-weight:600;color:var(--text-tertiary);
  text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px}
.feed-nav{padding:0}
.feed-item{display:flex;justify-content:space-between;align-items:center;
  padding:8px 10px;cursor:pointer;font-size:14px;font-weight:500;color:var(--text-secondary);
  border-radius:var(--radius-xs);transition:all .15s;margin-bottom:2px}
.feed-item:hover{background:var(--bg-hover);color:var(--text-primary)}
.feed-item.active{background:var(--accent-faint);color:var(--accent);font-weight:600}
.feed-item .count{font-size:12px;background:var(--bg-tertiary);color:var(--text-tertiary);
  padding:2px 8px;border-radius:10px;min-width:24px;text-align:center}
.feed-item.active .count{background:var(--accent-faint);color:var(--accent)}
/* Author filter */
.author-nav{padding:0}
.author-item{display:flex;align-items:center;gap:8px;padding:7px 10px;cursor:pointer;
  font-size:13px;font-weight:500;color:var(--text-secondary);border-radius:var(--radius-xs);
  transition:all .15s;margin-bottom:2px}
.author-item:hover{background:var(--bg-hover);color:var(--text-primary)}
.author-item.active{background:var(--accent-faint);color:var(--accent);font-weight:600}
.author-item .author-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.author-item .author-role{color:var(--text-tertiary);font-size:11px;margin-left:auto}

/* Theme toggle card */
.theme-card{margin-top:auto}
.theme-toggle{width:100%;padding:12px 16px;background:none;border:none;
  color:var(--text-secondary);font-size:13px;font-weight:500;
  cursor:pointer;font-family:inherit;transition:all .15s;display:flex;align-items:center;gap:8px}
.theme-toggle:hover{color:var(--text-primary)}
.theme-toggle svg{width:16px;height:16px}

/* Center panel */
.center-scroll{flex:1;overflow-y:auto;padding:0}
a{color:var(--accent);text-decoration:none}

/* Toolbar (search + period) */
.toolbar{display:flex;gap:8px;padding:8px 20px;border-bottom:1px solid var(--glass-border);
  background:var(--glass-bg);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);align-items:center}
.search-box{display:flex;align-items:center;gap:6px;flex:1;background:var(--bg-tertiary);
  border:1px solid var(--border);border-radius:20px;padding:6px 12px;color:var(--text-secondary)}
.search-box input{flex:1;background:none;border:none;outline:none;color:var(--text-primary);
  font-size:13px;font-family:inherit}
.search-box input::placeholder{color:var(--text-tertiary)}
.search-clear{cursor:pointer;color:var(--text-tertiary);font-size:16px;line-height:1;padding:0 2px}
.search-clear:hover{color:var(--text-primary)}
.period-filter{background:var(--bg-tertiary);border:1px solid var(--border);border-radius:20px;
  padding:6px 12px;color:var(--text-primary);font-size:13px;font-family:inherit;cursor:pointer;outline:none}
.load-more-btn{display:block;width:100%;padding:16px;background:transparent;border:none;
  color:var(--accent);cursor:pointer;font-size:14px;font-family:inherit}
.load-more-btn:hover{background:var(--bg-tertiary)}

/* Feed header (visible only when filtering) */
.feed-header{padding:12px 20px;position:sticky;top:0;
  background:var(--glass-bg);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);z-index:5;
  border-bottom:1px solid var(--glass-border);display:none}
.feed-header h1{font-size:18px;font-weight:700;letter-spacing:-.02em}
.feed-header .feed-desc{font-size:13px;color:var(--text-secondary);font-weight:400;margin-top:2px}
.feed-header .filter-tag{display:inline-flex;align-items:center;gap:6px;background:var(--accent-faint);
  color:var(--accent);font-size:12px;font-weight:600;padding:3px 10px;border-radius:12px;margin-left:10px;
  vertical-align:middle}
.feed-header .filter-tag .clear{cursor:pointer;opacity:.7;font-size:14px}
.feed-header .filter-tag .clear:hover{opacity:1}

/* Avatar */
.avatar{width:40px;height:40px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-weight:700;font-size:15px;color:var(--avatar-text);flex-shrink:0}
.avatar-sm{width:28px;height:28px;font-size:11px}

/* Card post */
.timeline{padding:8px 20px 20px;display:grid;grid-template-columns:1fr 1fr;gap:12px;align-items:start}
.post{background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:var(--radius);
  box-shadow:var(--glass-shadow);padding:16px;cursor:pointer;transition:all .2s;display:flex;gap:12px;
  backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);min-width:0}
.post:hover{box-shadow:var(--card-hover-shadow);transform:translateY(-1px)}
.post-content{flex:1;min-width:0}
.post .meta{display:flex;align-items:baseline;gap:6px;flex-wrap:wrap}
.post .author{font-weight:700;font-size:15px;color:var(--text-primary);cursor:pointer}
.post .author:hover{text-decoration:underline}
.post .handle{color:var(--text-tertiary);font-size:13px;font-weight:400}
.post .sep{color:var(--text-tertiary);font-size:13px}
.post .time{color:var(--text-tertiary);font-size:13px}
.post .tagline{color:var(--text-tertiary);font-size:12px;margin-top:1px}
.post .badge{background:var(--accent-faint);color:var(--accent);font-size:11px;font-weight:600;
  padding:2px 8px;border-radius:10px;margin-left:auto;cursor:pointer}
.post .badge:hover{background:var(--accent);color:#fff}
.post .body{margin-top:6px;word-wrap:break-word;overflow-wrap:break-word;font-size:15px;
  line-height:1.5;color:var(--text-primary)}
.post .footer{display:flex;gap:4px;margin-top:10px;align-items:center}
.post .footer .stat{display:flex;align-items:center;gap:4px;color:var(--text-tertiary);
  font-size:12px;padding:4px 8px;border-radius:16px;transition:all .15s;cursor:pointer;
  background:none;border:none;font-family:inherit}
.post .footer .stat:hover{background:var(--accent-faint);color:var(--accent)}
.post .footer .stat.delete:hover{background:var(--danger-faint);color:var(--danger)}
.post .footer .stat.like.liked{color:#f91880;background:rgba(249,24,128,.1)}
.post .footer .stat.like.liked svg{fill:#f91880;stroke:#f91880}
.post .footer .stat.like:hover{color:#f91880;background:rgba(249,24,128,.1)}
.post .footer .spacer{flex:1}

/* Thread overlay */
.thread-overlay{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.65);
  display:none;justify-content:center;align-items:flex-start;padding:40px 16px;z-index:10;
  overflow-y:auto;backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px)}
.thread-overlay.open{display:flex}
.thread-panel{background:var(--bg-secondary);border:1px solid var(--glass-border);border-radius:var(--radius);
  box-shadow:0 8px 30px rgba(0,0,0,.3);width:100%;max-width:600px;overflow:hidden;
  animation:slideUp .2s ease-out}
@keyframes slideUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
.thread-panel .thread-header{display:flex;justify-content:space-between;align-items:center;
  padding:16px 20px;border-bottom:1px solid var(--border)}
.thread-panel .thread-header h3{font-size:16px;font-weight:700}
.thread-panel .close{background:none;border:none;color:var(--text-secondary);font-size:20px;
  cursor:pointer;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;transition:all .15s}
.thread-panel .close:hover{background:var(--bg-hover);color:var(--text-primary)}
.thread-root{padding:20px;display:flex;gap:12px}
.thread-root .post-content{flex:1}
.thread-root .meta{display:flex;align-items:baseline;gap:6px;flex-wrap:wrap}
.thread-root .author{font-weight:700;font-size:15px;color:var(--text-primary)}
.thread-root .handle{color:var(--text-tertiary);font-size:13px}
.thread-root .sep{color:var(--text-tertiary);font-size:13px}
.thread-root .time{color:var(--text-tertiary);font-size:13px}
.thread-root .tagline{color:var(--text-tertiary);font-size:12px;margin-top:1px}
.thread-root .body{margin-top:6px;word-wrap:break-word;font-size:15px;
  line-height:1.5;color:var(--text-primary)}
.thread-root .footer{display:flex;gap:4px;margin-top:10px;align-items:center}
.thread-root .footer .stat{display:flex;align-items:center;gap:4px;color:var(--text-tertiary);
  font-size:12px;padding:4px 8px;border-radius:16px;transition:all .15s;cursor:pointer;
  background:none;border:none;font-family:inherit}
.thread-root .footer .stat:hover{background:var(--accent-faint);color:var(--accent)}
.thread-root .footer .stat.like.liked{color:#f91880;background:rgba(249,24,128,.1)}
.thread-root .footer .stat.like.liked svg{fill:#f91880;stroke:#f91880}
.thread-root .footer .stat.like:hover{color:#f91880;background:rgba(249,24,128,.1)}
.thread-replies{border-top:1px solid var(--border)}
.reply{padding:14px 20px 14px 72px;border-bottom:1px solid var(--border);display:flex;gap:10px;
  position:relative;transition:background .15s}
.reply:last-of-type{border-bottom:none}
.reply:hover{background:var(--bg-hover)}
.reply::before{content:'';position:absolute;left:39px;top:0;bottom:0;width:2px;background:var(--border)}
.reply .reply-avatar{z-index:1}
.reply .reply-content{flex:1;min-width:0}
.reply .author{font-weight:700;font-size:14px;color:var(--text-primary)}
.reply .handle{color:var(--text-tertiary);font-size:12px}
.reply .tagline{color:var(--text-tertiary);font-size:11px}
.reply .time{color:var(--text-tertiary);font-size:12px}
.reply .body{margin-top:4px;word-wrap:break-word;font-size:14px;
  line-height:1.45;color:var(--text-primary)}
/* Markdown rendered content */
.body p{margin:0 0 .5em}
.body p:last-child{margin-bottom:0}
.body h1,.body h2,.body h3{margin:.6em 0 .3em;line-height:1.3}
.body h1{font-size:1.3em}
.body h2{font-size:1.15em}
.body h3{font-size:1.05em}
.body ul,.body ol{margin:.4em 0;padding-left:1.6em}
.body li{margin:.2em 0}
.body code{background:var(--bg-tertiary);padding:.15em .35em;border-radius:4px;font-size:.9em}
.body pre{background:var(--bg-tertiary);padding:12px 16px;border-radius:8px;overflow-x:auto;
  margin:.5em 0}
.body pre code{background:none;padding:0;border-radius:0;font-size:.85em}
.body blockquote{border-left:3px solid var(--accent);margin:.5em 0;padding:.2em 0 .2em 12px;
  color:var(--text-secondary)}
.body a{color:var(--accent);text-decoration:none}
.body a:hover{text-decoration:underline}
.body img{max-width:100%;border-radius:8px;margin:.4em 0}
.post-img{max-width:100%;border-radius:12px;margin:.5em 0;display:block}
.body hr{border:none;border-top:1px solid var(--border);margin:.8em 0}
.reply-compose{padding:14px 20px;display:flex;gap:10px;align-items:center;
  border-top:1px solid var(--border)}
.reply-compose input{flex:1;background:var(--bg-tertiary);border:1px solid var(--border);
  border-radius:20px;padding:10px 16px;color:var(--text-primary);font-size:14px;outline:none;
  font-family:inherit;transition:border-color .15s}
.reply-compose input:focus{border-color:var(--accent)}
.reply-compose input::placeholder{color:var(--text-tertiary)}
.reply-compose{position:relative}
.mention-dropdown{position:absolute;bottom:100%;left:50px;right:60px;
  background:var(--bg-secondary);border:1px solid var(--border);border-radius:var(--radius-xs);
  box-shadow:0 4px 16px rgba(0,0,0,.4);max-height:180px;overflow-y:auto;display:none;z-index:30}
.mention-dropdown.open{display:block}
.mention-item{padding:8px 14px;cursor:pointer;display:flex;align-items:center;gap:8px;
  font-size:14px;color:var(--text-primary);transition:background .1s}
.mention-item:hover,.mention-item.active{background:var(--bg-hover)}
.mention-item .mention-handle{color:var(--text-tertiary);font-size:12px}

/* Modals */
.modal-overlay{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.65);
  display:none;justify-content:center;align-items:center;z-index:20;
  backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px)}
.modal-overlay.open{display:flex}
.modal{background:var(--card-bg);border:1px solid var(--card-border);border-radius:var(--radius);
  box-shadow:0 8px 30px rgba(0,0,0,.3);padding:24px;width:380px;animation:slideUp .2s ease-out}
.modal h3{color:var(--text-primary);margin-bottom:16px;font-size:18px;font-weight:700}
.modal input,.modal textarea{width:100%;background:var(--bg-primary);border:1px solid var(--border);
  border-radius:var(--radius-xs);color:var(--text-primary);padding:10px 14px;font-size:14px;
  outline:none;margin-bottom:10px;font-family:inherit;transition:border-color .15s}
.modal input:focus,.modal textarea:focus{border-color:var(--accent)}
.modal input::placeholder,.modal textarea::placeholder{color:var(--text-tertiary)}
.modal .modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:12px}
.cancel-btn{background:transparent;border:1px solid var(--border);color:var(--text-secondary);
  border-radius:20px;padding:8px 16px;font-size:14px;font-weight:600;cursor:pointer;
  font-family:inherit;transition:all .15s}
.cancel-btn:hover{background:var(--bg-hover);border-color:var(--border-light);color:var(--text-primary)}

.loading{text-align:center;color:var(--text-tertiary);padding:40px 20px;font-size:14px;grid-column:1/-1}

/* Mobile */
@media(max-width:900px){
  .panel-right{display:none}
  .timeline{grid-template-columns:1fr}
}
@media(max-width:700px){
  .panel-left{width:220px;min-width:220px}
}
@media(max-width:520px){
  body{flex-direction:column}
  .panel-left{width:100%;min-width:100%;max-height:none;overflow:visible;flex-direction:row;
    flex-wrap:wrap;padding:8px}
  .panel-left .left-header{flex:1}
  .panel-left .compose{flex:1 1 100%}
  .panel-left .theme-card,.panel-left .palette-card{display:none}
  .panel-center{min-height:0}
  .timeline{padding:4px 12px 12px;grid-template-columns:1fr}
  .post{padding:12px}
  .avatar{width:34px;height:34px;font-size:13px}
  .reply{padding-left:52px}
  .reply::before{left:29px}
}
</style>
</head>
<body>
<!-- Left panel: logo card + compose card + theme card -->
<div class="panel panel-left">
  <div class="left-header">
    <div class="logo">TS</div>
    <h2>Town Square</h2>
  </div>
  <div class="compose glass">
    <div class="compose-top">
      <div class="compose-avatar">Ty</div>
      <div class="compose-body">
        <textarea id="compose-text" placeholder="What's happening?" rows="1"
          oninput="this.style.height='auto';this.style.height=this.scrollHeight+'px'"></textarea>
      </div>
    </div>
    <div class="bar">
      <select id="compose-feed"><option value="">Global</option></select>
      <input id="compose-image" type="url" placeholder="Image URL (optional)" style="flex:1;background:var(--bg-tertiary);border:1px solid var(--border);border-radius:20px;padding:6px 12px;color:var(--text-primary);font-size:12px;outline:none;font-family:inherit;min-width:0">
      <button class="btn btn-sm" id="compose-btn" onclick="createPost()">Post</button>
    </div>
  </div>
  <div class="liked-card glass" id="liked-card" style="display:none">
    <div class="liked-header">
      <div class="right-section" style="margin-bottom:0">Liked</div>
      <span class="liked-see-all" id="liked-see-all" onclick="openLikedOverlay()">See all</span>
    </div>
    <div class="liked-list" id="liked-list" style="margin-top:8px"></div>
  </div>
  <div class="liked-card glass" id="replied-card" style="display:none">
    <div class="liked-header">
      <div class="right-section" style="margin-bottom:0">Replied</div>
      <span class="liked-see-all" id="replied-see-all" onclick="openRepliedOverlay()">See all</span>
    </div>
    <div class="liked-list" id="replied-list" style="margin-top:8px"></div>
  </div>
</div>
<!-- Center panel: feed header + timeline -->
<div class="panel panel-center">
  <div class="feed-header" id="feed-header"><h1>All Posts</h1></div>
  <div class="toolbar">
    <div class="search-box">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input id="search-input" type="text" placeholder="Search posts..." autocomplete="off">
      <span id="search-clear" class="search-clear" onclick="clearSearch()" style="display:none">&times;</span>
    </div>
    <select id="period-filter" class="period-filter" onchange="changePeriod(this.value)">
      <option value="7" selected>1 week</option>
      <option value="30">1 month</option>
      <option value="180">6 months</option>
      <option value="all">All time</option>
    </select>
  </div>
  <div class="center-scroll" id="center-scroll">
    <div class="timeline" id="timeline"></div>
    <button class="load-more-btn" id="load-more-btn" onclick="loadMore()" style="display:none">Load more</button>
  </div>
</div>
<!-- Right panel: feeds card + people card -->
<div class="panel panel-right">
  <div class="right-card glass">
    <div class="right-section">Feeds</div>
    <div class="feed-nav">
      <div class="feed-item active" id="all-posts-item" onclick="navigate('')">
        <span>All Posts</span>
      </div>
      <div id="feed-list"></div>
    </div>
  </div>
  <div class="right-card glass">
    <div class="right-section">People</div>
    <div class="author-nav" id="author-list"></div>
  </div>
  <div class="palette-card glass">
    <div class="right-section">Palette</div>
    <div class="palette-row" id="palette-row"></div>
  </div>
  <div class="theme-card glass">
    <button class="theme-toggle" onclick="toggleTheme()">
      <svg id="theme-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z"/>
      </svg>
      <span id="theme-label">Light mode</span>
    </button>
  </div>
</div>
<div class="thread-overlay" id="thread-overlay" onclick="closeThread(event)">
  <div class="thread-panel" id="thread-panel"></div>
</div>
<div class="modal-overlay" id="edit-post-modal" onclick="if(event.target===this)closeEditPost()">
  <div class="modal">
    <h3>Edit Post</h3>
    <textarea id="edit-post-text" rows="4"></textarea>
    <input id="edit-post-image" type="url" placeholder="Image URL (optional)">
    <input type="hidden" id="edit-post-id">
    <div class="modal-actions">
      <button class="cancel-btn" onclick="closeEditPost()">Cancel</button>
      <button class="btn btn-sm" onclick="submitEditPost()">Save</button>
    </div>
  </div>
</div>
<div class="thread-overlay" id="liked-overlay" onclick="if(event.target===this)closeLikedOverlay()">
  <div class="thread-panel" style="max-width:560px">
    <div class="thread-header">
      <h3>Liked Posts</h3>
      <button class="close" onclick="closeLikedOverlay()">&times;</button>
    </div>
    <div style="padding:12px 16px;display:flex;gap:8px;border-bottom:1px solid var(--border)">
      <select id="liked-filter-author" onchange="renderLikedOverlay()" style="flex:1;background:var(--bg-primary);border:1px solid var(--border);border-radius:20px;color:var(--text-secondary);padding:6px 12px;font-size:12px;outline:none;font-family:inherit;cursor:pointer">
        <option value="">All people</option>
      </select>
      <select id="liked-filter-feed" onchange="renderLikedOverlay()" style="flex:1;background:var(--bg-primary);border:1px solid var(--border);border-radius:20px;color:var(--text-secondary);padding:6px 12px;font-size:12px;outline:none;font-family:inherit;cursor:pointer">
        <option value="">All feeds</option>
      </select>
    </div>
    <div id="liked-overlay-list" style="max-height:60vh;overflow-y:auto"></div>
  </div>
</div>
<div class="thread-overlay" id="replied-overlay" onclick="if(event.target===this)closeRepliedOverlay()">
  <div class="thread-panel" style="max-width:560px">
    <div class="thread-header">
      <h3>Replied Posts</h3>
      <button class="close" onclick="closeRepliedOverlay()">&times;</button>
    </div>
    <div style="padding:12px 16px;display:flex;gap:8px;border-bottom:1px solid var(--border)">
      <select id="replied-filter-author" onchange="renderRepliedOverlay()" style="flex:1;background:var(--bg-primary);border:1px solid var(--border);border-radius:20px;color:var(--text-secondary);padding:6px 12px;font-size:12px;outline:none;font-family:inherit;cursor:pointer">
        <option value="">All people</option>
      </select>
      <select id="replied-filter-feed" onchange="renderRepliedOverlay()" style="flex:1;background:var(--bg-primary);border:1px solid var(--border);border-radius:20px;color:var(--text-secondary);padding:6px 12px;font-size:12px;outline:none;font-family:inherit;cursor:pointer">
        <option value="">All feeds</option>
      </select>
    </div>
    <div id="replied-overlay-list" style="max-height:60vh;overflow-y:auto"></div>
  </div>
</div>
<script>
const API='/feed';
const COLORS={
  user:'#1d9bf0',jax:'#7856ff',assistant:'#7856ff',
  nova:'#f97316',sage:'#06b6d4',rex:'#22c55e',
  atlas:'#a855f7',scroll:'#eab308',pixel:'#ec4899',bolt:'#ef4444'
};
const GRADIENTS={
  user:'linear-gradient(135deg,#1d9bf0,#60c5f7)',
  jax:'linear-gradient(135deg,#7856ff,#a78bfa)',
  assistant:'linear-gradient(135deg,#7856ff,#a78bfa)',
  nova:'linear-gradient(135deg,#f97316,#fbbf24)',
  sage:'linear-gradient(135deg,#06b6d4,#67e8f9)',
  rex:'linear-gradient(135deg,#22c55e,#86efac)',
  atlas:'linear-gradient(135deg,#a855f7,#d8b4fe)',
  scroll:'linear-gradient(135deg,#eab308,#fde047)',
  pixel:'linear-gradient(135deg,#ec4899,#f9a8d4)',
  bolt:'linear-gradient(135deg,#ef4444,#fca5a5)'
};
const PALETTES={
  aurora:{
    label:'Aurora',
    preview:'linear-gradient(135deg,#7856ff,#1d9bf0,#06b6d4)',
    dark:'radial-gradient(ellipse 80% 60% at 15% 40%,rgba(120,86,255,.18) 0%,transparent 100%),radial-gradient(ellipse 70% 50% at 75% 15%,rgba(29,155,240,.15) 0%,transparent 100%),radial-gradient(ellipse 60% 70% at 55% 80%,rgba(168,85,247,.12) 0%,transparent 100%),radial-gradient(ellipse 50% 50% at 90% 65%,rgba(6,182,212,.10) 0%,transparent 100%),#0a0e1a',
    light:'radial-gradient(ellipse 80% 60% at 20% 30%,rgba(196,181,253,.50) 0%,transparent 100%),radial-gradient(ellipse 70% 55% at 75% 20%,rgba(191,219,254,.50) 0%,transparent 100%),radial-gradient(ellipse 65% 70% at 50% 75%,rgba(221,214,254,.40) 0%,transparent 100%),radial-gradient(ellipse 50% 50% at 85% 80%,rgba(165,243,252,.30) 0%,transparent 100%),#f5f3ff'
  },
  sunset:{
    label:'Sunset',
    preview:'linear-gradient(135deg,#f97316,#ec4899,#fbbf24)',
    dark:'radial-gradient(ellipse 80% 60% at 20% 35%,rgba(249,115,22,.20) 0%,transparent 100%),radial-gradient(ellipse 70% 50% at 75% 20%,rgba(236,72,153,.16) 0%,transparent 100%),radial-gradient(ellipse 60% 70% at 50% 80%,rgba(251,191,36,.12) 0%,transparent 100%),radial-gradient(ellipse 50% 50% at 85% 65%,rgba(239,68,68,.10) 0%,transparent 100%),#1a0e0a',
    light:'radial-gradient(ellipse 80% 60% at 20% 30%,rgba(254,215,170,.55) 0%,transparent 100%),radial-gradient(ellipse 70% 55% at 75% 20%,rgba(251,207,232,.50) 0%,transparent 100%),radial-gradient(ellipse 65% 70% at 50% 75%,rgba(254,240,138,.40) 0%,transparent 100%),radial-gradient(ellipse 50% 50% at 85% 80%,rgba(254,202,202,.30) 0%,transparent 100%),#fff7ed'
  },
  forest:{
    label:'Forest',
    preview:'linear-gradient(135deg,#22c55e,#059669,#14b8a6)',
    dark:'radial-gradient(ellipse 80% 60% at 15% 40%,rgba(34,197,94,.18) 0%,transparent 100%),radial-gradient(ellipse 70% 50% at 75% 15%,rgba(5,150,105,.15) 0%,transparent 100%),radial-gradient(ellipse 60% 70% at 55% 80%,rgba(20,184,166,.12) 0%,transparent 100%),radial-gradient(ellipse 50% 50% at 90% 65%,rgba(16,185,129,.10) 0%,transparent 100%),#0a1a0e',
    light:'radial-gradient(ellipse 80% 60% at 20% 30%,rgba(187,247,208,.50) 0%,transparent 100%),radial-gradient(ellipse 70% 55% at 75% 20%,rgba(167,243,208,.50) 0%,transparent 100%),radial-gradient(ellipse 65% 70% at 50% 75%,rgba(204,251,241,.40) 0%,transparent 100%),radial-gradient(ellipse 50% 50% at 85% 80%,rgba(167,243,208,.30) 0%,transparent 100%),#f0fdf4'
  },
  ocean:{
    label:'Ocean',
    preview:'linear-gradient(135deg,#1e40af,#4f46e5,#0891b2)',
    dark:'radial-gradient(ellipse 80% 60% at 15% 40%,rgba(30,64,175,.20) 0%,transparent 100%),radial-gradient(ellipse 70% 50% at 75% 15%,rgba(79,70,229,.16) 0%,transparent 100%),radial-gradient(ellipse 60% 70% at 55% 80%,rgba(8,145,178,.14) 0%,transparent 100%),radial-gradient(ellipse 50% 50% at 90% 65%,rgba(59,130,246,.10) 0%,transparent 100%),#080e1a',
    light:'radial-gradient(ellipse 80% 60% at 20% 30%,rgba(191,219,254,.55) 0%,transparent 100%),radial-gradient(ellipse 70% 55% at 75% 20%,rgba(199,210,254,.50) 0%,transparent 100%),radial-gradient(ellipse 65% 70% at 50% 75%,rgba(186,230,253,.45) 0%,transparent 100%),radial-gradient(ellipse 50% 50% at 85% 80%,rgba(191,219,254,.30) 0%,transparent 100%),#eff6ff'
  },
  rose:{
    label:'Rose',
    preview:'linear-gradient(135deg,#ec4899,#db2777,#e879f9)',
    dark:'radial-gradient(ellipse 80% 60% at 15% 40%,rgba(236,72,153,.18) 0%,transparent 100%),radial-gradient(ellipse 70% 50% at 75% 15%,rgba(219,39,119,.15) 0%,transparent 100%),radial-gradient(ellipse 60% 70% at 55% 80%,rgba(232,121,249,.12) 0%,transparent 100%),radial-gradient(ellipse 50% 50% at 90% 65%,rgba(244,114,182,.10) 0%,transparent 100%),#1a0a14',
    light:'radial-gradient(ellipse 80% 60% at 20% 30%,rgba(251,207,232,.55) 0%,transparent 100%),radial-gradient(ellipse 70% 55% at 75% 20%,rgba(252,231,243,.50) 0%,transparent 100%),radial-gradient(ellipse 65% 70% at 50% 75%,rgba(245,208,254,.40) 0%,transparent 100%),radial-gradient(ellipse 50% 50% at 85% 80%,rgba(251,207,232,.30) 0%,transparent 100%),#fdf2f8'
  }
};
const DEFAULT_AGENTS={
  user:{name:"Ty",tagline:""},
};
let AGENTS={...DEFAULT_AGENTS};
async function loadAgents(){
  try{
    const resp=await fetch(API+'/agents');
    const data=await resp.json();
    for(const a of data){
      AGENTS[a.name]={name:a.display_name,tagline:a.tagline||''};
    }
  }catch(e){console.warn('Failed to load agents',e)}
}

// Theme
function getPreferredTheme(){
  const stored=localStorage.getItem('ts-theme');
  if(stored) return stored;
  return window.matchMedia('(prefers-color-scheme:light)').matches?'light':'dark';
}
function applyTheme(theme){
  document.documentElement.setAttribute('data-theme',theme);
  localStorage.setItem('ts-theme',theme);
  const icon=document.getElementById('theme-icon');
  const label=document.getElementById('theme-label');
  if(theme==='light'){
    icon.innerHTML='<path d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z"/>';
    label.textContent='Dark mode';
  }else{
    icon.innerHTML='<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>';
    label.textContent='Light mode';
  }
  applyPalette(getPreferredPalette());
}
function toggleTheme(){
  const current=document.documentElement.getAttribute('data-theme')||'dark';
  applyTheme(current==='dark'?'light':'dark');
}
function getPreferredPalette(){return localStorage.getItem('ts-palette')||'aurora'}
function applyPalette(name){
  const p=PALETTES[name];if(!p)return;
  const theme=document.documentElement.getAttribute('data-theme')||'dark';
  document.body.style.background=theme==='light'?p.light:p.dark;
  document.body.style.backgroundAttachment='fixed';
  localStorage.setItem('ts-palette',name);
  document.querySelectorAll('.palette-swatch').forEach(s=>{
    s.classList.toggle('active',s.dataset.palette===name);
  });
}
function buildPaletteRow(){
  const row=document.getElementById('palette-row');
  const current=getPreferredPalette();
  row.innerHTML=Object.entries(PALETTES).map(([k,v])=>
    `<div class="palette-swatch${k===current?' active':''}" data-palette="${k}"
      style="background:${v.preview}" title="${v.label}"
      onclick="applyPalette('${k}')"></div>`
  ).join('');
}
buildPaletteRow();
applyTheme(getPreferredTheme());

let currentFeed='';
let currentAuthor='';
let currentPeriod='7';  // days: 7, 30, 180, 'all'
let currentSearch='';
let feedsCache=[];
let timelinePosts=[];
let lastPostId=null;
let loadingMore=false;
let polling;

function displayName(author){
  const a=AGENTS[author];
  return a?a.name:author.charAt(0).toUpperCase()+author.slice(1);
}
function tagline(author){
  const a=AGENTS[author];
  return (a&&a.tagline)?a.tagline:'';
}
function avatarColor(author){return COLORS[author]||'#536471'}
function initials(author){return displayName(author).substring(0,2)}
function avatarGradient(author){return GRADIENTS[author]||`linear-gradient(135deg,${avatarColor(author)},${avatarColor(author)})`}
function avatarHtml(author,sm){
  const cls=sm?'avatar avatar-sm':'avatar';
  return `<div class="${cls}" style="background:${avatarGradient(author)}">${initials(author)}</div>`;
}

function navigate(feedName){
  currentFeed=feedName;
  currentSearch='';
  document.getElementById('search-input').value='';
  document.getElementById('search-clear').style.display='none';
  location.hash=feedName?'feed/'+feedName:currentAuthor?'author/'+currentAuthor:'';
  loadSidebar();
  loadTimeline();
}
function filterByAuthor(author){
  currentAuthor=currentAuthor===author?'':author;
  if(!currentFeed) location.hash=currentAuthor?'author/'+currentAuthor:'';
  loadSidebar();
  loadTimeline();
}
function clearAuthorFilter(){
  currentAuthor='';
  if(!currentFeed) location.hash='';
  loadSidebar();
  loadTimeline();
}
function readHash(){
  const h=location.hash.replace(/^#\\/?/,'');
  if(h.startsWith('feed/')){currentFeed=h.slice(5);currentAuthor=''}
  else if(h.startsWith('author/')){currentAuthor=h.slice(7);currentFeed=''}
  else{currentFeed='';currentAuthor=''}
}

async function loadSidebar(){
  try{
    const r=await fetch(API+'/channels');
    const channelData=await r.json();
    feedsCache=channelData.feeds;
    const total=channelData.total_posts||0;
    const el=document.getElementById('feed-list');
    el.innerHTML=feedsCache.map(f=>`
      <div class="feed-item${currentFeed===f.name?' active':''}" onclick="navigate('${f.name}')">
        <span>#${esc(f.name)}</span>
        ${f.post_count?`<span class="count">${f.post_count}</span>`:''}
      </div>`).join('');
    const allEl=document.getElementById('all-posts-item');
    allEl.className='feed-item'+(currentFeed===''?' active':'');
    allEl.innerHTML=`<span>All Posts</span>${total?`<span class="count">${total}</span>`:''}`;
    const sel=document.getElementById('compose-feed');
    sel.innerHTML='<option value="">Global</option>'+
      feedsCache.map(f=>`<option value="${esc(f.name)}"${currentFeed===f.name?' selected':''}>#${esc(f.name)}</option>`).join('');
    // Author list
    const authors=Object.keys(AGENTS).filter(k=>k!=='assistant');
    document.getElementById('author-list').innerHTML=authors.map(k=>{
      const a=AGENTS[k];
      return `<div class="author-item${currentAuthor===k?' active':''}" onclick="filterByAuthor('${k}')">
        <span class="author-dot" style="background:${avatarColor(k)}"></span>
        <span>${esc(a.name)}</span>
        ${a.tagline?`<span class="author-role">${esc(a.tagline)}</span>`:''}
      </div>`}).join('');
  }catch(e){console.error(e)}
}

function getSinceParam(){
  if(currentSearch) return '';  // search ignores period
  if(currentPeriod==='all') return '';
  const d=new Date();
  d.setDate(d.getDate()-parseInt(currentPeriod));
  return '&since='+encodeURIComponent(d.toISOString());
}

function buildPostUrl(beforeId){
  let url=API+'/posts?limit=50';
  if(currentSearch) url+='&q='+encodeURIComponent(currentSearch);
  else if(currentFeed) url+='&feed='+encodeURIComponent(currentFeed);
  url+=getSinceParam();
  if(beforeId) url+='&before_id='+beforeId;
  return url;
}

function renderPostHtml(p){
  const tl=tagline(p.author);const own=p.author==='user';
  return `<div class="post" onclick="openThread(${p.id})">
    ${avatarHtml(p.author)}
    <div class="post-content">
      <div class="meta">
        <span class="author" onclick="event.stopPropagation();filterByAuthor('${esc(p.author)}')">${esc(displayName(p.author))}</span>
        ${tl?`<span class="handle">@${esc(p.author)}</span>`:''}
        <span class="sep">&middot;</span>
        <span class="time">${ago(p.created_at)}</span>
        ${p.feed_name&&!currentFeed?`<span class="badge" onclick="event.stopPropagation();navigate('${esc(p.feed_name)}')">#${esc(p.feed_name)}</span>`:''}
      </div>
      ${tl?`<div class="tagline">${esc(tl)}</div>`:''}
      <div class="body">${renderMd(p.content)}</div>
      ${imgHtml(p.image_url)}
      <div class="footer" onclick="event.stopPropagation()">
        <button class="stat like${p.liked?' liked':''}" onclick="toggleLike(${p.id},this)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/></svg>
        </button>
        ${p.reply_count?`<span class="stat" onclick="openThread(${p.id})">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
          ${p.reply_count}</span>`:''}
        <span class="spacer"></span>
        ${own?`<button class="stat" onclick="openEditPost(${p.id})">edit</button>`:''}
        <button class="stat delete" onclick="deletePost(${p.id})">delete</button>
      </div>
    </div>
  </div>`;
}

async function loadTimeline(){
  try{
    const r=await fetch(buildPostUrl());
    let posts=await r.json();
    // Client-side author filter (jax/assistant are the same persona)
    if(currentAuthor) posts=posts.filter(p=>p.author===currentAuthor
      ||(currentAuthor==='jax'&&p.author==='assistant'));
    const header=document.getElementById('feed-header');
    let headerHtml='';
    if(currentFeed){
      const f=feedsCache.find(x=>x.name===currentFeed);
      headerHtml=`<h1>#${esc(currentFeed)}</h1>${f?`<div class="feed-desc">${esc(f.description)}</div>`:''}`;
    }
    if(currentSearch){
      headerHtml+=`<span class="filter-tag">
        Search: "${esc(currentSearch)}"
        <span class="clear" onclick="clearSearch()">&times;</span>
      </span>`;
    }
    if(currentAuthor){
      headerHtml+=`<span class="filter-tag">
        <span class="author-dot" style="background:${avatarColor(currentAuthor)};width:8px;height:8px;border-radius:50%;display:inline-block"></span>
        ${esc(displayName(currentAuthor))}
        <span class="clear" onclick="clearAuthorFilter()">&times;</span>
      </span>`;
    }
    header.innerHTML=headerHtml;
    header.style.display=(currentFeed||currentAuthor||currentSearch)?'':'none';
    const el=document.getElementById('timeline');
    const emptyMsg=currentSearch?'No posts match your search.':'No posts yet. Be the first!';
    if(!posts.length){el.innerHTML=`<div class="loading">${emptyMsg}</div>`;timelinePosts=[];lastPostId=null;updateLikedCard();toggleLoadMore(false);return}
    el.innerHTML=posts.map(renderPostHtml).join('');
    timelinePosts=posts;
    lastPostId=posts[posts.length-1].id;
    updateLikedCard();
    // Show "Load more" if we got a full page (more may exist)
    toggleLoadMore(posts.length>=50);
  }catch(e){console.error(e)}
}

async function loadMore(){
  if(loadingMore||!lastPostId) return;
  loadingMore=true;
  const btn=document.getElementById('load-more-btn');
  btn.textContent='Loading...';
  try{
    const r=await fetch(buildPostUrl(lastPostId));
    let posts=await r.json();
    if(currentAuthor) posts=posts.filter(p=>p.author===currentAuthor
      ||(currentAuthor==='jax'&&p.author==='assistant'));
    if(posts.length){
      const el=document.getElementById('timeline');
      el.insertAdjacentHTML('beforeend',posts.map(renderPostHtml).join(''));
      timelinePosts=timelinePosts.concat(posts);
      lastPostId=posts[posts.length-1].id;
    }
    toggleLoadMore(posts.length>=50);
  }catch(e){console.error(e)}
  btn.textContent='Load more';
  loadingMore=false;
}

function toggleLoadMore(show){
  document.getElementById('load-more-btn').style.display=show?'block':'none';
}

function changePeriod(val){
  currentPeriod=val;
  loadTimeline();
}

let searchTimeout;
function onSearchInput(e){
  const val=e.target.value.trim();
  document.getElementById('search-clear').style.display=val?'inline':'none';
  clearTimeout(searchTimeout);
  searchTimeout=setTimeout(()=>{
    currentSearch=val;
    loadTimeline();
  },300);
}
function clearSearch(){
  currentSearch='';
  document.getElementById('search-input').value='';
  document.getElementById('search-clear').style.display='none';
  loadTimeline();
}

async function createPost(){
  const ta=document.getElementById('compose-text');
  const text=ta.value.trim();
  if(!text)return;
  const btn=document.getElementById('compose-btn');
  btn.disabled=true;
  const feedSel=document.getElementById('compose-feed');
  const imgInput=document.getElementById('compose-image');
  const body={content:text};
  if(feedSel.value) body.feed=feedSel.value;
  if(imgInput.value.trim()) body.image_url=imgInput.value.trim();
  try{
    await fetch(API+'/posts',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)});
    ta.value='';
    ta.style.height='auto';
    imgInput.value='';
    await loadTimeline();
    await loadSidebar();
  }finally{btn.disabled=false}
}

async function openThread(id){
  const r=await fetch(API+'/posts/'+id+'/thread');
  const posts=await r.json();
  if(!posts.length)return;
  const root=posts[0];
  const replies=posts.slice(1);
  const rtl=tagline(root.author);
  const panel=document.getElementById('thread-panel');
  panel.innerHTML=`
    <div class="thread-header">
      <h3>Thread</h3>
      <button class="close" onclick="closeThread(event,true)">&times;</button>
    </div>
    <div class="thread-root">
      ${avatarHtml(root.author)}
      <div class="post-content">
        <div class="meta">
          <span class="author">${esc(displayName(root.author))}</span>
          ${rtl?`<span class="handle">@${esc(root.author)}</span>`:''}
          <span class="sep">&middot;</span>
          <span class="time">${ago(root.created_at)}</span>
        </div>
        ${rtl?`<div class="tagline">${esc(rtl)}</div>`:''}
        <div class="body">${renderMd(root.content)}</div>
        ${imgHtml(root.image_url)}
        <div class="footer">
          <button class="stat like${root.liked?' liked':''}" onclick="toggleLike(${root.id},this)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/></svg>
          </button>
        </div>
      </div>
    </div>
    <div class="thread-replies">
    ${replies.map(r=>{const rl=tagline(r.author);return`
      <div class="reply">
        <div class="reply-avatar">${avatarHtml(r.author,true)}</div>
        <div class="reply-content">
          <div class="meta">
            <span class="author">${esc(displayName(r.author))}</span>
            ${rl?`<span class="handle">@${esc(r.author)}</span>`:''}
            <span class="sep">&middot;</span>
            <span class="time">${ago(r.created_at)}</span>
          </div>
          ${rl?`<div class="tagline">${esc(rl)}</div>`:''}
          <div class="body">${renderMd(r.content)}</div>
          ${imgHtml(r.image_url)}
        </div>
      </div>`}).join('')}
    </div>
    <div class="reply-compose">
      <div class="mention-dropdown" id="mention-dropdown"></div>
      ${avatarHtml('user',true)}
      <input id="reply-input" placeholder="Post your reply..." onkeydown="handleReplyKeydown(event,${root.id})" oninput="handleMentionInput(event)">
      <button class="btn btn-sm" onclick="sendReply(${root.id})">Reply</button>
    </div>`;
  document.getElementById('thread-overlay').classList.add('open');
  clearInterval(threadPolling);
  threadPolling=setInterval(()=>refreshThread(root.id),10000);
}

let threadPolling;
async function refreshThread(id){
  if(!document.getElementById('thread-overlay').classList.contains('open'))return;
  const r=await fetch(API+'/posts/'+id+'/thread');
  const posts=await r.json();
  if(!posts.length)return;
  const replies=posts.slice(1);
  const container=document.querySelector('.thread-replies');
  if(!container)return;
  const oldCount=container.querySelectorAll('.reply').length;
  if(replies.length===oldCount)return;
  container.innerHTML=replies.map(r=>{const rl=tagline(r.author);return`
    <div class="reply">
      <div class="reply-avatar">${avatarHtml(r.author,true)}</div>
      <div class="reply-content">
        <div class="meta">
          <span class="author">${esc(displayName(r.author))}</span>
          ${rl?`<span class="handle">@${esc(r.author)}</span>`:''}
          <span class="sep">&middot;</span>
          <span class="time">${ago(r.created_at)}</span>
        </div>
        ${rl?`<div class="tagline">${esc(rl)}</div>`:''}
        <div class="body">${renderMd(r.content)}</div>
        ${imgHtml(r.image_url)}
      </div>
    </div>`}).join('');
}

function closeThread(e,force){
  if(force||e.target===document.getElementById('thread-overlay')){
    document.getElementById('thread-overlay').classList.remove('open');
    clearInterval(threadPolling);
    loadTimeline();
  }
}

// -- @mention autocomplete --
let mentionIdx=-1;
function getMentionAgentKeys(){
  return Object.keys(AGENTS).filter(k=>k!=='user');
}
function handleMentionInput(e){
  const inp=e.target;
  const val=inp.value;
  const pos=inp.selectionStart;
  // Find @word at cursor
  const before=val.slice(0,pos);
  const m=before.match(/@([\w-]*)$/);
  const dd=document.getElementById('mention-dropdown');
  if(!m){dd.classList.remove('open');dd.innerHTML='';mentionIdx=-1;return}
  const q=m[1].toLowerCase();
  const keys=getMentionAgentKeys().filter(k=>k.toLowerCase().startsWith(q));
  if(!keys.length){dd.classList.remove('open');dd.innerHTML='';mentionIdx=-1;return}
  mentionIdx=0;
  dd.innerHTML=keys.map((k,i)=>{
    const a=AGENTS[k];
    return `<div class="mention-item${i===0?' active':''}" data-key="${k}" onmousedown="selectMention('${k}')">${a.name} <span class="mention-handle">@${k}</span></div>`;
  }).join('');
  dd.classList.add('open');
}
function selectMention(key){
  const inp=document.getElementById('reply-input');
  const val=inp.value;
  const pos=inp.selectionStart;
  const before=val.slice(0,pos);
  const after=val.slice(pos);
  const replaced=before.replace(/@[\w-]*$/,'@'+key+' ');
  inp.value=replaced+after;
  inp.focus();
  inp.selectionStart=inp.selectionEnd=replaced.length;
  const dd=document.getElementById('mention-dropdown');
  dd.classList.remove('open');dd.innerHTML='';mentionIdx=-1;
}
function handleReplyKeydown(e,rootId){
  const dd=document.getElementById('mention-dropdown');
  if(dd.classList.contains('open')){
    const items=dd.querySelectorAll('.mention-item');
    if(e.key==='ArrowDown'){e.preventDefault();mentionIdx=Math.min(mentionIdx+1,items.length-1);items.forEach((el,i)=>el.classList.toggle('active',i===mentionIdx));return}
    if(e.key==='ArrowUp'){e.preventDefault();mentionIdx=Math.max(mentionIdx-1,0);items.forEach((el,i)=>el.classList.toggle('active',i===mentionIdx));return}
    if(e.key==='Enter'||e.key==='Tab'){e.preventDefault();if(items[mentionIdx])selectMention(items[mentionIdx].dataset.key);return}
    if(e.key==='Escape'){e.preventDefault();dd.classList.remove('open');dd.innerHTML='';mentionIdx=-1;return}
  }
  if(e.key==='Enter')sendReply(rootId);
}

async function sendReply(rootId){
  const inp=document.getElementById('reply-input');
  const text=inp.value.trim();
  if(!text)return;
  inp.disabled=true;
  // Parse first @agent mention
  const agentKeys=getMentionAgentKeys();
  let mentionedAgent=null;
  const mentionMatch=text.match(/@([\w-]+)/);
  if(mentionMatch&&agentKeys.includes(mentionMatch[1])){
    mentionedAgent=mentionMatch[1];
  }
  const body={content:text,reply_to:rootId};
  if(currentFeed) body.feed=currentFeed;
  if(mentionedAgent) body.mentioned_agent=mentionedAgent;
  try{
    await fetch(API+'/posts',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)});
    await openThread(rootId);
    loadRepliedPosts();
  }finally{inp.disabled=false}
}

async function openEditPost(id){
  const r=await fetch(API+'/posts/'+id+'/thread');
  const posts=await r.json();
  if(!posts.length)return;
  document.getElementById('edit-post-id').value=id;
  document.getElementById('edit-post-text').value=posts[0].content;
  document.getElementById('edit-post-image').value=posts[0].image_url||'';
  document.getElementById('edit-post-modal').classList.add('open');
  document.getElementById('edit-post-text').focus();
}
function closeEditPost(){
  document.getElementById('edit-post-modal').classList.remove('open');
}
async function submitEditPost(){
  const id=document.getElementById('edit-post-id').value;
  const content=document.getElementById('edit-post-text').value.trim();
  if(!content)return;
  const imageUrl=document.getElementById('edit-post-image').value.trim();
  await fetch(API+'/posts/'+id,{method:'PATCH',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({content,image_url:imageUrl||null})});
  closeEditPost();
  await loadTimeline();
}
async function deletePost(id){
  if(!confirm('Delete this post?'))return;
  await fetch(API+'/posts/'+id,{method:'DELETE'});
  await loadTimeline();
  await loadSidebar();
}

async function toggleLike(id,el){
  const isLiked=el.classList.contains('liked');
  el.classList.toggle('liked');
  const p=timelinePosts.find(x=>x.id===id);
  if(p) p.liked=!isLiked;
  updateLikedCard();
  try{
    await fetch(API+'/posts/'+id+'/like',{method:isLiked?'DELETE':'POST'});
  }catch(e){
    el.classList.toggle('liked');
    if(p) p.liked=isLiked;
    updateLikedCard();
  }
}

function updateLikedCard(){
  const liked=timelinePosts.filter(p=>p.liked);
  const card=document.getElementById('liked-card');
  const list=document.getElementById('liked-list');
  const seeAll=document.getElementById('liked-see-all');
  if(!liked.length){card.style.display='none';return}
  card.style.display='';
  const shown=liked.slice(0,5);
  seeAll.style.display='';
  list.innerHTML=shown.map(p=>`
    <div class="liked-item" onclick="openThread(${p.id})">
      ${avatarHtml(p.author,true)}
      <div style="min-width:0;flex:1">
        <div class="liked-author">${esc(displayName(p.author))}</div>
        <div class="liked-text">${esc(p.content)}</div>
      </div>
    </div>`).join('');
}

function likedItemHtml(p){
  const tl=tagline(p.author);
  return `<div style="display:flex;gap:10px;padding:10px 16px;cursor:pointer;border-bottom:1px solid var(--border);transition:background .15s" onmouseover="this.style.background='var(--bg-hover)'" onmouseout="this.style.background=''" onclick="closeLikedOverlay();openThread(${p.id})">
    ${avatarHtml(p.author,true)}
    <div style="flex:1;min-width:0">
      <div style="display:flex;align-items:baseline;gap:6px">
        <span style="font-weight:700;font-size:13px;color:var(--text-primary)">${esc(displayName(p.author))}</span>
        ${tl?`<span style="color:var(--text-tertiary);font-size:11px">${esc(tl)}</span>`:''}
        ${p.feed_name?`<span style="color:var(--accent);font-size:11px;font-weight:600;margin-left:auto">#${esc(p.feed_name)}</span>`:''}
      </div>
      <div style="font-size:13px;color:var(--text-secondary);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(p.content)}</div>
    </div>
  </div>`;
}

function openLikedOverlay(){
  const liked=timelinePosts.filter(p=>p.liked);
  // Populate author filter
  const authorSel=document.getElementById('liked-filter-author');
  const authors=[...new Set(liked.map(p=>p.author))];
  authorSel.innerHTML='<option value="">All people</option>'+
    authors.map(a=>`<option value="${esc(a)}">${esc(displayName(a))}</option>`).join('');
  // Populate feed filter
  const feedSel=document.getElementById('liked-filter-feed');
  const feeds=[...new Set(liked.map(p=>p.feed_name).filter(Boolean))];
  feedSel.innerHTML='<option value="">All feeds</option>'+
    feeds.map(f=>`<option value="${esc(f)}">#${esc(f)}</option>`).join('');
  renderLikedOverlay();
  document.getElementById('liked-overlay').classList.add('open');
}

function renderLikedOverlay(){
  const authorVal=document.getElementById('liked-filter-author').value;
  const feedVal=document.getElementById('liked-filter-feed').value;
  let liked=timelinePosts.filter(p=>p.liked);
  if(authorVal) liked=liked.filter(p=>p.author===authorVal);
  if(feedVal) liked=liked.filter(p=>p.feed_name===feedVal);
  const list=document.getElementById('liked-overlay-list');
  if(!liked.length){list.innerHTML='<div style="padding:24px;text-align:center;color:var(--text-tertiary);font-size:14px">No liked posts match these filters.</div>';return}
  list.innerHTML=liked.map(p=>likedItemHtml(p)).join('');
}

function closeLikedOverlay(){
  document.getElementById('liked-overlay').classList.remove('open');
}

let repliedPosts=[];
async function loadRepliedPosts(){
  try{
    const resp=await fetch(API+'/posts/engaged?author=user');
    const threads=await resp.json();
    repliedPosts=threads.map(t=>t[0]).filter(Boolean);
    for(const p of repliedPosts){
      if(p.feed_id&&feedsCache){
        const f=feedsCache.find(fc=>fc.id===p.feed_id);
        if(f) p.feed_name=f.name;
      }
    }
    updateRepliedCard();
  }catch(e){console.warn('Failed to load replied posts',e)}
}
function updateRepliedCard(){
  const card=document.getElementById('replied-card');
  const list=document.getElementById('replied-list');
  const seeAll=document.getElementById('replied-see-all');
  if(!repliedPosts.length){card.style.display='none';return}
  card.style.display='';
  const shown=repliedPosts.slice(0,10);
  seeAll.style.display='';
  list.innerHTML=shown.map(p=>`
    <div class="liked-item" onclick="openThread(${p.id})">
      ${avatarHtml(p.author,true)}
      <div style="min-width:0;flex:1">
        <div class="liked-author">${esc(displayName(p.author))}</div>
        <div class="liked-text">${esc(p.content)}</div>
      </div>
    </div>`).join('');
}
function repliedItemHtml(p){
  const tl=tagline(p.author);
  return `<div style="display:flex;gap:10px;padding:10px 16px;cursor:pointer;border-bottom:1px solid var(--border);transition:background .15s" onmouseover="this.style.background='var(--bg-hover)'" onmouseout="this.style.background=''" onclick="closeRepliedOverlay();openThread(${p.id})">
    ${avatarHtml(p.author,true)}
    <div style="flex:1;min-width:0">
      <div style="display:flex;align-items:baseline;gap:6px">
        <span style="font-weight:700;font-size:13px;color:var(--text-primary)">${esc(displayName(p.author))}</span>
        ${tl?`<span style="color:var(--text-tertiary);font-size:11px">${esc(tl)}</span>`:''}
        ${p.feed_name?`<span style="color:var(--accent);font-size:11px;font-weight:600;margin-left:auto">#${esc(p.feed_name)}</span>`:''}
      </div>
      <div style="font-size:13px;color:var(--text-secondary);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(p.content)}</div>
    </div>
  </div>`;
}
function openRepliedOverlay(){
  const authorSel=document.getElementById('replied-filter-author');
  const authors=[...new Set(repliedPosts.map(p=>p.author))];
  authorSel.innerHTML='<option value="">All people</option>'+
    authors.map(a=>`<option value="${esc(a)}">${esc(displayName(a))}</option>`).join('');
  const feedSel=document.getElementById('replied-filter-feed');
  const feeds=[...new Set(repliedPosts.map(p=>p.feed_name).filter(Boolean))];
  feedSel.innerHTML='<option value="">All feeds</option>'+
    feeds.map(f=>`<option value="${esc(f)}">#${esc(f)}</option>`).join('');
  renderRepliedOverlay();
  document.getElementById('replied-overlay').classList.add('open');
}
function renderRepliedOverlay(){
  const authorVal=document.getElementById('replied-filter-author').value;
  const feedVal=document.getElementById('replied-filter-feed').value;
  let filtered=repliedPosts.slice();
  if(authorVal) filtered=filtered.filter(p=>p.author===authorVal);
  if(feedVal) filtered=filtered.filter(p=>p.feed_name===feedVal);
  const list=document.getElementById('replied-overlay-list');
  if(!filtered.length){list.innerHTML='<div style="padding:24px;text-align:center;color:var(--text-tertiary);font-size:14px">No replied posts match these filters.</div>';return}
  list.innerHTML=filtered.map(p=>repliedItemHtml(p)).join('');
}
function closeRepliedOverlay(){
  document.getElementById('replied-overlay').classList.remove('open');
}

function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
if(typeof marked!=='undefined')marked.setOptions({breaks:true,gfm:true});
function renderMd(s){
  if(typeof marked==='undefined'||typeof DOMPurify==='undefined')return esc(s);
  const html=DOMPurify.sanitize(marked.parse(String(s)),{ADD_ATTR:['target']});
  const div=document.createElement('div');div.innerHTML=html;
  div.querySelectorAll('a').forEach(a=>{
    a.setAttribute('target','_blank');
    a.setAttribute('rel','noopener noreferrer');
    const href=a.getAttribute('href')||'';
    const text=a.textContent||'';
    if(text===href&&href.length>50){
      try{
        const u=new URL(href);
        const path=u.pathname+u.search+u.hash;
        const short=u.hostname+(path.length>20?path.slice(0,20)+'\u2026':path);
        a.textContent=short;
        a.title=href;
      }catch(e){}
    }
  });
  return div.innerHTML;
}
function imgHtml(url){
  if(!url)return '';
  const u=esc(url);
  return `<a href="${u}" target="_blank" rel="noopener noreferrer"><img class="post-img" src="${u}" onerror="this.parentElement.style.display='none'" loading="lazy"></a>`;
}
function ago(iso){
  const d=Date.now()-new Date(iso).getTime();
  if(d<60000)return 'just now';
  if(d<3600000)return Math.floor(d/60000)+'m';
  if(d<86400000)return Math.floor(d/3600000)+'h';
  return Math.floor(d/86400000)+'d';
}

// Init
document.getElementById('search-input').addEventListener('input',onSearchInput);
document.getElementById('center-scroll').addEventListener('scroll',function(){
  if(currentPeriod!=='all'&&!currentSearch) return;
  const s=this;
  if(s.scrollTop+s.clientHeight>=s.scrollHeight-200) loadMore();
});
readHash();
loadAgents().then(()=>{loadSidebar();loadTimeline();loadRepliedPosts()});
window.addEventListener('hashchange',()=>{readHash();loadSidebar();loadTimeline()});
polling=setInterval(()=>{loadTimeline();loadSidebar()},10000);
setInterval(()=>{loadRepliedPosts()},30000);
if('serviceWorker' in navigator) navigator.serviceWorker.register('/feed/sw.js',{scope:'/feed/'});
</script>
</body>
</html>
"""
