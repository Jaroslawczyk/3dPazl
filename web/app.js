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
    const realistic = (S.state?.detail || 'realistic') === 'realistic';
    if (realistic && !S.texAvail) S.texAvail = await api('textures/available').catch(() => ({}));
    gltf.scene.traverse((o) => {
      if (!o.isMesh) return;
      const name = o.name || o.parent?.name || '';
      if (name.startsWith('overlay|')) { setupOverlay(o, name.slice(8)); return; }
      o.castShadow = o.receiveShadow = true;
      if (!o.geometry.attributes.normal) o.geometry.computeVertexNormals();
      const id = welded ? null : name.split('|')[0].replaceAll('~', '/');
      o.userData.eid = id;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      mats.forEach((m) => {
        m.flatShading = !realistic; m.side = THREE.FrontSide; m.wireframe = $('#chkWire').checked;
        if (realistic && !welded) applyTextures(m);
        m.needsUpdate = true;
      });
      if (id) { if (!S.meshesById.has(id)) S.meshesById.set(id, []); S.meshesById.get(id).push(o); }
    });
    root.add(gltf.scene);
    applyHighlights();
    applyClip();
    const box = new THREE.Box3().setFromObject(root);
    if (fit || !S.lastCenter) fitView(box, 'iso');
    S.lastCenter = box.getCenter(new THREE.Vector3());
    const tris = countTris();
    $('#status').textContent = `v${S.state?.version ?? '?'} · элементов ${S.tree.length} · треугольников ${tris.toLocaleString('ru')} · ${welded ? 'цельная сварная модель' : 'разборный режим'}`;
  } catch (e) { feedLine({ type: 'error', agent: 'ui', note: e.message }); }
  loading = false; $('#busy').hidden = true;
  if (pendingReload) { pendingReload = false; reloadModel(); }
}
// ---------------------------------------------------------------- textures, overlays, interior illusion
const texLoader = new THREE.TextureLoader();
const texCache = new Map();
function tex(name, kind, srgb) {
  const key = name + '/' + kind;
  if (!texCache.has(key)) {
    const t = texLoader.load(`/tex/${encodeURIComponent(name)}/${kind}`);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.anisotropy = 8;
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    texCache.set(key, t);
  }
  return texCache.get(key);
}
function applyTextures(m) {
  // material name: "brick_red" or painted "brick_red#aa3322" (tint = paint colour)
  const [base, hex] = (m.name || '').split('#');
  const have = S.texAvail?.[base];
  if (!have || !have.includes('albedo')) return;
  m.map = tex(base, 'albedo', true);
  m.color.set(hex ? '#' + hex : '#ffffff');
  if (have.includes('normal')) m.normalMap = tex(base, 'normal');
  if (have.includes('roughness')) { m.roughnessMap = tex(base, 'roughness'); m.roughness = 1; }
  if (have.includes('ao')) { m.aoMap = tex(base, 'ao'); m.aoMapIntensity = 0.8; }
}
const INTERIOR_VS = `#include <clipping_planes_pars_vertex>
varying vec2 vUv; varying vec3 vPos; varying vec3 vN;
void main(){ vUv = uv; vec4 wp = modelMatrix * vec4(position, 1.0); vPos = wp.xyz;
  vN = normalize(mat3(modelMatrix) * normal); vec4 mvPosition = viewMatrix * wp;
  gl_Position = projectionMatrix * mvPosition;
  #include <clipping_planes_vertex>
}`;
const INTERIOR_FS = `#include <clipping_planes_pars_fragment>
uniform sampler2D map; uniform float depth; varying vec2 vUv; varying vec3 vPos; varying vec3 vN;
void main(){
  #include <clipping_planes_fragment>
  vec3 N = normalize(vN); vec3 up = vec3(0.0, 1.0, 0.0);
  vec3 T = normalize(cross(up, N)); vec3 B = normalize(cross(N, T));
  vec3 V = normalize(vPos - cameraPosition);
  vec3 d = vec3(dot(V, T), dot(V, B), dot(V, N));       // ray into the room, tangent space
  vec3 o = vec3(vUv, 0.0);
  float tx = d.x > 0.0 ? (1.0 - o.x) / d.x : -o.x / min(d.x, -1e-4);
  float ty = d.y > 0.0 ? (1.0 - o.y) / d.y : -o.y / min(d.y, -1e-4);
  float tz = -depth / min(d.z, -1e-4);
  float t = min(min(tx, ty), tz);
  vec3 h = o + d * t;                                   // hit point on wall/floor/ceiling/back
  float k = clamp(-h.z / depth, 0.0, 1.0);
  float s = 1.0 / (1.0 + 1.27 * k);                     // one-point perspective of the room picture
  vec2 puv = vec2(0.5) + (h.xy - vec2(0.5)) * s;
  vec3 c = texture2D(map, puv).rgb * (1.0 - 0.25 * k);
  gl_FragColor = vec4(c, 1.0);
  #include <colorspace_fragment>
}`;
function setupOverlay(o, mat) {
  const isDecal = mat.startsWith('decal_');
  o.userData.overlay = isDecal ? 'decal' : 'interior';
  o.castShadow = false; o.receiveShadow = !isDecal ? false : true;
  const map = tex(mat, 'albedo', true);
  map.wrapS = map.wrapT = THREE.ClampToEdgeWrapping;
  if (isDecal) {
    o.material = new THREE.MeshStandardMaterial({ map, transparent: true, depthWrite: false, roughness: 0.95,
      polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
    o.visible = $('#chkDecals').checked;
  } else {
    o.geometry.computeVertexNormals();
    o.material = $('#chkParallax').checked
      ? new THREE.ShaderMaterial({ uniforms: { map: { value: map }, depth: { value: 1.0 } }, vertexShader: INTERIOR_VS,
        fragmentShader: INTERIOR_FS, clipping: true })
      : new THREE.MeshBasicMaterial({ map });
    o.visible = $('#chkInteriors').checked;
  }
  o.renderOrder = isDecal ? 2 : 0;
}
function setOverlayVisibility() {
  root.traverse((o) => {
    if (o.userData.overlay === 'decal') o.visible = $('#chkDecals').checked;
    if (o.userData.overlay === 'interior') o.visible = $('#chkInteriors').checked;
  });
}
// height cut to look inside
renderer.localClippingEnabled = true;
const clipPlane = new THREE.Plane(new THREE.Vector3(0, -1, 0), 1e6);
function applyClip() {
  const v = Number($('#rngClip').value);
  const box = new THREE.Box3().setFromObject(root);
  const cut = box.isEmpty() ? Infinity : box.min.y + (box.max.y - box.min.y) * v / 100;
  renderer.clippingPlanes = v >= 100 || box.isEmpty() ? [] : [clipPlane];
  clipPlane.constant = cut;
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
  const [st1, st2] = String(S.state.style || 'generic').split('+');
  $('#selStyle').value = st1; $('#selStyle2').value = st2 || '';
  $('#chkInteriors').checked = S.state.interiors !== false; $('#chkDecals').checked = S.state.decals !== false;
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
const RANDOM_KEYS = new Set(['floors', 'upper_floors', 'sections', 'count', 'levels', 'tiers', 'storeys']);
function fieldHtml(key, spec, val) {
  const v = val === undefined ? spec.default : val;
  const desc = spec.desc ? `<div class="desc">${esc(spec.desc)}</div>` : '';
  let inp;
  if (RANDOM_KEYS.has(key) && (typeof spec.default === 'number' || spec.default === null || (v && typeof v === 'object' && !Array.isArray(v)))) {
    // число / диапазон (случайно одно значение) / микс (своё значение для каждой секции/копии)
    const mode = v && typeof v === 'object' ? (v.mix ? 'mix' : 'rand') : 'num';
    const a = mode === 'num' ? (v ?? '') : (v.mix || v.rand)[0], b = mode === 'num' ? '' : (v.mix || v.rand)[1];
    inp = `<div class="floors-ctl" data-k="${key}" data-rnd="1"><select><option value="num" ${mode === 'num' ? 'selected' : ''}>число</option>`
      + `<option value="rand" ${mode === 'rand' ? 'selected' : ''}>диапазон</option><option value="mix" ${mode === 'mix' ? 'selected' : ''}>микс</option></select>`
      + `<input type="number" step="any" value="${a}" placeholder="авто"><input type="number" step="any" value="${b}" ${mode === 'num' ? 'hidden' : ''} placeholder="до"></div>`;
    return `<div class="prop"><label title="${esc(key)}">${esc(key)}</label>${inp}${desc}</div>`;
  }
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
    if (el.dataset.rnd) {
      const [sel, a, b] = el.querySelectorAll('select, input');
      const na = a.value === '' ? null : Number(a.value), nb = b.value === '' ? na : Number(b.value);
      const intish = Number.isInteger(na) && Number.isInteger(nb);
      v = sel.value === 'num' || na === null ? na : { [sel.value]: [intish ? na : na, intish ? nb : nb] };
      const def = spec.default;
      if (JSON.stringify(v) !== JSON.stringify(def)) out[k] = v;
      return;
    }
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
    + fieldHtml('style', { default: null, desc: 'свой стиль элемента, можно микс: "gothic+baroque"' }, src.style)
    + `</fieldset><fieldset id="pf"><legend>Параметры</legend>${Object.entries(schema).map(([k, s]) => fieldHtml(k, s, params[k])).join('')}</fieldset>`
    + facadeHtml(info) + paintHtml(src) + planHtml(info)
    + `<div class="row"><button id="pApply" class="on">Применить</button><button id="pDup">Дублировать</button>`
    + `${isGroup && info.in_recipe ? '<button id="pExplode" title="Разобрать макрос на обычные элементы">Разобрать</button>' : ''}`
    + `<button id="pDel">Удалить</button><button id="pAnch">Якоря</button></div><div id="anchList"></div>`;
  const posSpecs = { on: { default: null }, at: { default: null }, offset: { default: null }, rot: { default: 0 }, repeat: { default: null }, style: { default: null } };
  wireExtras(id, info);
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

// facade tool, paint, floor plan
const WIN_KINDS = ['rect', 'arch', 'segmental', 'lancet', 'round', 'horseshoe', 'ogee', 'ribbon', 'slit'];
const TRIMS = ['simple', 'none', 'classic', 'pediment', 'baroque', 'gothic_hood', 'nalichnik', 'archivolt', 'rustic', 'soviet'];
function facadeHtml(info) {
  if (!info.faces?.length) return '';
  return `<fieldset id="fac"><legend>Фасад: окна на стороне</legend>`
    + `<div class="prop"><label>сторона</label><select id="facFace">${['all', ...info.faces.filter((f) => !/^face\d/.test(f) || info.faces.length < 5)].map((f) => `<option value="${f}">${f === 'all' ? 'все стороны' : f}</option>`).join('')}</select></div>`
    + `<div class="prop"><label>окна</label><select id="facKind"><option value="none">без окон</option>${WIN_KINDS.map((k) => `<option>${k}</option>`).join('')}</select></div>`
    + `<div class="prop"><label>наличник</label><select id="facTrim">${TRIMS.map((k) => `<option>${k}</option>`).join('')}</select></div>`
    + `<div class="prop"><label>ширина × высота</label><div class="floors-ctl"><input id="facW" type="number" step="0.1" value="1.2"><input id="facH" type="number" step="0.1" value="1.5"></div></div>`
    + `<div class="row"><button id="facApply">Заменить окна</button></div></fieldset>`;
}
const PAINT_ROLES = ['wall', 'roof', 'trim', 'frame', 'door', 'plinth'];
const ROLE_RU = { wall: 'стены', roof: 'крыша', trim: 'декор', frame: 'рамы', door: 'двери', plinth: 'цоколь' };
function paintHtml(src) {
  const c = src.colors || {};
  return `<fieldset id="pnt"><legend>Покраска (low-poly — цвет, реализм — тон текстуры)</legend><div class="paint-row">`
    + PAINT_ROLES.map((r) => `<label>${ROLE_RU[r]}<input type="color" data-role="${r}" value="${c[r] || '#d8d4cc'}" data-set="${c[r] ? 1 : ''}"></label>`).join('')
    + `</div><div class="row"><button id="pntApply">Покрасить</button><button id="pntRand">🎲 Случайно</button><button id="pntClear">Сбросить</button></div></fieldset>`;
}
const ROOM_COL = { living: '#c98f6a', bedroom: '#7d9ac9', kitchen: '#c9b46a', bath: '#6ac9c2', wc: '#6ac9c2', corridor: '#555',
  stairs: '#999', elevator: '#bbb', office: '#7dc98f', meeting: '#c97db8', classroom: '#9ac97d', nave: '#b89a6a', hall: '#b89a6a' };
function planHtml(info) {
  const plan = info.info?.plan;
  if (!plan?.length) return '';
  const floors = [...new Set(plan.map((r) => r.floor))];
  const s = info.info.summary || {};
  return `<fieldset class="plan"><legend>План этажей (${esc(info.info.program)})</legend><div class="hint">комнат ${s.rooms} · лестница ${s.stairs} · лифт ${s.elevator ? 'да' : 'нет'}</div>`
    + `<select id="planFloor">${floors.map((f) => `<option value="${f}">этаж ${f + 1}</option>`).join('')}</select><div id="planSvg"></div></fieldset>`;
}
function drawPlan(plan, f) {
  const rooms = plan.filter((r) => r.floor === f);
  const W = Math.max(...rooms.map((r) => r.rect[2])), H = Math.max(...rooms.map((r) => r.rect[3]));
  $('#planSvg').innerHTML = `<svg viewBox="-0.5 -0.5 ${W + 1} ${H + 1}">` + rooms.map((r) => {
    const [x0, y0, x1, y1] = r.rect;
    return `<rect x="${x0}" y="${H - y1}" width="${x1 - x0}" height="${y1 - y0}" fill="${ROOM_COL[r.name] || '#888'}" fill-opacity="0.75" stroke="#111" stroke-width="0.12"/>`
      + `<text x="${(x0 + x1) / 2}" y="${H - (y0 + y1) / 2}" text-anchor="middle">${esc(r.name_ru || r.name)}</text>`;
  }).join('') + '</svg>';
}
function wireExtras(id, info) {
  $$('.floors-ctl[data-rnd] select').forEach((sel) => sel.onchange = () => {
    sel.parentElement.querySelectorAll('input')[1].hidden = sel.value === 'num';
  });
  if ($('#facApply')) $('#facApply').onclick = () => {
    const kind = $('#facKind').value;
    const win = kind === 'none' ? 'none' : { kind, trim: $('#facTrim').value, w: Number($('#facW').value), h: Number($('#facH').value) };
    patch([{ op: 'facade', id, face: $('#facFace').value, windows: win }], `фасад ${id}:${$('#facFace').value}`);
  };
  if ($('#pntApply')) {
    $$('#pnt input[type=color]').forEach((i) => i.oninput = () => { i.dataset.set = '1'; });
    $('#pntApply').onclick = () => {
      const colors = {}; $$('#pnt input[type=color]').forEach((i) => { if (i.dataset.set) colors[i.dataset.role] = i.value; });
      patch([{ op: 'paint', id, colors }], 'покраска ' + id);
    };
    $('#pntRand').onclick = () => patch([{ op: 'paint_random', ids: [id] }], 'случайная покраска ' + id);
    $('#pntClear').onclick = () => patch([{ op: 'paint', id, colors: null }], 'покраска сброшена');
  }
  if ($('#planFloor')) {
    const plan = info.info.plan;
    $('#planFloor').onchange = (e) => drawPlan(plan, Number(e.target.value));
    drawPlan(plan, plan[0].floor);
  }
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
// library filters: epoch chips (multi) + territory
S.periodSel = new Set();
function stylesFiltered() {
  const reg = $('#regionSel').value;
  return S.styles.filter((s) => (!S.periodSel.size || (s.periods || []).some((p) => S.periodSel.has(p)))
    && (!reg || (s.regions || []).includes(reg) || (s.regions || []).includes('global')));
}
function renderFilters() {
  $('#periodChips').innerHTML = S.periods.periods.map((p) => `<button data-p="${p.id}" class="${S.periodSel.has(p.id) ? 'on' : ''}" title="${p.from}…${p.to}">${esc(p.name_ru)}</button>`).join('');
  $$('#periodChips button').forEach((b) => b.onclick = () => {
    S.periodSel.has(b.dataset.p) ? S.periodSel.delete(b.dataset.p) : S.periodSel.add(b.dataset.p);
    renderFilters(); renderLib(); renderStyles(false);
  });
}
function renderLib() {
  const q = $('#libSearch').value.toLowerCase();
  const groups = {};
  const filtering = S.periodSel.size || $('#regionSel').value;
  const allowed = new Set(stylesFiltered().flatMap((s) => s.macros || []));
  S.catalog.forEach((c) => {
    const text = (c.type + ' ' + (c.title_ru || '') + ' ' + c.desc).toLowerCase();
    if (q && !text.includes(q)) return;
    if (filtering && c.macro && !allowed.has(c.type)) return;
    (groups[c.category] ||= []).push(c);
  });
  $('#lib').innerHTML = Object.keys(CAT_RU).filter((k) => groups[k]).map((k) => `<div class="cat">${CAT_RU[k]}</div>`
    + groups[k].map((c) => `<div class="lib-item" data-t="${c.type}"><b>${esc(c.title_ru || c.type)}</b> <span class="t">${c.type}</span><small>${esc(c.desc.slice(0, 110))}</small></div>`).join('')).join('');
  $$('#lib .lib-item').forEach((d) => d.onclick = () => showAdd(d.dataset.t));
}
function renderStyles(selects = true) {
  if (selects) {
    const opts = S.styles.map((s) => `<option value="${s.id}">${esc(s.name_ru || s.name)}</option>`).join('');
    $('#selStyle').innerHTML = opts;
    $('#selStyle2').innerHTML = '<option value="">—</option>' + opts;
  }
  const yrs = (s) => s.years ? `${s.years[0] < 0 ? -s.years[0] + ' до н.э.' : s.years[0]}–${s.years[1] > 2025 ? 'н.в.' : s.years[1]}` : '';
  $('#styles').innerHTML = (S.periodSel.size || $('#regionSel').value ? '<div class="hint">Фильтр: эпоха / территория (вкладка «Библиотека»)</div>' : '')
    + stylesFiltered().map((s) => `<div class="style-card"><h4>${esc(s.name_ru || s.name)}</h4><small>${esc(yrs(s))} · ${esc(s.region || '')}</small>`
    + `<div class="hint">${esc(s.tips || '')}</div><div class="row">${(s.macros || []).map((m) => `<button data-m="${m}" data-s="${s.id}">+ ${m}</button>`).join('')}`
    + `<button data-apply="${s.id}">Применить стиль</button><button data-mixin="${s.id}" title="Добавить к текущему стилю как второй">+ к миксу</button></div></div>`).join('');
  $$('#styles [data-mixin]').forEach((b) => b.onclick = () => {
    const cur = String(S.state.style || 'generic').split('+')[0];
    patch([{ op: 'set', key: 'style', value: cur === b.dataset.mixin ? cur : cur + '+' + b.dataset.mixin }], 'микс стилей');
  });
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
const styleValue = () => $('#selStyle').value + ($('#selStyle2').value && $('#selStyle2').value !== $('#selStyle').value ? '+' + $('#selStyle2').value : '');
$('#selStyle').onchange = () => patch([{ op: 'set', key: 'style', value: styleValue() }], 'стиль ' + styleValue());
$('#selStyle2').onchange = () => patch([{ op: 'set', key: 'style', value: styleValue() }], 'микс стилей ' + styleValue());
$('#btnPaint').onclick = () => patch([{ op: 'paint_random' }], 'случайная покраска фасадов');
$('#btnReroll').onclick = () => patch([{ op: 'reroll' }], 'новый сид случайностей');
$('#btnInterior').onclick = async () => {
  await patch([{ op: 'interior_all' }], 'интерьер для всех объёмов');
  $('#rngClip').value = 40; applyClip();
  feedLine({ type: 'note', agent: 'ui', note: 'Интерьер создан. Ползунок «Срез» показывает этажи изнутри; план — в свойствах элемента interior.' });
};
$('#btnWeather').onclick = () => patch([{ op: 'weather_all', amount: 0.6 }], 'состаривание');
$('#chkInteriors').onchange = () => { setOverlayVisibility(); patch([{ op: 'set', key: 'interiors', value: $('#chkInteriors').checked }], 'интерьеры за окнами'); };
$('#chkDecals').onchange = () => { setOverlayVisibility(); patch([{ op: 'set', key: 'decals', value: $('#chkDecals').checked }], 'декали'); };
$('#chkParallax').onchange = () => reloadModel();
$('#rngClip').oninput = applyClip;
$('#regionSel').onchange = () => { renderLib(); renderStyles(false); };
$('#selTextures').onchange = async (e) => {
  const v = e.target.value; e.target.value = '';
  if (v === 'prompts') {
    const m = await api('textures/manifest', {});
    feedLine({ type: 'textures', agent: 'ui', note: `${m.materials.length} материалов. Промпты: ${m.prompts_md}. Положите PNG в указанные папки.` });
  } else if (v) {
    await api('textures/download', { which: v === 'dl_all' ? 'all' : 'project' });
    S.texAvail = null;
  }
  showTab('bottom', 'feed');
};
$$('#segDetail button').forEach((b) => b.onclick = () => patch([{ op: 'set', key: 'detail', value: b.dataset.v }], 'детализация ' + b.dataset.v));
$('#btnValidate').onclick = () => api('validate', {}).then(showCheck);
$('#btnRender').onclick = async () => { $('#busy').hidden = false; try { await api('render', {}); } finally { $('#busy').hidden = true; } };
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
    else if (ev.type === 'textures' && ev.downloaded) { S.texAvail = null; texCache.clear(); reloadModel(); }
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
  [S.catalog, S.styles, S.periods] = await Promise.all([api('catalog/elements'), api('catalog/styles'), api('catalog/periods')]);
  $('#regionSel').innerHTML = '<option value="">Все территории</option>' + Object.entries(S.periods.regions).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('');
  renderFilters();
  renderLib(); renderStyles();
  await refreshAll(true);
  connect();
})();
