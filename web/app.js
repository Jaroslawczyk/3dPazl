import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { TransformControls } from 'three/addons/controls/TransformControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const api = async (path, body, method) => {
  const r = await fetch('/api/' + path, {
    method: method || (body === undefined ? 'GET' : 'POST'),
    headers: { 'Content-Type': 'application/json', 'X-Agent': 'user' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const ct = r.headers.get('content-type') || '';
  const data = ct.includes('json') ? await r.json() : await r.arrayBuffer();
  if (!r.ok) throw new Error(data.detail || r.statusText);
  return data;
};
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// Z-up (core) -> Y-up (three):  (x, y, z) -> (x, z, -y)
const toThree = (v) => new THREE.Vector3(v[0], v[2], -v[1]);

// ---------------------------------------------------------------- state
const S = { recipe: null, state: null, tree: [], catalog: [], styles: [], selected: null, mode: 'select',
            highlight: new Set(), model: null, meshesById: new Map(), lastCenter: null };

// ---------------------------------------------------------------- three.js scene
const vp = $('#viewport');
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.shadowMap.enabled = true;
vp.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x9fb4c8);
scene.fog = new THREE.Fog(0x9fb4c8, 300, 1200);
const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 5000);
camera.position.set(30, 22, 30);
const orbit = new OrbitControls(camera, renderer.domElement);
orbit.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xdde8ff, 0x6a6458, 1.4));
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(-60, 100, 50); sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -120, right: 120, top: 120, bottom: -120, far: 500 });
scene.add(sun);
const ground = new THREE.Mesh(new THREE.CircleGeometry(800, 64), new THREE.MeshStandardMaterial({ color: 0x77806f, roughness: 1 }));
ground.rotation.x = -Math.PI / 2; ground.position.y = -0.02; ground.receiveShadow = true;
scene.add(ground);
const grid = new THREE.GridHelper(400, 400, 0x5c6455, 0x6a7362);
grid.material.opacity = 0.35; grid.material.transparent = true;
scene.add(grid);
const root = new THREE.Group();
scene.add(root);
const gizmo = new TransformControls(camera, renderer.domElement);
gizmo.showX = gizmo.showZ = true;
scene.add(gizmo.getHelper());
const proxy = new THREE.Object3D();
scene.add(proxy);
gizmo.addEventListener('dragging-changed', (e) => { orbit.enabled = !e.value; if (!e.value) commitGizmo(); });
let gizmoStart = null;
gizmo.addEventListener('mouseDown', () => { gizmoStart = { p: proxy.position.clone(), r: proxy.rotation.y }; });

function resize() {
  const w = vp.clientWidth, h = vp.clientHeight;
  renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(vp);
function loop() { requestAnimationFrame(loop); orbit.update(); tickCamAnim(); renderer.render(scene, camera); }

// ---------------------------------------------------------------- model loading
const loader = new GLTFLoader();
let loading = false, pendingReload = false;
async function reloadModel(fit = false) {
  if (loading) { pendingReload = true; return; }
  loading = true; $('#busy').hidden = false;
  try {
    const welded = $('#chkWelded').checked;
    const buf = await api(welded ? 'model.glb' : 'preview.glb');
    const gltf = await loader.parseAsync(buf, '');
    root.clear();
    S.meshesById.clear();
    gltf.scene.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = o.receiveShadow = true;
      const id = welded ? null : (o.name || o.parent?.name || '').split('|')[0].replaceAll('~', '/');
      o.userData.eid = id;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      mats.forEach((m) => { m.flatShading = true; m.side = THREE.FrontSide; m.wireframe = $('#chkWire').checked; m.needsUpdate = true; });
      if (id) { if (!S.meshesById.has(id)) S.meshesById.set(id, []); S.meshesById.get(id).push(o); }
    });
    root.add(gltf.scene);
    applyHighlights();
    const box = new THREE.Box3().setFromObject(root);
    if (fit || !S.lastCenter) fitView(box, 'iso');
    S.lastCenter = box.getCenter(new THREE.Vector3());
    const tris = countTris();
    $('#status').textContent = `v${S.state?.version ?? '?'} · элементов ${S.tree.length} · треугольников ${tris.toLocaleString('ru')} · ${welded ? 'цельная сварная модель' : 'разборный режим'}`;
  } catch (e) { feedLine({ type: 'error', agent: 'ui', note: e.message }); }
  loading = false; $('#busy').hidden = true;
  if (pendingReload) { pendingReload = false; reloadModel(); }
}
function countTris() { let n = 0; root.traverse((o) => { if (o.isMesh) n += (o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count) / 3; }); return n; }

function fitView(box, kind) {
  if (box.isEmpty()) return;
  const c = box.getCenter(new THREE.Vector3()), r = box.getSize(new THREE.Vector3()).length() / 2;
  const d = r / Math.sin(THREE.MathUtils.degToRad(camera.fov / 2)) * 1.05;
  const dir = { iso: [1, 0.6, 1], front: [0, 0.12, 1], side: [1, 0.12, 0], top: [0, 1, 0.001] }[kind] || [1, 0.6, 1];
  camAnimTo(c.clone().add(new THREE.Vector3(...dir).normalize().multiplyScalar(d)), c);
}

// smooth camera animation (also used to replay the AI's check views)
let camAnim = null;
function camAnimTo(pos, target, ms = 500) { camAnim = { p0: camera.position.clone(), t0: orbit.target.clone(), p1: pos, t1: target, s: performance.now(), ms }; }
function tickCamAnim() {
  if (!camAnim) return;
  const k = Math.min(1, (performance.now() - camAnim.s) / camAnim.ms), e = k * k * (3 - 2 * k);
  camera.position.lerpVectors(camAnim.p0, camAnim.p1, e);
  orbit.target.lerpVectors(camAnim.t0, camAnim.t1, e);
  if (k >= 1) camAnim = null;
}
async function playCameras(cams, center) {
  if (!$('#chkFollow').checked || !cams?.length) return;
  const back = { p: camera.position.clone(), t: orbit.target.clone() };
  const c = toThree(center);
  for (const cam of cams) {
    const m = cam.pose; // row-major 4x4, Z-up
    camAnimTo(toThree([m[0][3], m[1][3], m[2][3]]), c, 350);
    flashLabel(cam.view);
    await new Promise((r) => setTimeout(r, 520));
  }
  camAnimTo(back.p, back.t, 400);
}
function flashLabel(t) { $('#status').dataset.cam = t; $('#status').textContent = '📷 ИИ проверяет вид: ' + t; }

// ---------------------------------------------------------------- selection & highlight
const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
let downAt = null;
renderer.domElement.addEventListener('pointerdown', (e) => { downAt = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', (e) => {
  if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 4 || gizmo.dragging) return;
  const r = renderer.domElement.getBoundingClientRect();
  mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const hit = ray.intersectObjects(root.children, true).find((h) => h.object.userData.eid);
  select(hit ? hit.object.userData.eid : null);
});

function applyHighlights() {
  root.traverse((o) => {
    if (!o.isMesh) return;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    const id = o.userData.eid;
    const col = id && id === S.selected ? 0x7a5a10 : (id && S.highlight.has(id) ? 0x8a0000 : 0x000000);
    mats.forEach((m) => { if (m.emissive) m.emissive.setHex(col); });
  });
}

function select(id) {
  S.selected = id;
  applyHighlights();
  $$('#tree li > div').forEach((d) => d.classList.toggle('sel', d.dataset.id === id));
  attachGizmo();
  showProps(id);
}

function attachGizmo() {
  gizmo.detach();
  const meshes = S.meshesById.get(S.selected);
  if (!meshes || S.mode === 'select') return;
  const box = new THREE.Box3();
  meshes.forEach((m) => box.expandByObject(m));
  proxy.position.copy(box.getCenter(new THREE.Vector3()));
  proxy.rotation.set(0, 0, 0);
  gizmo.setMode(S.mode);
  gizmo.showX = gizmo.showZ = S.mode === 'translate';
  gizmo.showY = true;
  gizmo.attach(proxy);
}
gizmo.addEventListener('objectChange', () => {
  if (!gizmoStart) return;
  const d = proxy.position.clone().sub(gizmoStart.p), dr = proxy.rotation.y - gizmoStart.r;
  (S.meshesById.get(S.selected) || []).forEach((m) => {
    if (m.userData.p0 === undefined) { m.userData.p0 = m.position.clone(); }
    m.position.copy(m.userData.p0).add(d);
  });
  if (dr) $('#status').textContent = `поворот ${(THREE.MathUtils.radToDeg(dr)).toFixed(1)}°`;
});
async function commitGizmo() {
  if (!gizmoStart || !S.selected) return;
  const d = proxy.position.clone().sub(gizmoStart.p), dr = THREE.MathUtils.radToDeg(proxy.rotation.y - gizmoStart.r);
  gizmoStart = null;
  if (d.length() < 1e-4 && Math.abs(dr) < 0.01) return;
  const snap = (v) => Math.round(v * 100) / 100;
  await patch([{ op: 'nudge', id: S.selected, world_delta: [snap(d.x), snap(-d.z), snap(d.y)], rot_delta: snap(dr) }], 'ручное перемещение');
}

// ---------------------------------------------------------------- data refresh
async function refreshAll(fit = false) {
  [S.state, S.recipe, S.tree] = await Promise.all([api('state'), api('recipe'), api('tree')]);
  $('#projName').value = S.state.name || '';
  $('#selStyle').value = S.state.style;
  $$('#segDetail button').forEach((b) => b.classList.toggle('on', b.dataset.v === S.state.detail));
  $('#btnUndo').disabled = !S.state.can_undo; $('#btnRedo').disabled = !S.state.can_redo;
  renderTree();
  await reloadModel(fit);
  if (S.selected && !S.tree.find((t) => t.id === S.selected)) select(null);
  else if (S.selected) { attachGizmo(); showProps(S.selected); }
}

function renderTree() {
  const kids = new Map();
  S.tree.forEach((t) => { const p = t.host || ''; if (!kids.has(p)) kids.set(p, []); kids.get(p).push(t); });
  const build = (parent) => {
    const ul = document.createElement('ul');
    (kids.get(parent) || []).forEach((t) => {
      const li = document.createElement('li');
      const has = kids.has(t.id);
      const short = t.id.split('/').pop();
      li.innerHTML = `<div data-id="${esc(t.id)}" class="${t.id === S.selected ? 'sel' : ''}"><span class="tog">${has ? '▾' : ''}</span>`
        + `<span class="${t.error ? 'err' : ''}">${esc(short)}</span> <span class="t">${esc(t.type === '_group' ? 'макрос' : t.type)}</span>`
        + `${t.error ? ' <span class="err" title="' + esc(t.error) + '">⚠</span>' : ''}</div>`;
      if (has) li.appendChild(build(t.id));
      ul.appendChild(li);
    });
    return ul;
  };
  const t = $('#tree'); t.innerHTML = ''; t.appendChild(build(''));
  t.querySelectorAll('li > div').forEach((d) => d.addEventListener('click', (e) => {
    if (e.target.classList.contains('tog') && e.target.textContent) {
      const ul = d.parentElement.querySelector(':scope > ul'); ul.hidden = !ul.hidden;
      e.target.textContent = ul.hidden ? '▸' : '▾'; return;
    }
    select(d.dataset.id);
  }));
}

// ---------------------------------------------------------------- properties panel
const catalogByType = () => Object.fromEntries(S.catalog.map((c) => [c.type, c]));
function fieldHtml(key, spec, val) {
  const v = val === undefined ? spec.default : val;
  const desc = spec.desc ? `<div class="desc">${esc(spec.desc)}</div>` : '';
  let inp;
  if (spec.choices) inp = `<select data-k="${key}">${spec.choices.map((c) => `<option ${c === v ? 'selected' : ''}>${esc(c)}</option>`).join('')}</select>`;
  else if (typeof spec.default === 'boolean') inp = `<input type="checkbox" data-k="${key}" ${v ? 'checked' : ''}>`;
  else if (typeof spec.default === 'number' && (typeof v === 'number' || v === null)) inp = `<input type="number" step="any" data-k="${key}" value="${v ?? ''}">`;
  else if (typeof v === 'string' || (spec.default === null && v == null) || typeof spec.default === 'string')
    inp = `<input data-k="${key}" data-json="1" value="${esc(v == null ? '' : (typeof v === 'string' ? v : JSON.stringify(v)))}" placeholder="авто">`;
  else inp = `<input data-k="${key}" data-json="1" value="${esc(JSON.stringify(v))}">`;
  return `<div class="prop"><label title="${esc(key)}">${esc(key)}</label>${inp}${desc}</div>`;
}
function readFields(container, specs) {
  const out = {};
  container.querySelectorAll('[data-k]').forEach((el) => {
    const k = el.dataset.k, spec = specs[k] || {};
    let v;
    if (el.type === 'checkbox') v = el.checked;
    else if (el.type === 'number') v = el.value === '' ? null : Number(el.value);
    else if (el.dataset.json) {
      const s = el.value.trim();
      if (s === '') v = null;
      else { try { v = JSON.parse(s); } catch { v = s; } }
    } else v = el.value;
    const def = spec.default;
    if (JSON.stringify(v) !== JSON.stringify(def)) out[k] = v;
  });
  return out;
}

async function showProps(id) {
  const box = $('#props');
  if (!id) { box.innerHTML = '<div class="hint">Выберите элемент в сцене или в дереве. Режимы: Q — выбор, W — двигать, E — вращать.</div>'; return; }
  let info;
  try { info = await api('element/' + encodeURI(id)); } catch (e) { box.innerHTML = esc(e.message); return; }
  const src = info.src, type = src.macro_type || src.type, cat = catalogByType()[type];
  const schema = cat ? (await api('catalog/element/' + type)).params : {};
  const params = src.params || {};
  const isGroup = src.type === '_group';
  box.innerHTML = `<div class="props-head"><div class="id">${esc(id)}</div><div class="tp">${esc(type)}${isGroup ? ' (макрос)' : ''}</div>`
    + `${cat ? `<div class="hint">${esc(cat.desc)}</div>` : ''}${info.error ? `<div class="er">⚠ ${esc(info.error)}</div>` : ''}</div>`
    + `<fieldset><legend>Положение</legend>`
    + fieldHtml('on', { default: null, desc: 'к чему прикреплён: id:якорь' }, src.on)
    + fieldHtml('at', { default: null, desc: '[u,v] на фасаде или [x,y] на крыше, можно "50%"' }, src.at)
    + fieldHtml('offset', { default: null, desc: 'доп. смещение [x,y,z] в системе якоря' }, src.offset)
    + fieldHtml('rot', { default: 0, desc: 'поворот вокруг вертикали, °' }, src.rot ?? 0)
    + fieldHtml('repeat', { default: null, desc: '{"count":3,"step":[4,0,0]}' }, src.repeat)
    + `</fieldset><fieldset id="pf"><legend>Параметры</legend>${Object.entries(schema).map(([k, s]) => fieldHtml(k, s, params[k])).join('')}</fieldset>`
    + `<div class="row"><button id="pApply" class="on">Применить</button><button id="pDup">Дублировать</button>`
    + `${isGroup && info.in_recipe ? '<button id="pExplode" title="Разобрать макрос на обычные элементы">Разобрать</button>' : ''}`
    + `<button id="pDel">Удалить</button><button id="pAnch">Якоря</button></div><div id="anchList"></div>`;
  const posSpecs = { on: { default: null }, at: { default: null }, offset: { default: null }, rot: { default: 0 }, repeat: { default: null } };
  $('#pApply').onclick = async () => {
    const pos = {}; const fs = box.querySelector('fieldset');
    fs.querySelectorAll('[data-k]').forEach((el) => { const r = readFields({ querySelectorAll: () => [el] }, posSpecs); const k = el.dataset.k; pos[k] = k in r ? r[k] : null; });
    const p = readFields($('#pf'), schema);
    const full = {}; Object.keys(schema).forEach((k) => { full[k] = k in p ? p[k] : null; });
    Object.assign(full, p);
    const cleaned = Object.fromEntries(Object.entries(full).filter(([k, v]) => v !== null || k in params));
    await patch([{ op: 'update', id, params: cleaned, ...pos }], 'правка параметров ' + id);
  };
  $('#pDel').onclick = () => patch([{ op: 'remove', id }], 'удалён ' + id);
  $('#pDup').onclick = () => {
    const e = JSON.parse(JSON.stringify(src)); delete e.macro_type;
    if (e.type === '_group') e.type = type;
    e.id = id.split('/').pop() + '_copy'; e.offset = [(e.offset?.[0] || 0) + 2, e.offset?.[1] || 0, e.offset?.[2] || 0];
    if (id.includes('/')) { delete e.on; }
    return patch([{ op: 'add', element: e }], 'копия ' + id);
  };
  if ($('#pExplode')) $('#pExplode').onclick = () => patch([{ op: 'explode', id }], 'разобран макрос ' + id);
  $('#pAnch').onclick = async () => {
    const a = await api('anchors/' + encodeURI(id));
    $('#anchList').innerHTML = '<div class="hint">Якоря (к ним можно крепить элементы):</div>' + Object.entries(a).map(([k, v]) =>
      `<div class="hint">• <b>${esc(id)}:${esc(k)}</b> — ${v.kind}${v.kind === 'face' ? ` ${v.w}×${v.h} м` : ''}</div>`).join('');
  };
}

// add new element from the library
async function showAdd(type) {
  const cat = catalogByType()[type];
  const schema = (await api('catalog/element/' + type)).params;
  const hosts = S.tree.filter((t) => t.type !== '_group' || true);
  const def = S.selected || (hosts[0] && hosts[0].id) || '';
  $('#props').innerHTML = `<div class="props-head"><div class="id">Новый: ${esc(type)}</div><div class="hint">${esc(cat.desc)}</div>`
    + `<div class="hint">Крепление: <b>${esc(cat.attach)}</b>${cat.anchors ? ' · даёт якоря: ' + esc(cat.anchors) : ''}</div></div>`
    + `<fieldset><legend>Куда</legend><div class="prop"><label>к элементу</label><select id="nHost"><option value="">— свободно —</option>`
    + hosts.map((h) => `<option ${h.id === def ? 'selected' : ''}>${esc(h.id)}</option>`).join('') + `</select></div>`
    + `<div class="prop"><label>якорь</label><select id="nAnchor"></select></div>`
    + fieldHtml('at', { default: null, desc: '[u,v] / [x,y] / [x,y,z]' }, null) + `</fieldset>`
    + `<fieldset id="nf"><legend>Параметры</legend>${Object.entries(schema).map(([k, s]) => fieldHtml(k, s)).join('')}</fieldset>`
    + `<div class="row"><button id="nAdd" class="on">Добавить</button></div>`;
  const fillAnchors = async () => {
    const h = $('#nHost').value, sel = $('#nAnchor'); sel.innerHTML = '';
    if (!h) return;
    const a = await api('anchors/' + encodeURI(h));
    const want = cat.attach === 'face' ? 'face' : cat.attach === 'top' ? 'top' : null;
    Object.entries(a).filter(([, v]) => !want || v.kind === want).forEach(([k]) => sel.add(new Option(k, k)));
  };
  $('#nHost').onchange = fillAnchors; fillAnchors();
  $('#nAdd').onclick = async () => {
    const el = { id: type, type, params: readFields($('#nf'), schema) };
    const h = $('#nHost').value; if (h) el.on = h + ':' + ($('#nAnchor').value || 'origin');
    const at = readFields($('#props fieldset'), { at: { default: null } }).at; if (at) el.at = at;
    await patch([{ op: 'add', element: el }], 'добавлен ' + type);
  };
}

// ---------------------------------------------------------------- library & styles
const CAT_RU = { macros: 'Готовые здания (макросы)', structure: 'Конструкции', openings: 'Окна и двери', roofs: 'Крыши, купола, шпили',
  columns: 'Колонны и портики', decor: 'Декор и фасад', primitive: 'Примитивы (любые формы)' };
function renderLib() {
  const q = $('#libSearch').value.toLowerCase();
  const groups = {};
  S.catalog.forEach((c) => {
    const text = (c.type + ' ' + (c.title_ru || '') + ' ' + c.desc).toLowerCase();
    if (q && !text.includes(q)) return;
    (groups[c.category] ||= []).push(c);
  });
  $('#lib').innerHTML = Object.keys(CAT_RU).filter((k) => groups[k]).map((k) => `<div class="cat">${CAT_RU[k]}</div>`
    + groups[k].map((c) => `<div class="lib-item" data-t="${c.type}"><b>${esc(c.title_ru || c.type)}</b> <span class="t">${c.type}</span><small>${esc(c.desc.slice(0, 110))}</small></div>`).join('')).join('');
  $$('#lib .lib-item').forEach((d) => d.onclick = () => showAdd(d.dataset.t));
}
function renderStyles() {
  $('#selStyle').innerHTML = S.styles.map((s) => `<option value="${s.id}">${esc(s.name_ru || s.name)}</option>`).join('');
  $('#styles').innerHTML = S.styles.map((s) => `<div class="style-card"><h4>${esc(s.name_ru || s.name)}</h4><small>${esc(s.era || '')} · ${esc(s.region || '')}</small>`
    + `<div class="hint">${esc(s.tips || '')}</div><div class="row">${(s.macros || []).map((m) => `<button data-m="${m}" data-s="${s.id}">+ ${m}</button>`).join('')}`
    + `<button data-apply="${s.id}">Применить стиль</button></div></div>`).join('');
  $$('#styles [data-m]').forEach((b) => b.onclick = () => patch([{ op: 'set', key: 'style', value: b.dataset.s },
    { op: 'add', element: { id: b.dataset.m, type: b.dataset.m } }], 'добавлен макрос ' + b.dataset.m));
  $$('#styles [data-apply]').forEach((b) => b.onclick = () => patch([{ op: 'set', key: 'style', value: b.dataset.apply }], 'стиль ' + b.dataset.apply));
}

// ---------------------------------------------------------------- actions
async function patch(ops, note) {
  try { return await api('patch', { ops, note }); } catch (e) { feedLine({ type: 'error', agent: 'ui', note: e.message }); }
}
$('#btnUndo').onclick = () => api('undo', {});
$('#btnRedo').onclick = () => api('redo', {});
$('#btnNew').onclick = async () => {
  const name = prompt('Название нового проекта:', 'new_building'); if (!name) return;
  await api('new', { name, style: $('#selStyle').value || 'generic' }); select(null);
};
$('#selProjects').onfocus = async () => {
  const list = await api('projects');
  $('#selProjects').innerHTML = '<option value="">Открыть…</option>' + list.map((p) => `<option>${esc(p)}</option>`).join('');
};
$('#selProjects').onchange = async (e) => { if (e.target.value) { await api('load', { name: e.target.value }); select(null); refreshAll(true); } e.target.value = ''; };
$('#projName').onchange = (e) => patch([{ op: 'set', key: 'name', value: e.target.value }], 'переименован');
$('#selStyle').onchange = (e) => patch([{ op: 'set', key: 'style', value: e.target.value }], 'стиль ' + e.target.value);
$$('#segDetail button').forEach((b) => b.onclick = () => patch([{ op: 'set', key: 'detail', value: b.dataset.v }], 'детализация ' + b.dataset.v));
$('#btnValidate').onclick = () => api('validate', {}).then(showCheck);
$('#btnRender').onclick = async () => { $('#busy').hidden = false; try { await api('render', {}); } finally { $('#busy').hidden = true; } };
$('#btnTextures').onclick = async () => {
  const m = await api('textures/manifest', {});
  feedLine({ type: 'textures', agent: 'ui', note: `${m.materials.length} материалов. Промпты: ${m.prompts_md}. Положите PNG в указанные папки и нажмите «Цельная».` });
  showTab('bottom', 'feed');
};
$('#selExport').onchange = async (e) => {
  const v = e.target.value; e.target.value = ''; if (!v) return;
  let body = { format: v };
  if (v === 'lod') { const n = Number(prompt('Целевое число треугольников:', '20000')); if (!n) return; body = { format: 'glb', lod_tris: n }; }
  let r = await api('export', body).catch((er) => ({ error: er.message }));
  if (r.error && confirm('Есть проблемы:\n' + JSON.stringify(r.problems || r.error).slice(0, 600) + '\n\nЭкспортировать всё равно?')) r = await api('export', { ...body, force: true });
  if (r.path) feedLine({ type: 'exported', agent: 'ui', note: r.path });
};
$('#chkWelded').onchange = () => reloadModel();
$('#chkWire').onchange = () => reloadModel();
$('#vFront').onclick = () => fitView(new THREE.Box3().setFromObject(root), 'front');
$('#vSide').onclick = () => fitView(new THREE.Box3().setFromObject(root), 'side');
$('#vTop').onclick = () => fitView(new THREE.Box3().setFromObject(root), 'top');
$('#vIso').onclick = () => fitView(new THREE.Box3().setFromObject(root), 'iso');
function setMode(m) { S.mode = m; $$('#vtools [data-mode]').forEach((b) => b.classList.toggle('on', b.dataset.mode === m)); attachGizmo(); }
$$('#vtools [data-mode]').forEach((b) => b.onclick = () => setMode(b.dataset.mode));
window.addEventListener('keydown', (e) => {
  if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
  if (e.ctrlKey && e.key === 'z') { api('undo', {}); e.preventDefault(); }
  else if (e.ctrlKey && e.key === 'y') { api('redo', {}); e.preventDefault(); }
  else if (e.key === 'q') setMode('select'); else if (e.key === 'w') setMode('translate'); else if (e.key === 'e') setMode('rotate');
  else if (e.key === 'Delete' && S.selected) patch([{ op: 'remove', id: S.selected }], 'удалён ' + S.selected);
  else if (e.key === 'f' && S.selected) { const b = new THREE.Box3(); (S.meshesById.get(S.selected) || []).forEach((m) => b.expandByObject(m)); fitView(b, 'iso'); }
});
function showTab(where, tab) {
  $$(`.tabs[data-for="${where}"] button`).forEach((b) => b.classList.toggle('on', b.dataset.tab === tab));
  const parent = where === 'left' ? $('#left') : $('#bottom');
  parent.querySelectorAll(':scope > .pane').forEach((p) => p.classList.toggle('on', p.dataset.pane === tab));
}
$$('.tabs button').forEach((b) => b.onclick = () => showTab(b.parentElement.dataset.for, b.dataset.tab));
$('#libSearch').oninput = renderLib;
$('#lightbox').onclick = () => { $('#lightbox').hidden = true; };

function showCheck(rep) {
  S.highlight = new Set((rep.floating || []).flatMap((f) => f.elements));
  applyHighlights();
  const errs = rep.errors || [];
  $('#check').innerHTML = (rep.ok ? '<div class="okline">✓ Модель цельная: нет висящих частей и ошибок</div>' : `<div class="badline">✗ Проблем: ${errs.length}</div>`)
    + `<div class="hint">Треугольников: ${rep.triangles?.toLocaleString('ru')} (после оптимизации ${rep.triangles_optimized?.toLocaleString('ru') ?? '—'}) · компонентов ${rep.components} · размер ${rep.bbox?.size?.join(' × ')} м · замкнутая (watertight): да</div>`
    + '<ul>' + errs.map((e) => `<li data-id="${esc((e.elements || [e.id])[0] || '')}">${esc(e.error)} — ${esc((e.elements || [e.id]).join(', '))}${e.center ? ' @ ' + e.center.join(', ') : ''}</li>`).join('') + '</ul>'
    + (rep.info || []).map((i) => `<div class="hint">${esc(JSON.stringify(i))}</div>`).join('');
  $$('#check li').forEach((li) => li.onclick = () => li.dataset.id && select(li.dataset.id));
  showTab('bottom', 'check');
}

// ---------------------------------------------------------------- live feed
const KIND_RU = { updated: 'изменение', render: 'скриншоты', validated: 'проверка', exported: 'экспорт', textures: 'текстуры',
  note: 'ИИ пишет', camera: 'камера', error: 'ошибка', hello: 'связь' };
function feedLine(ev) {
  const li = document.createElement('li');
  const t = new Date((ev.t || Date.now() / 1000) * 1000).toLocaleTimeString('ru');
  const bad = ev.type === 'error' || (ev.errors && ev.errors.length) || ev.ok === false;
  li.innerHTML = `<time>${t}</time><span class="ag ${esc(ev.agent)}">${esc(ev.agent || '?')}</span><span class="k">${KIND_RU[ev.type] || ev.type}</span>`
    + `<span class="${bad ? 'bad' : ''}">${esc(ev.note || '')}${ev.errors && ev.errors.length ? ' · ошибок: ' + ev.errors.length + ' (' + esc(ev.errors.map((e) => e.id).slice(0, 4).join(', ')) + ')' : ''}</span>`;
  const f = $('#feed'); f.prepend(li);
  while (f.children.length > 300) f.lastChild.remove();
}
function addShot(url) {
  const img = document.createElement('img'); img.src = url + '?t=' + Date.now();
  img.onclick = () => { $('#lightbox img').src = img.src; $('#lightbox').hidden = false; };
  $('#shots').prepend(img);
}
function connect() {
  const ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onmessage = async (m) => {
    const ev = JSON.parse(m.data);
    if (ev.type === 'hello') return;
    feedLine(ev);
    if (ev.type === 'updated') {
      // flash elements the change touched
      const ids = (ev.note || '').match(/[+*~]([\w/]+)/g)?.map((s) => s.slice(1)) || [];
      await refreshAll();
      if (ids.length) { S.highlight = new Set(ids); applyHighlights(); setTimeout(() => { S.highlight.clear(); applyHighlights(); }, 1500); }
    } else if (ev.type === 'render') { addShot(ev.url); if (ev.agent !== 'user') playCameras(ev.cameras, ev.center); }
    else if (ev.type === 'validated') { S.highlight = new Set(ev.highlight || []); applyHighlights(); }
    else if (ev.type === 'camera' && $('#chkFollow').checked) {
      const c = ev.camera, box = new THREE.Box3().setFromObject(root), ctr = c.target ? toThree(c.target) : box.getCenter(new THREE.Vector3());
      const r = box.getSize(new THREE.Vector3()).length() / 2, d = c.dist || r / Math.sin(THREE.MathUtils.degToRad(22)) * 1.1;
      const a = THREE.MathUtils.degToRad(c.az ?? -45), e = THREE.MathUtils.degToRad(c.el ?? 25);
      camAnimTo(toThree([ctr.x + d * Math.cos(e) * Math.cos(a), -ctr.z + d * Math.cos(e) * Math.sin(a), ctr.y + d * Math.sin(e)]), ctr);
    }
  };
  ws.onclose = () => setTimeout(connect, 1500);
}

// ---------------------------------------------------------------- start
(async () => {
  loop();
  [S.catalog, S.styles] = await Promise.all([api('catalog/elements'), api('catalog/styles')]);
  renderLib(); renderStyles();
  await refreshAll(true);
  connect();
})();
