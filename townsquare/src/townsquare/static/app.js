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
  const h=location.hash.replace(/^#\/?/,'');
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
  // Convert @agent mentions into clickable links
  const agentKeys=getMentionAgentKeys();
  if(agentKeys.length){
    const mentionRe=new RegExp('@('+agentKeys.map(k=>k.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('|')+')\\b','g');
    const walker=document.createTreeWalker(div,NodeFilter.SHOW_TEXT);
    const textNodes=[];
    while(walker.nextNode()) textNodes.push(walker.currentNode);
    textNodes.forEach(node=>{
      if(node.parentElement&&node.parentElement.closest('a'))return;
      const txt=node.textContent;
      if(!mentionRe.test(txt))return;
      mentionRe.lastIndex=0;
      const frag=document.createDocumentFragment();
      let last=0;
      let match;
      while((match=mentionRe.exec(txt))!==null){
        if(match.index>last) frag.appendChild(document.createTextNode(txt.slice(last,match.index)));
        const a=document.createElement('a');
        a.href='#author/'+match[1];
        a.className='mention-link';
        a.textContent='@'+match[1];
        frag.appendChild(a);
        last=mentionRe.lastIndex;
      }
      if(last<txt.length) frag.appendChild(document.createTextNode(txt.slice(last)));
      node.parentNode.replaceChild(frag,node);
    });
  }
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
