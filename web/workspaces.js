// Workspace switcher: 🏛 Здания (the building constructor in app.js) and the workshops (items, clothes, rig).
// Each workshop owns the viewport while active and has its own module web/ws/<id>.js exporting
// mount(el, ctx) -> builds its tools into el; ctx = { pazl, info, blender, refresh, open }.
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const KEY = 'pazl.ws';
let infos = null, blender = null;

async function blenderInfo() {
  if (!blender) blender = fetch('/api/ws/blender').then((r) => r.json()).catch(() => ({ found: false }));
  return blender;
}

function blenderLine(b) {
  if (!b) return '⏳ проверяю Blender…';
  if (!b.found) return 'Blender не найден (не обязателен: встроенные инструменты работают без него; PAZL_BLENDER — путь, если нужен).';
  if (b.error) return '⚠ Blender найден, но не запустился: ' + esc(b.error);
  const ok = Object.entries(b.addons || {}).filter(([, v]) => v).map(([k]) => k).join(', ');
  return `✓ Blender ${esc(b.version)} · ${esc(ok)}`;
}

// 2D workspaces: a 2D canvas replaces the 3D viewport (body[data-dim="2d"]). Modules draw via ctx.view2d.
let v2d = null;
function view2d() {
  if (v2d) return v2d;
  const c = document.createElement('canvas');
  c.id = 'view2d';
  c.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;z-index:1;display:none;background:#26262b';
  $('#center').appendChild(c);
  const st = document.createElement('style');
  st.textContent = 'body[data-dim="2d"] #view2d{display:block!important} body[data-dim="2d"] #vtools .vrow>*:not(#btnHideL):not(#btnHideR){display:none}';
  document.head.appendChild(st);
  const g = c.getContext('2d');
  let last = null;
  const cache = new Map();
  const img = (src) => {
    if (typeof src !== 'string') return Promise.resolve(src);
    if (!cache.has(src)) cache.set(src, new Promise((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = no; i.src = src; }));
    return cache.get(src);
  };
  const size = () => { const r = c.getBoundingClientRect(); const d = devicePixelRatio || 1;
    if (c.width !== Math.round(r.width * d) || c.height !== Math.round(r.height * d)) { c.width = Math.round(r.width * d); c.height = Math.round(r.height * d); } };
  // layers: [{img, alpha?}] drawn fitted into the canvas over a checkerboard; after(g, fit) for overlays
  const draw = (layers, after) => {
    last = [layers, after]; size();
    const W = c.width, H = c.height;
    g.setTransform(1, 0, 0, 1, 0, 0); g.fillStyle = '#26262b'; g.fillRect(0, 0, W, H);
    const base = layers.find((l) => l.img)?.img; if (!base) return null;
    const s = Math.min((W - 40) / base.width, (H - 40) / base.height, 8), w = base.width * s, h = base.height * s;
    const f = { s, x: (W - w) / 2, y: (H - h) / 2, w, h, d: devicePixelRatio || 1 };
    const q = 8 * f.d; for (let y = 0; y < h; y += q) for (let x = 0; x < w; x += q) {
      g.fillStyle = ((x / q + y / q) & 1) ? '#cfcfd4' : '#f2f2f5'; g.fillRect(f.x + x, f.y + y, Math.min(q, w - x), Math.min(q, h - y)); }
    g.imageSmoothingEnabled = s < 2;
    for (const l of layers) if (l.img) { g.globalAlpha = l.alpha ?? 1; g.drawImage(l.img, f.x, f.y, w, h); }
    g.globalAlpha = 1; after?.(g, f); return f;
  };
  new ResizeObserver(() => last && draw(...last)).observe(c);
  v2d = { canvas: c, g, img, draw, show: async (src) => draw([{ img: await img(src) }]), redraw: () => last && draw(...last) };
  return v2d;
}

async function renderWs(id) {
  const el = $('#wsLeft');
  infos ||= await fetch('/api/ws').then((r) => r.json());
  const info = infos.find((w) => w.id === id);
  el.innerHTML = `<h3>${esc(info.title)}</h3><div class="hint">${esc(info.about)}</div>
    <div class="hint" id="wsBlender">${blenderLine(null)}</div>
    <h4>Модели</h4><div id="wsModels"></div><button id="wsRoblox" style="width:100%;margin:4px 0" title="Готовые файлы и инструкция в projects/roblox/">⬇ Для Roblox</button><pre id="wsRbxOut" class="hint" style="white-space:pre-wrap;font-size:11px"></pre><div id="wsTools"></div>`;
  blenderInfo().then((b) => { const n = $('#wsBlender'); if (n && document.body.dataset.ws === id) n.innerHTML = blenderLine(b); });
  let picked = null;
  $('#wsRoblox').onclick = async () => {
    const out = $('#wsRbxOut');
    const char = ['chars', 'clothes'].includes(id) ? (localStorage.getItem('pazl.char') || '') : '';
    if (!char && !picked) { out.textContent = 'Сначала выберите модель'; return; }
    out.textContent = '⏳ готовлю файлы…';
    const r = await fetch('/api/ws/roblox/export', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(char ? { char } : { path: picked }) });
    const j = await r.json();
    out.textContent = r.ok ? `✓ ${j.abs}\n${j.files.join(', ')}${j.notes.length ? '\n⚠ ' + j.notes.join('\n⚠ ') : ''}` : '⚠ ' + j.detail;
  };
  const open = async (path) => {
    picked = path;
    document.querySelectorAll('#wsModels .ws-model').forEach((m) => m.classList.toggle('on', m.dataset.p === path));
    if (info.dim === '2d') { if (ctx.pick) return ctx.pick(path); return view2d().show('/files/' + path); }
    return window.pazl.viewGlb(path);
  };
  const ctx = {};
  const refresh = async () => {
    const list = await fetch(`/api/ws/${id}/models`).then((r) => r.json());
    const box = $('#wsModels');
    if (!box) return list;
    box.innerHTML = list.length ? list.map((m) => `<div class="ws-model" data-p="${esc(m.path)}">${esc(m.name)} <span class="hint">${m.kb} КБ</span></div>`).join('')
      : `<div class="hint">Пока пусто: файлы появятся в projects/${esc(info.dir || id)}/.</div>`;
    box.querySelectorAll('.ws-model').forEach((m) => { m.onclick = () => open(m.dataset.p); });
    return list;
  };
  const list = await refresh();
  window.pazl.root.clear(); window.pazl.invalidate();
  $('#status').textContent = `${info.title}: ${list.length ? 'выберите модель слева' : 'моделей пока нет'}`;
  try {
    const mod = await import(`./ws/${id}.js`);
    Object.assign(ctx, { pazl: window.pazl, info, blender: blenderInfo, refresh, open, view2d: info.dim === '2d' ? view2d() : null });
    mod.mount?.($('#wsTools'), ctx);
  } catch (e) { $('#wsTools').innerHTML = `<div class="hint">Ошибка модуля: ${esc(e.message)}</div>`; }
}

// 2D / 3D: which group of workspaces the header shows; each group remembers its last workspace
const dimOf = (id) => document.querySelector(`#segWs button[data-ws="${id}"]`)?.dataset.dim || '3d';
const lastIn = { '2d': 'frames', '3d': 'build' };
function showDim(dim) {
  document.body.dataset.dim = dim;
  document.querySelectorAll('#segDim button').forEach((b) => b.classList.toggle('on', b.dataset.dim === dim));
  document.querySelectorAll('#segWs button').forEach((b) => { b.hidden = b.dataset.dim !== dim; });
}
document.querySelectorAll('#segDim button').forEach((b) => { b.onclick = () => setWs(lastIn[b.dataset.dim]); });

function setWs(id) {
  if (!document.querySelector(`#segWs button[data-ws="${id}"]`)) id = 'build';
  lastIn[dimOf(id)] = id; showDim(dimOf(id));
  document.body.dataset.ws = id;
  document.querySelectorAll('#segWs button').forEach((b) => b.classList.toggle('on', b.dataset.ws === id));
  try { localStorage.setItem(KEY, id); } catch (e) { /* storage blocked */ }
  if (id === 'build') return window.pazl?.reloadModel(true);
  return renderWs(id);
}

// A character GLB (chars/…) opened from outside a character workshop (e.g. by the agent) switches to the clothes tab
// instead of showing up under whatever workshop was remembered last (e.g. transport).
window.pazlEnsureWs = async (path) => {
  if (!/^(projects\/)?chars\//.test(path || '')) return;
  if (['chars', 'clothes', 'skins', 'rig'].includes(document.body.dataset.ws)) return;
  await setWs('clothes');
};

document.querySelectorAll('#segWs button').forEach((b) => { b.onclick = () => setWs(b.dataset.ws); });
let saved = 'build';
try { saved = localStorage.getItem(KEY) || 'build'; } catch (e) { /* storage blocked */ }
if (saved !== 'build') {  // wait until app.js has exposed window.pazl
  const t = setInterval(() => { if (window.pazl) { clearInterval(t); setWs(saved); } }, 100);
}
