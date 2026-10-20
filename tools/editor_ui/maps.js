"use strict";
// ============================================================ Tilemaps view
(function () {
const M = {list: [], data: null, entries: [], undo: [], redo: [], dirty: false, sel: -1, brush: null, img: null, base: 0, paint: null};

async function init(state) {
  M.list = state.maps;
  renderList();
  const pick = M.list.find(m => m.name === store('map')) || M.list[0];
  if (pick) await loadMap(pick.name);
}
function renderList() {
  $('#mList').innerHTML = M.list.map(m => `<div class="it ${M.data && M.data.name === m.name ? 'cur' : ''}" data-n="${esc(m.name)}"><span>${esc(m.name)}</span></div>`).join('');
  $('#mList').querySelectorAll('.it').forEach(el => el.onclick = () => {
    if (M.dirty && !confirm('You have unsaved map changes. Discard them?')) return;
    act(() => loadMap(el.dataset.n));
  });
  $('#mEmpty').textContent = M.list.length ? '' : 'No maps yet - press + Map.';
}
async function loadMap(name) {
  const d = await api('/api/map?name=' + encodeURIComponent(name));
  M.data = d; M.entries = d.entries.slice(); M.undo = []; M.redo = []; M.sel = -1; M.base = d.base;
  setDirty(false); store('map', d.name); renderList();
  $('#mBase').value = d.base;
  M.img = null;
  if (d.sheetOk) loadImage('/api/png?path=' + encodeURIComponent(d.sheet) + '&v=' + d.sheetMtime).then(i => { M.img = i; drawAll(); });
  let h = `<div>${esc(d.note || '')}</div><div style="margin-top:6px">${d.width}&times;${d.height} tiles</div>
    <div>Map: <b>${esc(d.source)}</b></div><div>Sheet: ${esc(d.sheet)}</div>`;
  if (d.rom) h += `<div>ROM: ${esc(d.rom)} (written back in place on build)</div>`;
  else h += `<div class="help">No ROM address: the saved .bin is used by your own asm/build.</div>`;
  if (!d.sheetOk) h += `<div class="banner warn">Sheet not found: ${esc(d.sheet)}</div>`;
  $('#mInfo').innerHTML = h;
  drawAll();
}
function setDirty(v) { M.dirty = v; const s = $('#mStatus'); s.textContent = v ? 'Unsaved changes' : 'Saved'; s.className = 'status' + (v ? ' dirty' : ''); App.dirtyChanged(); }
function pushUndo() { M.undo.push(M.entries.slice()); if (M.undo.length > 300) M.undo.shift(); M.redo = []; setDirty(true); }
function undo() { if (!M.undo.length) return; M.redo.push(M.entries); M.entries = M.undo.pop(); setDirty(true); drawAll(); }
function redo() { if (!M.redo.length) return; M.undo.push(M.entries); M.entries = M.redo.pop(); setDirty(true); drawAll(); }

const cols = () => (M.data.sheetW / 8) | 0;
const ntiles = () => cols() * ((M.data.sheetH / 8) | 0);

// --------------------------------------------------------------- drawing
const cv = $('#mcv'), ctx = cv.getContext('2d');
function drawAll() { if (!M.data) return; drawMap(); drawSheet(); renderBrush(); renderCell(); }
function drawTile(c, e, x, y, z, dim) {
  const t = (e & 0x3FF) - M.base, hf = e & 0x400, vf = e & 0x800;
  if (t >= 0 && t < ntiles() && M.img) {
    c.save(); c.translate(x + (hf ? 8 * z : 0), y + (vf ? 8 * z : 0)); c.scale(hf ? -z : z, vf ? -z : z);
    c.drawImage(M.img, (t % cols()) * 8, Math.floor(t / cols()) * 8, 8, 8, 0, 0, 8, 8); c.restore();
    return true;
  }
  if (dim) { c.fillStyle = 'rgba(120,120,140,.18)'; c.fillRect(x, y, 8 * z, 8 * z); }
  return false;
}
function drawMap() {
  const d = M.data, z = +$('#mZoom').value, W = d.width, H = d.height;
  cv.width = W * 8 * z; cv.height = H * 8 * z; ctx.imageSmoothingEnabled = false;
  checker(ctx, W * 8, H * 8, z);
  const src = $('#mRomChk').checked && d.romEntries ? d.romEntries : M.entries;
  const num = $('#mNumChk').checked;
  for (let i = 0; i < W * H; i++) {
    const x = (i % W) * 8 * z, y = Math.floor(i / W) * 8 * z, e = src[i];
    const inSheet = drawTile(ctx, e, x, y, z, true);
    if (num) { ctx.fillStyle = inSheet ? '#fff' : '#8b93a7'; ctx.font = Math.max(8, 2.6 * z) + 'px monospace'; ctx.fillText((e & 0x3FF).toString(16), x + 1, y + 3 * z); }
    if (d.romEntries && src === M.entries && e !== d.romEntries[i]) { ctx.fillStyle = '#ffb347'; ctx.fillRect(x + 8 * z - 4, y, 4, 4); }
  }
  if ($('#mGridChk').checked) {
    ctx.strokeStyle = 'rgba(255,255,255,.07)'; ctx.lineWidth = 1; ctx.beginPath();
    for (let x = 0; x <= W; x++) { ctx.moveTo(x * 8 * z + .5, 0); ctx.lineTo(x * 8 * z + .5, H * 8 * z); }
    for (let y = 0; y <= H; y++) { ctx.moveTo(0, y * 8 * z + .5); ctx.lineTo(W * 8 * z, y * 8 * z + .5); }
    ctx.stroke();
  }
  if (M.sel >= 0) { ctx.strokeStyle = '#ffd84d'; ctx.lineWidth = 2; ctx.strokeRect((M.sel % W) * 8 * z + 1, Math.floor(M.sel / W) * 8 * z + 1, 8 * z - 2, 8 * z - 2); }
  if (M.hover !== undefined && M.hover >= 0 && M.brush) {
    const b = M.brush; ctx.strokeStyle = '#4da3ff'; ctx.lineWidth = 2;
    ctx.strokeRect((M.hover % W) * 8 * z + 1, Math.floor(M.hover / W) * 8 * z + 1, b.cols * 8 * z - 2, b.rows * 8 * z - 2);
  }
}
const sc = $('#msheet'), sctx = sc.getContext('2d');
function usedTiles() { const s = new Set(); for (const e of M.entries) { const t = (e & 0x3FF) - M.base; if (t >= 0) s.add(t); } return s; }
function drawSheet() {
  const d = M.data, z = +$('#mSheetZoom').value, W = d.sheetW, H = d.sheetH;
  sc.width = W * z; sc.height = H * z; sctx.imageSmoothingEnabled = false;
  checker(sctx, W, H, z);
  if (M.img) sctx.drawImage(M.img, 0, 0, W * z, H * z);
  const used = usedTiles(), ne = new Set(d.nonempty), n = ntiles(), cc = cols();
  let inactive = 0;
  for (let t = 0; t < n; t++) {
    const x = (t % cc) * 8 * z, y = Math.floor(t / cc) * 8 * z;
    if (ne.has(t) && !used.has(t)) { inactive++; sctx.fillStyle = 'rgba(255,93,108,.35)'; sctx.fillRect(x, y, 8 * z, 8 * z); }
    sctx.strokeStyle = 'rgba(255,255,255,.08)'; sctx.lineWidth = 1; sctx.strokeRect(x + .5, y + .5, 8 * z - 1, 8 * z - 1);
    if (used.has(t)) { sctx.strokeStyle = '#3ccf7a'; sctx.strokeRect(x + 1.5, y + 1.5, 8 * z - 3, 8 * z - 3); }
    if ($('#mSheetNum').checked) { sctx.fillStyle = '#fff'; sctx.font = Math.max(8, 3 * z) + 'px monospace'; sctx.fillText(t + M.base, x + 2, y + 3 * z + 1); }
  }
  if (M.brush) { const b = M.brush; sctx.strokeStyle = '#4da3ff'; sctx.lineWidth = 2; sctx.strokeRect(b.c * 8 * z + 1, b.r * 8 * z + 1, b.cols * 8 * z - 2, b.rows * 8 * z - 2); }
  $('#mSheetName').textContent = `${d.sheet} - ${inactive} inactive tile${inactive === 1 ? '' : 's'}`;
}
function renderBrush() {
  const b = M.brush;
  $('#mBrush').innerHTML = b ? `Brush: ${b.cols}&times;${b.rows} tile${b.cols * b.rows > 1 ? 's' : ''} starting at tile <b>${b.r * cols() + b.c + M.base}</b>. Click or drag on the map to paint.`
    : 'Click or drag across tiles below to pick a brush, then click/drag on the map to paint.';
}
function renderCell() {
  const el = $('#mCell');
  if (M.sel < 0 || !M.data) { el.innerHTML = '<div class="help">Click a map cell (with no brush) to inspect it.</div>'; return; }
  const e = M.entries[M.sel], W = M.data.width, rom = M.data.romEntries ? M.data.romEntries[M.sel] : null;
  el.innerHTML = `<div class="help">Cell (${M.sel % W}, ${Math.floor(M.sel / W)}) &middot; raw 0x${e.toString(16).toUpperCase().padStart(4, '0')}${rom !== null && rom !== e ? ` (ROM 0x${rom.toString(16).toUpperCase().padStart(4, '0')})` : ''}</div>
  <div class="grid2" style="margin-top:6px">
    <label>Tile</label><input type="number" data-k="tile" min="0" max="1023" value="${e & 0x3FF}">
    <label>Palette</label><input type="number" data-k="pal" min="0" max="15" value="${e >> 12}">
    <label>H flip</label><input type="checkbox" data-k="h" ${e & 0x400 ? 'checked' : ''}>
    <label>V flip</label><input type="checkbox" data-k="v" ${e & 0x800 ? 'checked' : ''}>
  </div><div class="row"><button id="mCellClear">Set to tile 0</button>${rom !== null ? '<button id="mCellRom">Reset to ROM</button>' : ''}</div>`;
  el.querySelectorAll('[data-k]').forEach(inp => inp.onchange = () => {
    pushUndo(); let v = M.entries[M.sel];
    const k = inp.dataset.k;
    if (k === 'tile') v = (v & ~0x3FF) | (Math.max(0, Math.min(1023, parseInt(inp.value) || 0)));
    if (k === 'pal') v = (v & 0x0FFF) | ((parseInt(inp.value) & 15) << 12);
    if (k === 'h') v = inp.checked ? v | 0x400 : v & ~0x400;
    if (k === 'v') v = inp.checked ? v | 0x800 : v & ~0x800;
    M.entries[M.sel] = v; drawAll();
  });
  $('#mCellClear').onclick = () => { pushUndo(); M.entries[M.sel] = M.entries[M.sel] & 0xF000; drawAll(); };
  if (rom !== null) $('#mCellRom').onclick = () => { pushUndo(); M.entries[M.sel] = rom; drawAll(); };
}

// ------------------------------------------------------------ painting
function cellAt(e) {
  const r = cv.getBoundingClientRect(), z = +$('#mZoom').value, W = M.data.width, H = M.data.height;
  const x = Math.floor((e.clientX - r.left) / z / 8), y = Math.floor((e.clientY - r.top) / z / 8);
  if (x < 0 || y < 0 || x >= W || y >= H) return -1;
  return y * W + x;
}
function stamp(i) {
  const b = M.brush, W = M.data.width, H = M.data.height, cc = cols();
  const x0 = i % W, y0 = Math.floor(i / W), hf = $('#mBrushH').checked, vf = $('#mBrushV').checked;
  const keep = $('#mKeepPal').checked, pal = parseInt($('#mBrushPal').value) & 15;
  for (let r = 0; r < b.rows; r++) for (let c = 0; c < b.cols; c++) {
    const x = x0 + (hf ? b.cols - 1 - c : c), y = y0 + (vf ? b.rows - 1 - r : r);
    if (x >= W || y >= H) continue;
    const k = y * W + x, t = (b.r + r) * cc + b.c + c + M.base;
    const p = keep ? (M.entries[k] >> 12) : pal;
    M.entries[k] = (p << 12) | (vf ? 0x800 : 0) | (hf ? 0x400 : 0) | (t & 0x3FF);
  }
}
cv.addEventListener('contextmenu', e => e.preventDefault());
cv.addEventListener('mousedown', e => {
  if (!M.data || $('#mRomChk').checked) return;
  const i = cellAt(e); if (i < 0) return;
  if (e.button === 2) {  // eyedropper
    const v = M.entries[i], t = (v & 0x3FF) - M.base;
    if (t >= 0 && t < ntiles()) { M.brush = {c: t % cols(), r: Math.floor(t / cols()), cols: 1, rows: 1};
      $('#mBrushH').checked = !!(v & 0x400); $('#mBrushV').checked = !!(v & 0x800); $('#mBrushPal').value = v >> 12; }
    else log(`tile ${v & 0x3FF} isn't in this sheet (with offset ${M.base})`, false);
    M.sel = i; drawAll(); return;
  }
  if (!M.brush) { M.sel = i; drawAll(); return; }
  pushUndo(); M.paint = {last: i}; stamp(i); drawAll();
});
cv.addEventListener('mousemove', e => {
  if (!M.data) return; const i = cellAt(e);
  if (i >= 0) { const v = M.entries[i]; $('#mCursor').textContent = `cell ${i % M.data.width},${Math.floor(i / M.data.width)}  tile ${v & 0x3FF}  pal ${v >> 12}`; }
  if (M.paint && i >= 0 && i !== M.paint.last) { M.paint.last = i; stamp(i); }
  if (i !== M.hover) { M.hover = i; drawMap(); }
});
window.addEventListener('mouseup', () => { if (M.paint) { M.paint = null; drawAll(); } });
cv.addEventListener('mouseleave', () => { M.hover = -1; if (M.data) drawMap(); });

function sheetCell(e) {
  const r = sc.getBoundingClientRect(), z = +$('#mSheetZoom').value;
  return {c: Math.max(0, Math.min(cols() - 1, Math.floor((e.clientX - r.left) / z / 8))),
          r: Math.max(0, Math.min(M.data.sheetH / 8 - 1, Math.floor((e.clientY - r.top) / z / 8)))};
}
sc.addEventListener('mousedown', e => { if (!M.data) return; const t = sheetCell(e); M.sdrag = {a: t}; M.brush = {c: t.c, r: t.r, cols: 1, rows: 1}; drawSheet(); renderBrush(); });
window.addEventListener('mousemove', e => {
  if (!M.sdrag) return; const t = sheetCell(e), a = M.sdrag.a;
  M.brush = {c: Math.min(a.c, t.c), r: Math.min(a.r, t.r), cols: Math.abs(a.c - t.c) + 1, rows: Math.abs(a.r - t.r) + 1}; drawSheet(); renderBrush();
});
window.addEventListener('mouseup', () => { M.sdrag = null; });
$('#mClearBrush').onclick = () => { M.brush = null; drawAll(); };

// -------------------------------------------------------------- toolbar
['#mZoom', '#mGridChk', '#mNumChk', '#mRomChk'].forEach(s => $(s).oninput = () => M.data && drawMap());
['#mSheetZoom', '#mSheetNum'].forEach(s => $(s).oninput = () => M.data && drawSheet());
$('#mBase').oninput = () => { if (!M.data) return; M.base = Math.max(0, parseInt($('#mBase').value) || 0); drawAll(); };
$('#mBaseSave').onclick = () => act(async () => { const r = await api('/api/map/base', {name: M.data.name, base: M.base}); log(r.log); });
$('#mUndoBtn').onclick = undo; $('#mRedoBtn').onclick = redo;
async function save() {
  if (!M.data) return;
  const r = await api('/api/map/save', {name: M.data.name, entries: M.entries}); log(r.log); setDirty(false);
}
$('#mSaveBtn').onclick = () => act(save);
function key(e) {
  if (e.target.matches('input,select,textarea')) return;
  const k = e.key.toLowerCase(), ctrl = e.ctrlKey || e.metaKey;
  if (ctrl && k === 'z') { e.preventDefault(); e.shiftKey ? redo() : undo(); }
  else if (ctrl && k === 'y') { e.preventDefault(); redo(); }
  else if (e.key === 'Escape') { M.brush = null; M.sel = -1; drawAll(); }
}

// -------------------------------------------------------------- add map
$('#mAddBtn').onclick = () => { $('#mAddDlg').showModal(); };
$('#maCancel').onclick = () => $('#mAddDlg').close();
$('#maOk').onclick = () => act(async () => {
  const r = await api('/api/map/add', {name: $('#maName').value, sheet: $('#maSheet').value, file: $('#maFile').value,
    rom: $('#maRom').value, width: $('#maW').value, height: $('#maH').value, base: $('#maBase').value});
  log(r.log); $('#mAddDlg').close();
  const st = await api('/api/state'); M.list = st.maps; await loadMap(r.name);
});

App.register('maps', {init, isDirty: () => M.dirty, save, key, shown: () => drawAll()});
})();
