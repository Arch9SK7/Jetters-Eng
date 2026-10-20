"use strict";
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const hex = (v, n = 8) => '0x' + (v >>> 0).toString(16).toUpperCase().padStart(n, '0');

async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} :
    {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  const j = await r.json();
  if (!r.ok || j.error) throw new Error(j.error || ('HTTP ' + r.status));
  return j;
}
function log(text, ok = true) {
  const el = $('#log');
  el.textContent += (el.textContent ? '\n' : '') + String(text).trim();
  el.scrollTop = 1e9;
  const last = String(text).trim().split('\n').pop();
  $('#logLast').textContent = last;
  $('#logLast').style.color = ok ? '' : 'var(--bad)';
  if (!ok) openLog(true);
}
function openLog(v) { $('#log').classList.toggle('open', v); $('#logArrow').innerHTML = v ? '&#9662;' : '&#9656;'; }
$('#logbar').onclick = () => openLog(!$('#log').classList.contains('open'));
async function act(fn) { try { return await fn(); } catch (e) { log(e.message, false); } }
function store(k, v) { try { if (v === undefined) return localStorage.getItem('jse.' + k); localStorage.setItem('jse.' + k, v); } catch (e) { return null; } }
function loadImage(src) { return new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = src; }); }
function checker(ctx, w, h, z) {
  for (let y = 0; y < h; y += 8) for (let x = 0; x < w; x += 8) {
    ctx.fillStyle = ((x + y) / 8) % 2 ? '#2a2f3a' : '#232731'; ctx.fillRect(x * z, y * z, 8 * z, 8 * z);
  }
}

const App = {
  state: null, view: 'sprites', views: {},
  register(name, v) { this.views[name] = v; },
  dirtyChanged() {
    document.querySelectorAll('#tabs button').forEach(b => {
      const v = this.views[b.dataset.view];
      b.querySelector('.dot').hidden = !(v && v.isDirty());
    });
  },
  anyDirty() { return Object.values(this.views).some(v => v.isDirty()); },
  async saveAll() { for (const v of Object.values(this.views)) if (v.isDirty()) await v.save(); },
  show(name) {
    this.view = name; store('view', name);
    document.querySelectorAll('#tabs button').forEach(b => b.classList.toggle('active', b.dataset.view === name));
    document.querySelectorAll('.view').forEach(s => s.classList.toggle('active', s.id === 'v-' + name));
    const v = this.views[name]; if (v && v.shown) v.shown();
  },
  async start() {
    try {
      this.state = await api('/api/state');
    } catch (e) { log(e.message, false); return; }
    $('#batBtn').disabled = $('#buildTestBtn').disabled = !this.state.windows;
    if (!this.state.windows) $('#batBtn').title = $('#buildTestBtn').title = 'build.bat only runs on Windows';
    document.querySelectorAll('#tabs button').forEach(b => b.onclick = () => this.show(b.dataset.view));
    for (const v of Object.values(this.views)) await act(() => v.init(this.state));
    this.show(store('view') || 'sprites');
  },
};

window.addEventListener('beforeunload', e => { if (App.anyDirty()) { e.preventDefault(); e.returnValue = ''; } });
window.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault(); const v = App.views[App.view]; if (v) act(() => v.save());
    return;
  }
  const v = App.views[App.view]; if (v && v.key) v.key(e);
});

async function runBuild(test) {
  await App.saveAll();
  const btn = test ? $('#buildTestBtn') : $('#batBtn'), label = btn.innerHTML;
  btn.disabled = true; btn.textContent = 'Building...';
  try {
    const r = await api(test ? '/api/buildtest' : '/api/buildbat', {});
    log(r.log, r.ok); openLog(true);
    if (!r.ok) log('Build failed - read the output above (the first error is usually the real one).', false);
  } finally { btn.disabled = false; btn.innerHTML = label; }
}
$('#buildTestBtn').onclick = () => act(() => runBuild(true));
$('#batBtn').onclick = () => act(() => runBuild(false));
$('#romBtn').onclick = () => act(async () => log((await api('/api/launch', {})).log));
$('#settingsBtn').onclick = () => { $('#setEmu').value = (App.state.settings || {}).emulator || ''; $('#setDlg').showModal(); };
$('#setCancel').onclick = () => $('#setDlg').close();
$('#setOk').onclick = () => act(async () => {
  const r = await api('/api/settings', {emulator: $('#setEmu').value.trim()});
  App.state.settings = r.settings; log(r.log); $('#setDlg').close();
});
