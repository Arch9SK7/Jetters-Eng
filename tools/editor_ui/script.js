"use strict";
// ============================================================ Script view
(function () {
const T = {meta: null, files: [], file: null, blocks: [], sel: -1, edits: {}, font: null, fontVar: null, issues: {}};
const SCALE = 3;
const END_TAGS = new Set(['<END>', '<CLOSE>', '<NEXT>', '<PAUSE>', '<E01F_CLEAR>']);
const PROMPTS = new Set(['<PROMPT_YES>', '<PROMPT_NO>', '<PROMPT_SWAP_NO>', '<PROMPT_SWAP_YES>', '<PROMPT_3>']);
const NUMS = {'<NUMBER0>': '999', '<NUMBER1>': '999', '<NUMBER2>': '999', '<NUMBER1_2DIGIT>': '99', '<NUMBER2_2DIGIT>': '99'};
const PLACES = {'<PLACE>': 'PLACE', '<WORLD>': 'WORLD', '<PLANET>': 'PLANET'};

async function init() {
  T.meta = await api('/api/script/meta');
  const b = T.meta.box;
  $('#sBoxW').value = store('boxW') || b.width; $('#sBoxR').value = store('boxR') || b.rows;
  if (T.meta.fontOk) {
    const img = await loadImage('/api/png?path=' + encodeURIComponent(T.meta.font));
    T.font = tint(img, null); T.fontVar = tint(img, '#ffd84d'); T.fontBad = tint(img, '#ff8a95');
  } else log('Font not found (' + T.meta.font + ') - preview uses boxes', false);
  await loadFiles();
  const f = store('scriptFile');
  const pick = T.files.find(x => x.name === f) || T.files[0];
  if (pick) await loadFile(pick.name);
}
function tint(img, color) {
  const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
  const g = c.getContext('2d'); g.drawImage(img, 0, 0);
  if (color) { g.globalCompositeOperation = 'source-in'; g.fillStyle = color; g.fillRect(0, 0, c.width, c.height); }
  return c;
}
async function loadFiles() {
  T.files = await api('/api/script/files');
  renderFiles();
}
function renderFiles() {
  $('#sFiles').innerHTML = T.files.map(f => {
    const pct = f.room ? Math.min(100, Math.round(f.size / f.room * 100)) : 0;
    const col = f.overlap ? 'var(--bad)' : pct > 90 ? 'var(--warn)' : 'var(--ok)';
    return `<div class="it ${T.file && T.file.name === f.name ? 'cur' : ''}" data-n="${f.name}">
      <div class="row" style="margin:0;justify-content:space-between"><b>${f.name.replace('jetters_', '').replace('.txt', '')}</b>
      <span class="muted">${f.strings} strings</span></div>
      <div class="help">${esc(f.title || '')}</div>
      ${f.room ? `<div class="meter" title="${f.size} of ${f.room} bytes"><i style="width:${pct}%;background:${col}"></i></div>` : ''}
      ${f.overlap ? '<div class="bad" style="font-size:11px">Overlaps the next file!</div>' : ''}
      ${f.unknown.length ? `<div class="mod" style="font-size:11px">Not in table: ${esc(f.unknown.join(' '))}</div>` : ''}
    </div>`;
  }).join('');
  $('#sFiles').querySelectorAll('.it').forEach(el => el.onclick = () => {
    if (isDirty() && !confirm('You have unsaved script changes in ' + T.file.name + '. Discard them?')) return;
    act(() => loadFile(el.dataset.n));
  });
}
async function loadFile(name, keepSel) {
  const d = await api('/api/script/file?name=' + encodeURIComponent(name));
  T.file = d; T.blocks = d.blocks; T.edits = {}; if (!keepSel) T.sel = -1;
  store('scriptFile', name); setStatus(); renderFiles();
  T.issues = {}; T.blocks.forEach(b => T.issues[b.i] = layout(b.text).issues);
  renderStrings();
  if (T.sel < 0 && T.blocks.length) select(0); else select(T.sel);
}
const textOf = b => T.edits[b.i] !== undefined ? T.edits[b.i] : b.text;
function isDirty() { return Object.keys(T.edits).some(i => T.edits[i] !== T.blocks[i].text); }
function setStatus() { const d = isDirty(), s = $('#sStatus'); s.textContent = d ? 'Unsaved changes' : (T.file ? 'Saved' : '-'); s.className = 'status' + (d ? ' dirty' : ''); App.dirtyChanged(); }

function renderStrings() {
  const q = $('#sSearch').value.trim().toLowerCase(), bad = $('#sOnlyBad').checked;
  let shown = 0, nbad = 0;
  const html = T.blocks.map(b => {
    const iss = T.issues[b.i] || [], txt = textOf(b);
    if (iss.length) nbad++;
    if (bad && !iss.length) return '';
    if (q && !txt.toLowerCase().includes(q) && !('$' + b.ptr.toString(16)).includes(q)) return '';
    shown++;
    const first = txt.split('\n').map(l => l.trim()).find(l => l && !l.startsWith('//')) || '';
    const prev = first.replace(/<\$[0-9A-Fa-f]{2}>/g, '').replace(/<[^<>]+>/g, ' ').trim() || first;
    const mod = T.edits[b.i] !== undefined && T.edits[b.i] !== b.text;
    return `<div class="it ${b.i === T.sel ? 'cur' : ''}" data-i="${b.i}"><span class="n">${b.i}</span><span class="t">${mod ? '<span class="mod">&#9679;</span> ' : ''}${esc(prev)}</span>${iss.length ? `<span class="badge">${iss.length}</span>` : ''}</div>`;
  }).join('');
  $('#sStrings').innerHTML = html;
  $('#sCount').textContent = `${shown} of ${T.blocks.length} strings` + (nbad ? ` - ${nbad} with problems` : ' - no problems found');
  $('#sStrings').querySelectorAll('.it').forEach(el => el.onclick = () => select(+el.dataset.i));
}
function select(i) {
  T.sel = i; const b = T.blocks[i];
  $('#sStrings').querySelectorAll('.it').forEach(el => el.classList.toggle('cur', +el.dataset.i === i));
  if (!b) { $('#sEdit').value = ''; $('#sPages').innerHTML = ''; $('#sHead').innerHTML = ''; return; }
  $('#sHead').innerHTML = `<b>${esc(T.file.name)}</b> <span class="muted">string #${b.i} &middot; pointer $${b.ptr.toString(16).toUpperCase()} &middot; line ${b.line}</span>`;
  $('#sEdit').value = textOf(b);
  preview();
}
$('#sEdit').addEventListener('input', () => {
  const b = T.blocks[T.sel]; if (!b) return;
  T.edits[b.i] = $('#sEdit').value;
  T.issues[b.i] = layout(T.edits[b.i]).issues;
  preview(); setStatus();
  const el = $(`#sStrings .it[data-i="${b.i}"]`);
  if (el) { const iss = T.issues[b.i]; const bd = el.querySelector('.badge');
    if (iss.length) { if (bd) bd.textContent = iss.length; else el.insertAdjacentHTML('beforeend', `<span class="badge">${iss.length}</span>`); } else if (bd) bd.remove(); }
});
$('#sRevertBtn').onclick = () => { const b = T.blocks[T.sel]; if (!b) return; delete T.edits[b.i]; T.issues[b.i] = layout(b.text).issues; select(b.i); renderStrings(); setStatus(); };

// ----------------------------------------------------------------- layout shit
function box() { return {width: +$('#sBoxW').value || 184, rows: +$('#sBoxR').value || 3, lineStep: T.meta.box.lineStep, halfStep: T.meta.box.halfStep}; }
function layout(text) {
  const bx = box(), W = T.meta.widths, chars = T.meta.chars, tags = T.meta.tags;
  const body = text.split('\n').filter(l => { const s = l.trim(); return !s.startsWith('//') && !s.startsWith('#'); }).join('');
  const toks = body.match(/<\$[0-9A-Fa-f]{2}>|<[^<>]+>|[\s\S]/g) || [];
  const pages = []; let pg = null, x = 0, y = 0, pending = null, rawTitle = null;
  const newPg = () => { pg = {glyphs: [], rows: {}, notes: [], title: null, end: '', unknown: []}; x = 0; y = 0; };
  const flush = end => { if (pg.glyphs.length || pg.title || pg.notes.length) { pg.end = end; pages.push(pg); } newPg(); };
  const put = (code, v) => { const w = W[code] === undefined ? 8 : W[code]; pg.glyphs.push({code, x, y, v}); x += w; pg.rows[y] = Math.max(pg.rows[y] || 0, x); };
  const putText = (s, v) => { for (const c of s) { const code = chars[c]; if (code === undefined) { pg.unknown.push(c); put(-1, 'bad'); } else put(code, v); } };
  newPg();
  for (const t of toks) {
    if (rawTitle) { if (t.startsWith('<$')) { rawTitle.left--; } else { rawTitle.s += t; rawTitle.left--; }
      if (rawTitle.left <= 0) { pg.title = rawTitle.s; rawTitle = null; } continue; }
    if (t.startsWith('<$')) {
      const v = parseInt(t.slice(2, 4), 16);
      if (pending === 'name') putText(T.meta.names[v] !== undefined ? T.meta.names[v] : `[item ${v}]`, 'var');
      else if (pending === 'card') pg.title = 'name card #' + v;
      else if (pending === 'raw') { if (v > 0) rawTitle = {s: '', left: v}; }
      pending = null; continue;
    }
    pending = null;
    if (t === '<LINE>') { y += bx.lineStep; x = 0; continue; }
    if (t === '<HALF>') { y += bx.halfStep; x = 0; continue; }
    if (t === '<WAIT>') { flush('A'); continue; }
    if (END_TAGS.has(t)) { flush(t.slice(1, -1)); continue; }
    if (t === '<NAME>') { pending = 'name'; continue; }
    if (t === '<NAME_CARD>' || t === '<NAME_CARD_KARABON>') { pending = 'card'; continue; }
    if (t === '<NAME_CARD_RAW>') { pending = 'raw'; continue; }
    if (NUMS[t]) { putText(NUMS[t], 'var'); continue; }
    if (PLACES[t]) { putText(PLACES[t], 'var'); continue; }
    if (PROMPTS.has(t)) { pg.notes.push('Yes/No prompt'); continue; }
    if (t.length > 1 && t.startsWith('<')) { if (tags[t] !== undefined) put(tags[t]); continue; }
    if (t === '\r') continue;
    const code = chars[t];
    if (code === undefined) { pg.unknown.push(t); put(-1, 'bad'); } else put(code);
  }
  flush('');
  const issues = [];
  pages.forEach((p, n) => {
    p.issues = [];
    const ys = Object.keys(p.rows).map(Number).sort((a, b) => a - b);
    ys.forEach((yy, k) => { if (p.rows[yy] > bx.width) p.issues.push(`Line ${k + 1} is ${p.rows[yy]} px wide (box is ${bx.width})`); });
    const bottom = ys.length ? Math.max(...ys) + 8 : 0;
    if (bottom > bx.rows * 8) p.issues.push(`Too many lines: needs ${Math.ceil(bottom / 8)} tile rows, box has ${bx.rows}`);
    if (p.unknown.length) p.issues.push('Not in the table: ' + [...new Set(p.unknown)].join(' '));
    p.issues.forEach(s => issues.push(`page ${n + 1}: ${s}`));
  });
  return {pages, issues};
}

function preview() {
  const b = T.blocks[T.sel]; if (!b) return;
  const {pages} = layout(textOf(b)), bx = box();
  const wrap = $('#sPages'); wrap.innerHTML = '';
  if (!pages.length) { wrap.innerHTML = '<div class="help">No visible text in this string (control codes only).</div>'; return; }
  pages.forEach((p, n) => {
    const maxX = Math.max(bx.width, ...Object.values(p.rows), 0);
    const ys = Object.keys(p.rows).map(Number);
    const maxY = Math.max(bx.rows * 8, ...ys.map(y => y + 8), 8);
    const pad = 8, W = maxX + pad * 2, H = maxY + pad * 2;
    const c = document.createElement('canvas'); c.width = W * SCALE; c.height = H * SCALE;
    const g = c.getContext('2d'); g.imageSmoothingEnabled = false; g.scale(SCALE, SCALE);
    g.fillStyle = '#0e1014'; g.fillRect(0, 0, W, H);
    g.fillStyle = '#20366b'; g.fillRect(pad - 4, pad - 4, bx.width + 8, bx.rows * 8 + 8);
    g.strokeStyle = '#d8e2ff'; g.lineWidth = 1; g.strokeRect(pad - 3.5, pad - 3.5, bx.width + 7, bx.rows * 8 + 7);
    if (maxX > bx.width) { g.fillStyle = 'rgba(255,93,108,.25)'; g.fillRect(pad + bx.width, pad, maxX - bx.width, maxY); }
    if (maxY > bx.rows * 8) { g.fillStyle = 'rgba(255,93,108,.25)'; g.fillRect(pad, pad + bx.rows * 8, maxX, maxY - bx.rows * 8); }
    for (const gl of p.glyphs) {
      const X = pad + gl.x, Y = pad + gl.y;
      if (gl.code < 0) { g.fillStyle = '#ff5d6c'; g.fillRect(X, Y, 7, 8); continue; }
      const out = gl.x + (T.meta.widths[gl.code] || 8) > bx.width || gl.y + 8 > bx.rows * 8;
      const f = out ? T.fontBad : gl.v === 'var' ? T.fontVar : T.font;
      if (f) g.drawImage(f, (gl.code % 16) * 8, Math.floor(gl.code / 16) * 8, 8, 8, X, Y, 8, 8);
      else { g.fillStyle = '#ccc'; g.fillRect(X + 1, Y + 1, 5, 6); }
    }
    if (p.end === 'A') { g.fillStyle = '#ffd84d'; g.beginPath(); g.moveTo(pad + bx.width - 6, pad + bx.rows * 8 + 1); g.lineTo(pad + bx.width, pad + bx.rows * 8 + 1); g.lineTo(pad + bx.width - 3, pad + bx.rows * 8 + 4); g.fill(); }
    const el = document.createElement('div'); el.className = 'page';
    const endTxt = p.end === 'A' ? 'waits for A' : p.end ? '&lt;' + p.end + '&gt;' : '';
    el.innerHTML = `<div class="cap"><b>Page ${n + 1}</b><span>${endTxt}</span>${p.title ? `<span>title: ${esc(p.title)}</span>` : ''}${p.notes.map(s => `<span>${esc(s)}</span>`).join('')}</div>`;
    el.appendChild(c);
    if (p.issues.length) el.insertAdjacentHTML('beforeend', '<ul>' + p.issues.map(s => `<li>${esc(s)}</li>`).join('') + '</ul>');
    wrap.appendChild(el);
  });
}

// ----------------------------------------------------------------- toolbar
function boxChanged() { store('boxW', $('#sBoxW').value); store('boxR', $('#sBoxR').value);
  T.blocks.forEach(b => T.issues[b.i] = layout(textOf(b)).issues); renderStrings(); preview(); }
$('#sBoxW').onchange = boxChanged; $('#sBoxR').onchange = boxChanged;
$('#sBoxReset').onclick = () => { $('#sBoxW').value = T.meta.box.width; $('#sBoxR').value = T.meta.box.rows; boxChanged(); };
$('#sSearch').oninput = renderStrings; $('#sOnlyBad').onchange = renderStrings;
async function save() {
  if (!T.file || !isDirty()) return;
  const edits = Object.keys(T.edits).map(Number).filter(i => T.edits[i] !== T.blocks[i].text)
    .map(i => ({i, hash: T.blocks[i].hash, text: T.edits[i]}));
  const r = await api('/api/script/save', {name: T.file.name, edits});
  log(r.log, r.checkOk);
  if (T.file.name === 'jetters_011.txt') T.meta = await api('/api/script/meta');
  await loadFiles(); await loadFile(T.file.name, true);
}
$('#sSaveBtn').onclick = () => act(save);
$('#sCheckBtn').onclick = () => act(async () => { const r = await api('/api/script/check', {args: ['--width', String(box().width)]}); log(r.log, r.ok); openLog(true); });
function key(e) {
  if (e.target.matches('input,select,textarea')) return;
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    const items = [...document.querySelectorAll('#sStrings .it')].map(el => +el.dataset.i);
    const k = items.indexOf(T.sel) + (e.key === 'ArrowDown' ? 1 : -1);
    if (k >= 0 && k < items.length) { e.preventDefault(); select(items[k]); const el = $(`#sStrings .it[data-i="${items[k]}"]`); if (el) el.scrollIntoView({block: 'nearest'}); }
  }
}

App.register('script', {init, isDirty, save, key, shown: () => {}});
})();
