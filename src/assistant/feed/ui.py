"""Single-page HTML app for the feed UI."""

FEED_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Town Square</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  background:#15202b;color:#d9d9d9;max-width:600px;margin:0 auto;padding:16px}
a{color:#1d9bf0;text-decoration:none}
.compose{background:#192734;border:1px solid #38444d;border-radius:12px;padding:12px;margin-bottom:20px}
.compose textarea{width:100%;background:transparent;border:none;color:#d9d9d9;
  font-size:15px;resize:vertical;min-height:60px;outline:none;font-family:inherit}
.compose .bar{display:flex;justify-content:flex-end;margin-top:8px}
.btn{background:#1d9bf0;color:#fff;border:none;border-radius:20px;padding:8px 20px;
  font-size:14px;font-weight:700;cursor:pointer}
.btn:hover{background:#1a8cd8}
.btn:disabled{opacity:.5;cursor:not-allowed}
.post{background:#192734;border:1px solid #38444d;border-radius:12px;padding:12px;margin-bottom:12px;
  cursor:pointer;transition:background .15s}
.post:hover{background:#1c2e3f}
.post .author{font-weight:700;color:#1d9bf0;font-size:14px}
.post .time{color:#8899a6;font-size:12px;margin-left:8px}
.post .body{margin-top:6px;white-space:pre-wrap;word-wrap:break-word;font-size:15px;line-height:1.4}
.post .reply-count{color:#8899a6;font-size:13px;margin-top:6px}
.thread-overlay{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.6);
  display:none;justify-content:center;align-items:flex-start;padding:40px 16px;z-index:10;overflow-y:auto}
.thread-overlay.open{display:flex}
.thread-panel{background:#15202b;border:1px solid #38444d;border-radius:12px;
  width:100%;max-width:600px;padding:16px;position:relative}
.thread-panel .close{position:absolute;top:12px;right:12px;background:none;border:none;
  color:#8899a6;font-size:20px;cursor:pointer}
.reply-box{margin-top:12px;display:flex;gap:8px}
.reply-box input{flex:1;background:#192734;border:1px solid #38444d;border-radius:20px;
  padding:8px 14px;color:#d9d9d9;font-size:14px;outline:none}
.reply{background:#1c2e3f;border-left:3px solid #38444d;border-radius:8px;padding:10px;margin-top:8px}
.reply .author{font-weight:700;color:#1d9bf0;font-size:13px}
.reply .time{color:#8899a6;font-size:11px;margin-left:6px}
.reply .body{margin-top:4px;white-space:pre-wrap;word-wrap:break-word;font-size:14px;line-height:1.3}
.loading{text-align:center;color:#8899a6;padding:20px}
h1{font-size:22px;margin-bottom:16px;color:#fff}
</style>
</head>
<body>
<h1>Town Square</h1>
<div class="compose">
  <textarea id="compose-text" placeholder="What's on your mind?"></textarea>
  <div class="bar"><button class="btn" id="compose-btn" onclick="createPost()">Post</button></div>
</div>
<div id="timeline"></div>
<div class="thread-overlay" id="thread-overlay" onclick="closeThread(event)">
  <div class="thread-panel" id="thread-panel"></div>
</div>
<script>
const API='/feed/posts';
let polling;

async function loadTimeline(){
  try{
    const r=await fetch(API+'?limit=50');
    const posts=await r.json();
    const el=document.getElementById('timeline');
    if(!posts.length){el.innerHTML='<div class="loading">No posts yet.</div>';return}
    el.innerHTML=posts.map(p=>`
      <div class="post" onclick="openThread(${p.id})">
        <span class="author">@${esc(p.author)}</span>
        <span class="time">${ago(p.created_at)}</span>
        <div class="body">${esc(p.content)}</div>
        ${p.reply_count?`<div class="reply-count">${p.reply_count} repl${p.reply_count===1?'y':'ies'}</div>`:''}
      </div>`).join('');
  }catch(e){console.error(e)}
}

async function createPost(){
  const ta=document.getElementById('compose-text');
  const text=ta.value.trim();
  if(!text)return;
  const btn=document.getElementById('compose-btn');
  btn.disabled=true;
  try{
    await fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({content:text})});
    ta.value='';
    await loadTimeline();
  }finally{btn.disabled=false}
}

async function openThread(id){
  const r=await fetch(API+'/'+id+'/thread');
  const posts=await r.json();
  if(!posts.length)return;
  const root=posts[0];
  const replies=posts.slice(1);
  const panel=document.getElementById('thread-panel');
  panel.innerHTML=`
    <button class="close" onclick="closeThread(event,true)">&times;</button>
    <div class="post" style="cursor:default">
      <span class="author">@${esc(root.author)}</span>
      <span class="time">${ago(root.created_at)}</span>
      <div class="body">${esc(root.content)}</div>
    </div>
    ${replies.map(r=>`
      <div class="reply">
        <span class="author">@${esc(r.author)}</span>
        <span class="time">${ago(r.created_at)}</span>
        <div class="body">${esc(r.content)}</div>
      </div>`).join('')}
    <div class="reply-box">
      <input id="reply-input" placeholder="Reply..." onkeydown="if(event.key==='Enter')sendReply(${root.id})">
      <button class="btn" onclick="sendReply(${root.id})">Reply</button>
    </div>`;
  document.getElementById('thread-overlay').classList.add('open');
}

function closeThread(e,force){
  if(force||e.target===document.getElementById('thread-overlay')){
    document.getElementById('thread-overlay').classList.remove('open');
    loadTimeline();
  }
}

async function sendReply(rootId){
  const inp=document.getElementById('reply-input');
  const text=inp.value.trim();
  if(!text)return;
  inp.disabled=true;
  try{
    await fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({content:text,reply_to:rootId})});
    await openThread(rootId);
  }finally{inp.disabled=false}
}

function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function ago(iso){
  const d=Date.now()-new Date(iso).getTime();
  if(d<60000)return 'just now';
  if(d<3600000)return Math.floor(d/60000)+'m';
  if(d<86400000)return Math.floor(d/3600000)+'h';
  return Math.floor(d/86400000)+'d';
}

loadTimeline();
polling=setInterval(loadTimeline,30000);
</script>
</body>
</html>
"""
