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

async function renderWs(id) {
  const el = $('#wsLeft');
  infos ||= await fetch('/api/ws').then((r) => r.json());
  const info = infos.find((w) => w.id === id);
  el.innerHTML = `<h3>${esc(info.title)}</h3><div class="hint">${esc(info.about)}</div>
    <div class="hint" id="wsBlender">${blenderLine(null)}</div>
    <h4>Модели</h4><div id="wsModels"></div><div id="wsTools"></div>`;
  blenderInfo().then((b) => { const n = $('#wsBlender'); if (n && document.body.dataset.ws === id) n.innerHTML = blenderLine(b); });
  const open = async (path) => {
    document.querySelectorAll('#wsModels .ws-model').forEach((m) => m.classList.toggle('on', m.dataset.p === path));
    return window.pazl.viewGlb(path);
  };
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
    mod.mount?.($('#wsTools'), { pazl: window.pazl, info, blender: blenderInfo, refresh, open });
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
  if (id === 'build') window.pazl?.reloadModel(true);
  else renderWs(id);
}

document.querySelectorAll('#segWs button').forEach((b) => { b.onclick = () => setWs(b.dataset.ws); });
let saved = 'build';
try { saved = localStorage.getItem(KEY) || 'build'; } catch (e) { /* storage blocked */ }
if (saved !== 'build') {  // wait until app.js has exposed window.pazl
  const t = setInterval(() => { if (window.pazl) { clearInterval(t); setWs(saved); } }, 100);
}
