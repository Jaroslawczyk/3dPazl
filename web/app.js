import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { TransformControls } from 'three/addons/controls/TransformControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { LANG, LANGS, initI18n, setLang } from './i18n.js';

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
// logarithmic depth: mm-level depth precision at any distance -> coplanar-ish faces and decals don't flicker
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, logarithmicDepthBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.autoUpdate = false; // shadows are static: re-rendered only when the model/light changes
vp.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const cssVar = (n, d) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || d;
scene.background = new THREE.Color(cssVar('--sky', '#9fb4c8'));
scene.fog = new THREE.Fog(scene.background.getHex(), 300, 1200);
const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 5000);
camera.position.set(30, 22, 30);
const orbit = new OrbitControls(camera, renderer.domElement);
orbit.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xdde8ff, 0x6a6458, 1.4));
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(-60, 100, 50); sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.bias = -0.0005; sun.shadow.normalBias = 0.03; // no shadow acne (striped flicker on walls)
Object.assign(sun.shadow.camera, { left: -120, right: 120, top: 120, bottom: -120, far: 500 });
scene.add(sun); scene.add(sun.target);
const ground = new THREE.Mesh(new THREE.CircleGeometry(800, 64), new THREE.MeshStandardMaterial({ color: cssVar('--ground', '#77806f'), roughness: 1 }));
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
  renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix(); invalidate();
}
new ResizeObserver(resize).observe(vp);
// render on demand: an idle viewport costs nothing; any input / camera move / model change requests a frame
let dirty = true;
function invalidate(shadows = false) { dirty = true; if (shadows) renderer.shadowMap.needsUpdate = true; }
orbit.addEventListener('change', () => invalidate());
gizmo.addEventListener('change', () => invalidate());
for (const ev of ['pointerdown', 'pointermove', 'wheel', 'keydown'])
  document.addEventListener(ev, () => invalidate(), { passive: true, capture: true });
for (const ev of ['input', 'change', 'click'])  // UI toggles may change what casts shadows
  document.addEventListener(ev, () => invalidate(true), { passive: true, capture: true });
THREE.DefaultLoadingManager.onLoad = () => invalidate();
const modelBox = new THREE.Box3();
function updateClipRange() {
  // near/far hug the scene: keeps depth precision where the model is
  const box = modelBox;
  const r = box.isEmpty() ? 50 : box.getSize(new THREE.Vector3()).length() / 2;
  const d = box.isEmpty() ? camera.position.length() : camera.position.distanceTo(box.getCenter(new THREE.Vector3()));
  const near = THREE.MathUtils.clamp((d - r) * 0.5, 0.05, 10), far = Math.max(d + r * 4, 1500);
  if (Math.abs(camera.near - near) > near * 0.1 || camera.far !== far) {
    camera.near = near; camera.far = far; camera.updateProjectionMatrix();
  }
}
function loop() {
  requestAnimationFrame(loop);
  orbit.update(); tickCamAnim(); tickDoors(); tickBoom();
  if (!dirty && !camAnim) return;
  dirty = false;
  updateClipRange();
  renderer.render(scene, camera);
  drawMarks();
}

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
    root.traverse((o) => {  // free GPU memory of the previous model (otherwise every edit leaks and slows down)
      if (!o.isMesh) return;
      o.geometry.dispose();
      (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => m.dispose());
    });
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
      const door = name.startsWith('door|') ? o.parent : null;  // the hinge node: rotate it to open the leaf
      if (door) { door.userData.openDeg = Number(name.split('|')[3]) || -95; o.userData.door = door; }
      const id = door ? name.split('|')[1].replaceAll('~', '/') : welded ? null : name.split('|')[0].replaceAll('~', '/');
      o.userData.eid = id;
      // own material per mesh: glTF shares them by index, so highlighting one element lit up all of that material
      o.material = Array.isArray(o.material) ? o.material.map((m) => m.clone()) : o.material.clone();
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      mats.forEach((m) => {
        m.flatShading = !realistic; m.side = THREE.FrontSide; m.wireframe = $('#chkWire').checked;
        if (realistic && !welded) applyTextures(m);
        if ((m.name || '').split('#')[0].startsWith('glass') && m.transparent) { o.userData.glass = true; setGlass(m); }
        m.needsUpdate = true;
      });
      if (id) { if (!S.meshesById.has(id)) S.meshesById.set(id, []); S.meshesById.get(id).push(o); }
    });
    root.add(gltf.scene);
    applyHighlights();
    applyClip();
    const box = modelBox.setFromObject(root);
    if (!box.isEmpty()) {  // shadow frustum fitted to the model: sharper shadows, no acne
      const c = box.getCenter(new THREE.Vector3()), r = Math.max(10, box.getSize(new THREE.Vector3()).length() / 2 + 2);
      sun.target.position.copy(c);
      sun.position.copy(c).add(new THREE.Vector3(-60, 100, 50).normalize().multiplyScalar(r * 2));
      Object.assign(sun.shadow.camera, { left: -r, right: r, top: r, bottom: -r, near: 0.5, far: r * 4 });
      sun.shadow.camera.updateProjectionMatrix();
    }
    invalidate(true);
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
  const [mat, hex] = (m.name || '').split('#');
  if (S.state?.textures === false) return;
  const base = S.state?.tex_swap?.[mat] || mat;  // texture set swapped by the user
  const have = S.texAvail?.[base];
  if (!have || !have.includes('albedo')) return;
  m.map = tex(base, 'albedo', true);
  m.color.set(hex ? '#' + hex : '#ffffff');
  if (have.includes('normal')) m.normalMap = tex(base, 'normal');
  if (have.includes('roughness')) { m.roughnessMap = tex(base, 'roughness'); m.roughness = 1; }
  if (have.includes('ao')) { m.aoMap = tex(base, 'ao'); m.aoMapIntensity = 0.8; }
}
const INTERIOR_VS = `#include <common>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
varying vec2 vUv; varying vec3 vPos; varying vec3 vN;
void main(){ vUv = uv; vec4 wp = modelMatrix * vec4(position, 1.0); vPos = wp.xyz;
  vN = normalize(mat3(modelMatrix) * normal); vec4 mvPosition = viewMatrix * wp;
  gl_Position = projectionMatrix * mvPosition;
  #include <logdepthbuf_vertex>
  #include <clipping_planes_vertex>
}`;
const INTERIOR_FS = `#include <common>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
uniform sampler2D map; uniform float depth; varying vec2 vUv; varying vec3 vPos; varying vec3 vN;
void main(){
  #include <clipping_planes_fragment>
  #include <logdepthbuf_fragment>
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
    o.visible = winPlug();
  }
  o.renderOrder = isDecal ? 2 : 0;
}
// windows: "plug" = room picture behind slightly reflective glass; "glass" = clear glass, the real interior is visible
const winPlug = () => S.state?.interiors !== false;
function setGlass(m) {
  m.transparent = true; m.depthWrite = false;
  m.opacity = winPlug() ? 0.6 : 0.18;
}
function setOverlayVisibility() {
  root.traverse((o) => {
    if (o.userData.overlay === 'decal') o.visible = $('#chkDecals').checked;
    if (o.userData.overlay === 'interior') o.visible = winPlug();
    if (o.userData.glass) setGlass(o.material);
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
  invalidate();
  const k =Math.min(1, (performance.now() - camAnim.s) / camAnim.ms), e = k * k * (3 - 2 * k);
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
  if (S.marking) return;
  if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 4 || gizmo.dragging) return;
  const r = renderer.domElement.getBoundingClientRect();
  mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const hit = ray.intersectObjects(root.children, true)
    .find((h) => h.object.userData.eid && h.object.visible && (!renderer.clippingPlanes.length || clipPlane.distanceToPoint(h.point) >= 0));
  if (hit?.object.userData.door) toggleDoor(hit.object.userData.door);
  select(hit ? hit.object.userData.eid : null);
  pickFace(hit);
});

function applyHighlights() {
  root.traverse((o) => {
    if (!o.isMesh) return;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    const id = o.userData.eid;
    const col = id && id === S.selected ? 0x7a5a10 : (id && S.highlight.has(id) ? 0x8a0000 : 0x000000);
    mats.forEach((m) => { if (m.emissive) m.emissive.setHex(col); });
  });
  invalidate();
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
  invalidate(true);
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
  $('#chkRooms').checked = S.state.rooms !== false; $('#chkDecals').checked = S.state.decals !== false;
  $$('#segWin button').forEach((b) => b.classList.toggle('on', b.dataset.v === (winPlug() ? 'plug' : 'glass')));
  $$('#segDetail button').forEach((b) => b.classList.toggle('on', b.dataset.v === S.state.detail));
  $('#btnUndo').disabled = !S.state.can_undo; $('#btnRedo').disabled = !S.state.can_redo;
  renderTree();
  if (frac.group) fracReset();  // the model changed: old chunks are stale
  await reloadModel(fit);
  renderMats();
  renderBuild();
  $('#chkProps').checked = S.state.props !== false;
  renderUsage();
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
  columns: 'Колонны и портики', decor: 'Декор и фасад', primitive: 'Примитивы (любые формы)', props: 'Украшения и мелкие объекты' };
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
    + groups[k].map((c) => `<div class="lib-item" data-t="${c.type}"><b>${esc(ttl(c))}</b> <span class="t">${c.type}</span><small>${esc(c.desc.slice(0, 110))}</small></div>`).join('')).join('');
  $$('#lib .lib-item').forEach((d) => d.onclick = () => showAdd(d.dataset.t));
}
function renderStyles(selects = true) {
  if (selects) {
    const opts = styleOptions();
    $('#selStyle').innerHTML = opts;
    $('#selStyle2').innerHTML = '<option value="">—</option>' + opts;
  }
  const yrs = (s) => s.years ? `${s.years[0] < 0 ? -s.years[0] + ' до н.э.' : s.years[0]}–${s.years[1] > 2025 ? 'н.в.' : s.years[1]}` : '';
  $('#styles').innerHTML = (S.periodSel.size || $('#regionSel').value ? '<div class="hint">Фильтр: эпоха / территория (вкладка «Библиотека»)</div>' : '')
    + stylesFiltered().map((s) => `<div class="style-card"><h4>${esc(nm(s))}</h4><small>${esc(yrs(s))} · ${esc(s.region || '')}</small>`
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
$('#chkRooms').onchange = () => {
  const on = $('#chkRooms').checked;
  const have = S.tree.some((t) => t.type === 'interior');  // nothing generated yet -> create rooms for every volume
  patch([{ op: 'set', key: 'rooms', value: on }, ...(on && !have ? [{ op: 'interior_all' }] : [])], on ? 'интерьер включён' : 'интерьер выключен');
};
$$('#segWin button').forEach((b) => b.onclick = () => {
  S.state.interiors = b.dataset.v === 'plug';
  $$('#segWin button').forEach((x) => x.classList.toggle('on', x === b));
  setOverlayVisibility(); invalidate(true);
  patch([{ op: 'set', key: 'interiors', value: S.state.interiors }], b.dataset.v === 'plug' ? 'окна: затычка' : 'окна: прозрачные');
});
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
  if (v === 'open') return api('export/open', {}).catch((er) => feedLine({ type: 'error', agent: 'ui', note: er.message }));
  let body = { format: v };
  if ($('#chkExpSel').checked) {
    if (!S.selected) return alert('Сначала выберите элемент в сцене или в дереве.');
    body.only = [S.selected];
  }
  if (v === 'lod') { const n = Number(prompt('Целевое число треугольников:', '20000')); if (!n) return; body = { ...body, format: 'glb', lod_tris: n }; }
  let r = await api('export', body).catch((er) => ({ error: er.message }));
  if (r.error && confirm('Есть проблемы:\n' + JSON.stringify(r.problems || r.error).slice(0, 600) + '\n\nЭкспортировать всё равно?')) r = await api('export', { ...body, force: true });
  if (r.path) feedLine({ type: 'exported', agent: 'ui', note: 'Сохранено: ' + r.path + ` (${r.triangles} △)` });
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
// ---------------------------------------------------------------- materials: textures on/off, swaps, decal kinds
const DECAL_RU = { dirt: 'грязь', soot: 'копоть', moss: 'мох', rust: 'ржавчина', water_stain: 'подтёки', crack: 'трещины',
                   peeling: 'облупленная краска', graffiti: 'граффити', poster: 'плакаты', scuff: 'потёртости' };
async function renderMats() {
  if (!S.state) return;
  if (!S.texAvail) S.texAvail = await api('textures/available').catch(() => ({}));
  $('#chkTextures').checked = S.state.textures !== false;
  const off = new Set(S.state.decals_off || []);
  $('#decalKinds').innerHTML = Object.entries(DECAL_RU).map(([k, ru]) =>
    `<label class="chip ${off.has(k) ? '' : 'on'}"><input type="checkbox" data-k="${k}" ${off.has(k) ? '' : 'checked'}> ${ru}</label>`).join('');
  const used = new Set();
  root.traverse((o) => { if (o.isMesh && !o.userData.overlay) (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => m.name && used.add(m.name.split('#')[0])); });
  const avail = Object.keys(S.texAvail || {}).filter((k) => S.texAvail[k].includes('albedo')).sort();
  const swap = S.state.tex_swap || {};
  $('#matList').innerHTML = [...used].sort().map((m) => {
    const cur = swap[m] || '';
    const opts = [`<option value="">${S.texAvail?.[m] ? 'своя' : 'своя (нет файла)'}</option>`, `<option value="none" ${cur === 'none' ? 'selected' : ''}>без текстуры</option>`]
      .concat(avail.filter((a) => a !== m).map((a) => `<option ${cur === a ? 'selected' : ''}>${esc(a)}</option>`));
    return `<div class="row"><span>${esc(m)}</span><select data-m="${esc(m)}">${opts.join('')}</select></div>`;
  }).join('') || '<div class="hint">Нет материалов (включите «Реализм»).</div>';
}
$('#chkTextures').onchange = () => patch([{ op: 'set', key: 'textures', value: $('#chkTextures').checked }], $('#chkTextures').checked ? 'текстуры включены' : 'текстуры выключены');
$('#decalKinds').onchange = (e) => {
  const off = $$('#decalKinds input').filter((i) => !i.checked).map((i) => i.dataset.k);
  patch([{ op: 'set', key: 'decals_off', value: off }], 'декали: ' + (DECAL_RU[e.target.dataset.k] || '') + (e.target.checked ? ' вкл.' : ' выкл.'));
};
$('#matList').onchange = (e) => {
  const swap = { ...(S.state.tex_swap || {}) };
  if (e.target.value) swap[e.target.dataset.m] = e.target.value; else delete swap[e.target.dataset.m];
  patch([{ op: 'set', key: 'tex_swap', value: swap }], `текстура ${e.target.dataset.m} → ${e.target.value || 'своя'}`);
};

// ---------------------------------------------------------------- faces: click picks the plane of a wall / roof top
const faceMat = new THREE.MeshBasicMaterial({ color: 0xe0a84a, transparent: true, opacity: 0.28, depthWrite: false, side: THREE.DoubleSide });
const faceMesh = new THREE.Mesh(new THREE.BufferGeometry(), faceMat);
faceMesh.renderOrder = 5; faceMesh.visible = false;
scene.add(faceMesh);
const v3 = (a) => new THREE.Vector3(...a);
async function faceOf(eid, p, n) {  // p, n in Z-up coords -> best face anchor of eid, or null
  let an;
  try { an = await api('anchors/' + encodeURI(eid)); } catch { return null; }
  let best = null;
  for (const [name, a] of Object.entries(an)) {
    if (a.kind === 'top' && n.z > 0.8 && name === 'top') best = best || { name, a, score: 9 };
    if (a.kind !== 'face' || /^face\d+$/.test(name) === false && !['front', 'back', 'left', 'right', 'face'].includes(name)) continue;
    const N = v3(a.normal), up = new THREE.Vector3(0, 0, 1), X = up.clone().cross(N).normalize();
    if (n.dot(N) < 0.85) continue;
    const d = p.clone().sub(v3(a.origin)), u = d.dot(X), v = d.dot(up), off = d.dot(N);
    if (off < -a.depth - 0.6 || off > 0.7 || u < -0.4 || u > a.w + 0.4 || v < -1 || v > a.h + 1) continue;
    const score = Math.abs(off) + (/^face\d+$/.test(name) ? 0.001 : 0);  // prefer front/back/... names
    if (!best || score < best.score) best = { name, a, u, v, X, N, score };
  }
  return best;
}
async function pickFace(hit) {
  S.face = null; faceMesh.visible = false; $('#faceBox').hidden = true;
  if (!hit) return invalidate();
  const eid = hit.object.userData.eid;
  const n3 = hit.face.normal.clone().transformDirection(hit.object.matrixWorld);
  const p = v3(toCore(hit.point)), n = new THREE.Vector3(n3.x, -n3.z, n3.y);
  let f = await faceOf(eid, p, n), owner = eid;
  if (!f) {  // a window / door / decor piece: the face it sits on
    const on = S.tree.find((t) => t.id === eid)?.on;
    if (on && on.includes(':')) { owner = on.split(':')[0]; f = await faceOf(owner, p, n); }
  }
  if (!f || S.selected !== eid) return invalidate();
  S.face = { eid: owner, name: f.name, a: f.a, u: f.u, v: f.v, point: hit.point.clone() };
  if (f.a.kind === 'face') {
    const o = v3(f.a.origin).add(f.N.clone().multiplyScalar(0.04));
    const c = [[0, 0], [f.a.w, 0], [f.a.w, f.a.h], [0, f.a.h]].map(([u, v]) => { const q = o.clone().add(f.X.clone().multiplyScalar(u)); q.z += v; return toThree([q.x, q.y, q.z]); });
    faceMesh.geometry.dispose();
    faceMesh.geometry = new THREE.BufferGeometry().setFromPoints([c[0], c[1], c[2], c[0], c[2], c[3]]);
    faceMesh.visible = true;
  }
  renderFace(); invalidate();
}
function faceElems(f) { return S.tree.filter((t) => t.on === `${f.eid}:${f.name}`); }
function renderFace() {
  const f = S.face, box = $('#faceBox');
  if (!f) { box.hidden = true; return; }
  const size = f.a.kind === 'face' ? `${f.a.w.toFixed(1)} × ${f.a.h.toFixed(1)} м` : 'верх (крыша / площадка)';
  const here = faceElems(f);
  const faceTypes = S.catalog.filter((c) => c.attach === 'face' || (f.a.kind === 'top' && c.attach === 'top'));
  box.innerHTML = `<h3>Грань</h3><div class="face-head"><b>${esc(f.eid)}</b> · ${esc(f.name)} <span class="hint">${size}</span></div>
    ${here.length ? `<div class="hint">На грани: ${here.map((t) => esc(t.id.split('/').pop()) + ' <i>' + esc(t.type) + '</i>').join(', ')}</div>` : ''}
    ${f.a.kind === 'face' ? `<label class="row">Окна <select id="faceWin"><option value="">—</option><option value="none">убрать окна</option>
      <option value="all">все окна</option><option value="random">случайно (часть заложена)</option><option value="symmetric">случайно, симметрично</option>
      <option value="checker">шахматка</option><option value="alternate">через одно</option><option value="formula">по формуле…</option></select></label>` : ''}
    <div class="row"><select id="faceAddType">${faceTypes.map((c) => `<option value="${c.type}">${esc(ttl(c))}</option>`).join('')}</select>
      <button id="faceAdd" title="Добавить на эту грань в место клика">+ сюда</button></div>
    <div class="row"><button id="faceAsk" class="act" title="Пометка на этой грани: ИИ поменяет только её">💬 ИИ: изменить эту грань</button>
      <button id="faceClose" title="Снять выделение грани">✕</button></div>`;
  box.hidden = false;
  $('#faceClose').onclick = () => { S.face = null; faceMesh.visible = false; box.hidden = true; invalidate(); };
  $('#faceAdd').onclick = () => {
    const type = $('#faceAddType').value, at = f.a.kind === 'face' ? [+f.u.toFixed(2), +Math.max(0, f.v).toFixed(2)] : undefined;
    const el = { id: type, type, on: `${f.eid}:${f.name}` };
    if (at && !['windows', 'timber_frame', 'weathering', 'panel_grid'].includes(type)) el.at = type === 'window' || type === 'door' ? at : at;
    patch([{ op: 'add', element: el }], `+${type} на ${f.eid}:${f.name}`);
  };
  $('#faceAsk').onclick = () => {
    S.marks.push({ kind: 'point', pts: [f.point], eids: [f.eid, ...faceElems(f).map((t) => t.id)], note: '', face: `${f.eid}:${f.name}` });
    renderMarks(); invalidate();
    setTimeout(() => $(`#markList input[data-i="${S.marks.length - 1}"]`)?.focus(), 0);
  };
  const fw = $('#faceWin');
  if (fw) fw.onchange = () => {
    const mode = fw.value; if (!mode) return;
    const grids = faceElems(f).filter((t) => t.type === 'windows');
    let formula;
    if (mode === 'formula') { formula = prompt('Формула: c — столбец, r — ряд (с 0), cols, rows. Истина = окно. Например: (c + r) % 2 == 0', '(c + r) % 2 == 0'); if (!formula) return; }
    const pr = { fill: mode, ...(formula ? { fill_formula: formula } : {}) };
    const ops = mode === 'none' ? [{ op: 'facade', id: f.eid, face: f.name, windows: 'none' }]
      : grids.length ? grids.map((t) => ({ op: 'update', id: t.id, params: pr })) : [{ op: 'facade', id: f.eid, face: f.name, windows: pr }];
    patch(ops, `окна на ${f.eid}:${f.name}: ${mode}`);
  };
}

// ---------------------------------------------------------------- whole-project buttons: window fill, building shapes
$('#selWinFill').onchange = async (e) => {
  const mode = e.target.value; e.target.value = '';
  if (!mode) return;
  let formula;
  if (mode === 'formula') { formula = prompt('Формула для всех сеток окон. c — столбец, r — ряд (с 0), cols, rows, n. Истина = окно.\nПримеры: (c + r) % 2 == 0 · c in (0, cols - 1) · r > 0 and c % 3 != 1', 'c % 3 != 1'); if (!formula) return; }
  await patch([{ op: 'windows_fill', fill: mode, ...(formula ? { fill_formula: formula } : {}) }], 'окна: ' + mode);
};
$('#selShapes').onchange = async (e) => {
  const shape = e.target.value; e.target.value = '';
  if (shape) await patch([{ op: 'shapes', shape }], 'формы зданий: ' + shape);
};

// ---------------------------------------------------------------- doors (separate objects on hinges)
const doorAnims = new Map();  // hinge node -> {from, to, t0}
function toggleDoor(node) {
  const open = !node.userData.open;
  node.userData.open = open;
  doorAnims.set(node, { from: node.rotation.y, to: open ? THREE.MathUtils.degToRad(node.userData.openDeg) : 0, t0: performance.now() });
  invalidate();
}
function tickDoors() {
  for (const [n, a] of doorAnims) {
    const k = Math.min(1, (performance.now() - a.t0) / 700), e = k * k * (3 - 2 * k);
    n.rotation.y = a.from + (a.to - a.from) * e;
    if (k >= 1) doorAnims.delete(n);
    invalidate();
  }
}
$('#btnDoors').onclick = () => {
  const doors = []; root.traverse((o) => { if (o.userData.door && !doors.includes(o.userData.door)) doors.push(o.userData.door); });
  const open = !doors.some((d) => d.userData.open);
  doors.forEach((d) => { if (!!d.userData.open !== open) toggleDoor(d); });
};

// ---------------------------------------------------------------- building mode, destruction
function renderBuild() {
  const st = S.state || {};
  $$('#segBuild button').forEach((b) => b.classList.toggle('on', b.dataset.v === (st.build_mode || 'solid')));
  $('#selBrick').value = String(st.brick_size ?? 0.5);
  $('#chkCull').checked = st.brick_cull !== false;
  $('#chkDoors').checked = st.doors_separate !== false;
  const f = st.fracture || {};
  $('#chkFrac').checked = !!f.on;
  $('#selFracLevel').value = f.level || 'medium';
  $('#selFracMode').value = f.mode || 'voronoi';
  $('#selFracLevel option[value="bricks"]').disabled = st.build_mode !== 'bricks';
}
$$('#segBuild button').forEach((b) => b.onclick = () => patch([{ op: 'set', key: 'build_mode', value: b.dataset.v }], 'сборщик: ' + b.textContent));
$('#selBrick').onchange = (e) => patch([{ op: 'set', key: 'brick_size', value: Number(e.target.value) }], 'кирпич ' + e.target.value + ' м');
$('#chkCull').onchange = (e) => patch([{ op: 'set', key: 'brick_cull', value: e.target.checked }], e.target.checked ? 'невидимые грани удаляются' : 'кирпичи — полные кубы');
$('#chkDoors').onchange = (e) => patch([{ op: 'set', key: 'doors_separate', value: e.target.checked }], e.target.checked ? 'двери отдельно' : 'двери вварены');
function fracSet(upd, note) {
  const f = { on: $('#chkFrac').checked, level: $('#selFracLevel').value, mode: $('#selFracMode').value, seed: (S.state?.fracture?.seed || 1), ...upd };
  return patch([{ op: 'set', key: 'fracture', value: f }], note);
}
$('#chkFrac').onchange = (e) => { fracReset(); fracSet({ on: e.target.checked }, e.target.checked ? 'разрушаемость включена' : 'разрушаемость выключена'); };
$('#selFracLevel').onchange = (e) => { fracReset(); fracSet({ level: e.target.value }, 'разрушаемость: ' + e.target.selectedOptions[0].textContent); };
$('#selFracMode').onchange = (e) => { fracReset(); fracSet({ mode: e.target.value }, 'разрушаемость: ' + e.target.selectedOptions[0].textContent); };

const frac = { group: null, chunks: [], center: new THREE.Vector3(), boom: null };
async function fracLoad() {
  if (frac.group) return true;
  if (!$('#chkFrac').checked) { alert('Сначала включите «Разрушаемое здание».'); return false; }
  $('#busy').hidden = false;
  try {
    const gltf = await loader.parseAsync(await api('fracture.glb'), '');
    frac.group = gltf.scene;
    const realistic = (S.state?.detail || 'realistic') === 'realistic';
    frac.group.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = o.receiveShadow = true;
      if (!o.geometry.attributes.normal) o.geometry.computeVertexNormals();  // without normals the pieces render black
      o.material.flatShading = !realistic;
      if (realistic) applyTextures(o.material);
      o.material.needsUpdate = true;
    });
    frac.chunks = frac.group.children.filter((c) => c.name.startsWith('chunk'));
    frac.chunks.forEach((c) => { c.userData.base = c.position.clone(); c.userData.rot = c.quaternion.clone(); });
    frac.center = new THREE.Box3().setFromObject(frac.group).getCenter(new THREE.Vector3());
    scene.add(frac.group);
    root.visible = false;
    $('#status').textContent = `💥 ${frac.chunks.length} кусков`;
    return true;
  } catch (e) { feedLine({ type: 'error', agent: 'ui', note: e.message }); return false; }
  finally { $('#busy').hidden = true; invalidate(true); }
}
function fracReset() {
  if (frac.group) { scene.remove(frac.group); frac.group.traverse((o) => { if (o.isMesh) { o.geometry.dispose(); o.material.dispose(); } }); }
  frac.group = null; frac.chunks = []; frac.boom = null; root.visible = true; $('#rngExplode').value = 0; invalidate(true);
}
function fracExplode(k) {
  frac.chunks.forEach((c) => {
    const d = c.userData.base.clone().sub(frac.center);
    c.position.copy(c.userData.base).add(d.multiplyScalar(k * 0.6));
    c.quaternion.copy(c.userData.rot);
  });
  invalidate(true);
}
$('#btnFracShow').onclick = async () => { if (await fracLoad()) fracExplode(Number($('#rngExplode').value) / 100); };
$('#rngExplode').oninput = async (e) => { if (await fracLoad()) { frac.boom = null; fracExplode(Number(e.target.value) / 100); } };
$('#btnFracReset').onclick = fracReset;
$('#btnFracBoom').onclick = async () => {  // a quick physics demo: impulse from the centre, gravity, ground bounce
  if (!(await fracLoad())) return;
  fracExplode(0);
  frac.chunks.forEach((c) => {
    const d = c.userData.base.clone().sub(frac.center); d.y = Math.max(d.y, 0.5);
    const r = new THREE.Box3().setFromObject(c).getSize(new THREE.Vector3()).length() / 4;
    c.userData.v = d.normalize().multiplyScalar(4 + Math.random() * 7).add(new THREE.Vector3(0, 3 + Math.random() * 6, 0));
    c.userData.w = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).multiplyScalar(6);
    c.userData.r = Math.max(0.1, r);
  });
  frac.boom = { t: performance.now(), last: performance.now() };
};
function tickBoom() {
  const b = frac.boom;
  if (!b) return;
  const now = performance.now(), dt = Math.min(0.04, (now - b.last) / 1000);
  b.last = now;
  frac.chunks.forEach((c) => {
    const v = c.userData.v, w = c.userData.w;
    v.y -= 9.81 * dt;
    c.position.addScaledVector(v, dt);
    if (c.position.y < c.userData.r) { c.position.y = c.userData.r; v.y = -v.y * 0.3; v.x *= 0.7; v.z *= 0.7; w.multiplyScalar(0.7); }
    c.rotateOnAxis(w.clone().normalize(), w.length() * dt);
  });
  if (now - b.t > 6000) frac.boom = null;
  invalidate(true);
}

// ---------------------------------------------------------------- marks for the AI: points and drawings on the model
// The AI then changes only the marked elements (the server locks everything else for the run).
S.marks = []; S.marking = false;
const markCv = document.createElement('canvas');
markCv.id = 'markCanvas';
if (getComputedStyle(vp).position === 'static') vp.style.position = 'relative';
vp.appendChild(markCv);
const toCore = (v) => [+(v.x).toFixed(2), +(-v.z).toFixed(2), +(v.y).toFixed(2)];  // Y-up -> Z-up
function markHit(e) {
  const r = renderer.domElement.getBoundingClientRect();
  mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const cut = renderer.clippingPlanes.length ? clipPlane : null;
  const hits = ray.intersectObjects(root.children, true)
    .filter((h) => h.object.visible && !h.object.userData.overlay && (!cut || cut.distanceToPoint(h.point) >= 0));
  return hits.find((h) => h.object.userData.eid) || hits[0] || null;
}
let drawing = null;
renderer.domElement.addEventListener('pointerdown', (e) => {
  if (!S.marking || e.button !== 0) return;
  drawing = { x: e.clientX, y: e.clientY, last: [e.clientX, e.clientY], pts: [], eids: new Set() };
  markAdd(drawing, e);
});
renderer.domElement.addEventListener('pointermove', (e) => {
  if (!drawing || !(e.buttons & 1)) return;
  if (Math.hypot(e.clientX - drawing.last[0], e.clientY - drawing.last[1]) < 6) return;
  drawing.last = [e.clientX, e.clientY];
  markAdd(drawing, e);
  invalidate();
});
window.addEventListener('pointerup', (e) => {
  if (!drawing) return;
  const d = drawing; drawing = null;
  const moved = Math.hypot(e.clientX - d.x, e.clientY - d.y) > 6;
  if (!d.pts.length || (moved && d.pts.length < 2)) return invalidate();
  S.marks.push({ kind: moved ? 'stroke' : 'point', pts: moved ? d.pts : d.pts.slice(0, 1), eids: [...d.eids], note: '' });
  renderMarks(); invalidate();
  setTimeout(() => $(`#markList input[data-i="${S.marks.length - 1}"]`)?.focus(), 0);
});
function markAdd(d, e) {
  const h = markHit(e);
  if (!h) return;
  d.pts.push(h.point.clone());
  if (h.object.userData.eid) d.eids.add(h.object.userData.eid);
}
function drawMarks() {
  const w = vp.clientWidth, h = vp.clientHeight, k = renderer.getPixelRatio();
  if (markCv.width !== Math.round(w * k) || markCv.height !== Math.round(h * k)) { markCv.width = Math.round(w * k); markCv.height = Math.round(h * k); }
  const c = markCv.getContext('2d');
  c.setTransform(k, 0, 0, k, 0, 0);
  c.clearRect(0, 0, w, h);
  const scr = (v) => { const p = v.clone().project(camera); return p.z > 1 ? null : [(p.x + 1) / 2 * w, (1 - p.y) / 2 * h]; };
  const all = drawing ? [...S.marks, { kind: 'stroke', pts: drawing.pts, live: true }] : S.marks;
  all.forEach((m, i) => {
    const P = m.pts.map(scr).filter(Boolean);
    if (!P.length) return;
    c.strokeStyle = '#ff3b30'; c.fillStyle = '#ff3b30'; c.lineWidth = 3; c.lineJoin = c.lineCap = 'round';
    if (m.kind === 'stroke') { c.beginPath(); P.forEach(([x, y], j) => (j ? c.lineTo(x, y) : c.moveTo(x, y))); c.stroke(); }
    if (m.live) return;
    const [x, y] = P[0];
    c.beginPath(); c.arc(x, y, 10, 0, Math.PI * 2); c.fill();
    c.fillStyle = '#fff'; c.font = 'bold 12px sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle';
    c.fillText(String(i + 1), x, y + 0.5);
  });
}
function typeOf(id) { return S.tree.find((t) => t.id === id)?.type || ''; }
function renderMarks() {
  $('#markBar').hidden = !S.marks.length;
  $('#markList').innerHTML = S.marks.map((m, i) => {
    const what = m.eids.length ? m.eids.map((id) => `${esc(id)} <i>${esc(typeOf(id))}</i>`).join(', ') : 'без элемента (точка в пространстве)';
    return `<div class="mk"><b>${i + 1}</b><span class="what" title="${m.kind === 'stroke' ? 'рисунок' : 'точка'}">${m.kind === 'stroke' ? '〰' : '•'} ${what}</span>
      <input data-i="${i}" value="${esc(m.note)}" placeholder="что здесь сделать"><button data-del="${i}" title="Удалить пометку">✕</button></div>`;
  }).join('');
  if (S.marks.length) showTab('right', 'chat');
}
function setMarking(on) {
  S.marking = on;
  $('#btnMark').classList.toggle('on', on);
  renderer.domElement.style.cursor = on ? 'crosshair' : '';
  orbit.mouseButtons = on ? { LEFT: null, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE }
    : { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
  if (on) { gizmo.detach(); $('#status').textContent = 'Пометки: клик — точка, протянуть — нарисовать; камера — правая кнопка мыши'; }
}
$('#btnMark').onclick = () => setMarking(!S.marking);
$('#markList').oninput = (e) => { if (e.target.dataset.i) S.marks[+e.target.dataset.i].note = e.target.value; };
$('#markList').onclick = (e) => { if (e.target.dataset.del) { S.marks.splice(+e.target.dataset.del, 1); renderMarks(); invalidate(); } };
$('#markClear').onclick = () => { S.marks = []; renderMarks(); invalidate(); };
function markShot() {  // the view with the marks drawn on top, as the AI should see it
  renderer.render(scene, camera); drawMarks();
  const src = renderer.domElement, s = Math.min(1, 1280 / src.width);
  const cv = document.createElement('canvas');
  cv.width = Math.round(src.width * s); cv.height = Math.round(src.height * s);
  const c = cv.getContext('2d');
  c.drawImage(src, 0, 0, cv.width, cv.height); c.drawImage(markCv, 0, 0, cv.width, cv.height);
  return cv.toDataURL('image/png');
}
$('#markRun').onclick = async () => {
  if (!S.marks.length) return;
  const task = $('#chatText').value.trim();
  const scope = [...new Set(S.marks.flatMap((m) => m.eids))];
  const lines = S.marks.map((m, i) => {
    const where = m.kind === 'stroke'
      ? `рисунок по ${m.eids.length ? 'элементам ' + m.eids.map((id) => `\`${id}\` (${typeOf(id)})`).join(', ') : 'пустому месту'}, от ${JSON.stringify(toCore(m.pts[0]))} до ${JSON.stringify(toCore(m.pts.at(-1)))}`
      : m.face ? `грань \`${m.face}\` (точка ${JSON.stringify(toCore(m.pts[0]))}; на ней: ${m.eids.slice(1).map((id) => '`' + id + '`').join(', ') || 'ничего'})`
      : `точка на ${m.eids.length ? `элементе \`${m.eids[0]}\` (${typeOf(m.eids[0])})` : 'пустом месте'} в ${JSON.stringify(toCore(m.pts[0]))}`;
    return `${i + 1}. ${where}: «${m.note || task || 'переделать'}»`;
  });
  const text = ['Переделай ТОЛЬКО отмеченные места модели. Всё остальное не трогай.',
    scope.length ? `Менять можно только элементы ${scope.map((s) => '`' + s + '`').join(', ')} и их дочерние элементы, новые элементы — только прикреплённые к ним; остальные правки сервер отклонит.`
      : 'Пометки не попали на элементы — ориентируйся по координатам.',
    task ? `Общая задача: ${task}` : '',
    'Пометки (координаты в метрах, Z вверх; на скриншоте — красные номера и линии):', ...lines,
    'После правок проверь validate и render_views (только что отмеченное).'].filter(Boolean).join('\n');
  try {
    chatBusy(true); showTab('right', 'chat');
    await api('chat', { text, scope, image: markShot() });
    $('#chatText').value = '';
    setMarking(false);
  } catch (e) { chatBusy(false); chatItem({ role: 'error', text: e.message }); }
};

// ---------------------------------------------------------------- AI chat (any provider; runs on the server)
const CH = { settings: null };
function chatItem(it) {
  const log = $('#chatLog');
  log.querySelector('.hint')?.remove();
  const d = document.createElement('div');
  d.className = 'msg ' + it.role;
  if (it.role === 'tool') d.textContent = '🔧 ' + it.text + (it.args && Object.keys(it.args).length ? ' ' + JSON.stringify(it.args).slice(0, 160) : '');
  else d.textContent = it.text;
  log.appendChild(d);
  log.scrollTop = log.scrollHeight;
}
function chatBusy(b) { $('#chatSend').hidden = b; $('#chatStop').hidden = !b; }
function chatEvent(ev) {
  if (ev.role === 'done') { renderUsage(); return chatBusy(false); }
  chatItem(ev);
}
function chatFill() {
  const s = CH.settings, p = s.providers.find((x) => x.id === s.provider) || s.providers[0];
  $('#chatProvider').innerHTML = s.providers.map((x) => `<option value="${x.id}" ${x.id === s.provider ? 'selected' : ''}>${esc(x.title)}${x.id in s.cli && !s.cli[x.id] ? ' (не установлен)' : ''}</option>`).join('');
  $('#chatModel').value = s.models[p.id] || '';
  const acct = p.id in s.cli;  // signs in with an account, no API key
  $('#chatModel').placeholder = p.model || (acct ? 'модель (по умолчанию)' : 'модель (имя у провайдера)');
  const compat = p.id !== 'anthropic' && !acct;
  $('#chatUrl').hidden = !compat; $('#chatUrl').value = s.base_urls[p.id] || p.base_url;
  $('#chatKey').hidden = acct;
  $('#chatAcct').hidden = !acct;
  if (acct) chatAccount(p.id);
  $('#chatKey').value = '';
  $('#chatKey').placeholder = s.has_key[p.id] ? 'ключ сохранён (ввести новый)' : (p.needs_key ? 'API-ключ' : 'API-ключ (не обязателен)');
  $('#chatEffort').hidden = p.id !== 'anthropic'; $('#chatEffort').value = s.effort || 'high';
  $('#chatVision').parentElement.hidden = !compat; $('#chatVision').checked = s.vision !== false;
}
async function chatAccount(id) {
  $('#chatAcctSt').textContent = 'проверяю вход…';
  const a = await api('chat/account?provider=' + id).catch(() => ({}));
  if (CH.settings.provider !== id) return;
  $('#chatInstall').hidden = !!a.installed;
  $('#chatLogin').hidden = !a.installed;
  $('#chatAcctSt').textContent = !a.installed ? 'не установлен' : a.logged_in === true ? '✓ вход выполнен' : a.logged_in === false ? 'не выполнен вход' : '';
  $('#chatAcctSt').title = a.status || '';
}
async function chatConsole(what) {
  try {
    await api('chat/console', { provider: CH.settings.provider, what });
    chatItem({ role: 'info', text: what === 'install' ? 'Идёт установка в отдельном окне. Когда закончится, нажмите «Войти».'
      : 'Открылось окно входа: войдите в аккаунт в браузере, затем закройте окно и пишите в чат.' });
  } catch (e) { chatItem({ role: 'error', text: e.message }); }
}
$('#chatLogin').onclick = () => chatConsole('login');
$('#chatInstall').onclick = () => chatConsole('install');
window.addEventListener('focus', () => { const id = CH.settings?.provider; if (id && id in CH.settings.cli) chatAccount(id); });
async function chatSave(upd) { CH.settings = await api('chat/settings', upd); chatFill(); }
async function chatInit() {
  const st = await api('chat');
  CH.settings = st.settings; chatFill();
  st.transcript.forEach(chatItem);
  chatBusy(st.busy);
}
$('#chatProvider').onchange = () => chatSave({ provider: $('#chatProvider').value });
$('#chatModel').onchange = () => chatSave({ model: $('#chatModel').value });
$('#chatUrl').onchange = () => chatSave({ base_url: $('#chatUrl').value });
$('#chatKey').onchange = () => chatSave({ api_key: $('#chatKey').value });
$('#chatEffort').onchange = () => chatSave({ effort: $('#chatEffort').value });
$('#chatVision').onchange = () => chatSave({ vision: $('#chatVision').checked });
$('#chatReset').onclick = async () => {
  try { await api('chat/reset', {}); $('#chatLog').innerHTML = '<div class="hint">Новый разговор.</div>'; }
  catch (e) { chatItem({ role: 'error', text: e.message }); }
};
$('#chatStop').onclick = () => api('chat/stop', {});
async function chatSend() {
  const text = $('#chatText').value.trim();
  if (!text) return;
  try { chatBusy(true); await api('chat', { text }); $('#chatText').value = ''; }
  catch (e) { chatBusy(false); chatItem({ role: 'error', text: e.message }); }
}
$('#chatSend').onclick = chatSend;
$('#chatText').addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); chatSend(); } });
chatInit().catch((e) => chatItem({ role: 'error', text: 'чат: ' + e.message }));

// ---------------------------------------------------------------- about / author / license
async function showAbout() {
  try {
    const a = await api('about');
    $('#aboutVer').textContent = 'v' + a.version;
    $('#aboutLic').textContent = a.license_text;
  } catch { /* the card still shows the author and terms */ }
  $('#about').hidden = false;
}
$('#brand').onclick = showAbout;
$('#aboutClose').onclick = () => { $('#about').hidden = true; };
$('#about').onclick = (e) => { if (e.target.id === 'about') $('#about').hidden = true; };

// ---------------------------------------------------------------- language, theme, names
function nm(s) { return LANG === 'ru' ? (s.name_ru || s.name || s.id) : (s.name || s.name_ru || s.id); }
function ttl(c) { return LANG === 'ru' ? (c.title_ru || c.type) : c.type.replace(/_/g, ' '); }
function styleOptions() {  // sub-styles (variants) grouped under their parent style
  const kids = {};
  S.styles.filter((s) => s.parent).forEach((s) => (kids[s.parent] = kids[s.parent] || []).push(s));
  return S.styles.filter((s) => !s.parent).map((s) => kids[s.id]
    ? `<optgroup label="${esc(nm(s))}"><option value="${s.id}">${esc(nm(s))}</option>${kids[s.id].map((k) => `<option value="${k.id}">↳ ${esc(nm(k))}</option>`).join('')}</optgroup>`
    : `<option value="${s.id}">${esc(nm(s))}</option>`).join('');
}
function applyTheme(t) {
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem('pazl.theme', t); } catch { /* not saved */ }
  scene.background.set(cssVar('--sky', '#9fb4c8')); scene.fog.color.copy(scene.background);
  ground.material.color.set(cssVar('--ground', '#77806f'));
  invalidate();
}
$('#setLang').innerHTML = Object.entries(LANGS).map(([k, v]) => `<option value="${k}" ${k === LANG ? 'selected' : ''}>${v}</option>`).join('');
$('#setLang').onchange = (e) => setLang(e.target.value);
$('#setTheme').value = document.documentElement.dataset.theme || 'graphite';
$('#setTheme').onchange = (e) => applyTheme(e.target.value);
$('#btnSettings').onclick = () => { $('#settings').hidden = false; };
$('#settingsClose').onclick = () => { $('#settings').hidden = true; };
$('#settings').onclick = (e) => { if (e.target.id === 'settings') $('#settings').hidden = true; };

// ---------------------------------------------------------------- autosaves
$('#selAutosave').onfocus = $('#selAutosave').onmousedown = async () => {
  const list = await api('autosaves').catch(() => []);
  $('#selAutosave').innerHTML = '<option value="">🕘 Автосохранения…</option>' + (list.length
    ? list.map((a) => `<option value="${esc(a.file)}">${esc(a.time)} · v${a.version} · ${a.elements} эл.</option>`).join('')
    : '<option value="" disabled>нет автосохранений</option>');
};
$('#selAutosave').onchange = async (e) => {
  const f = e.target.value; e.target.value = '';
  if (f && confirm('Вернуть проект к этому автосохранению?')) await api('autosaves/restore', { file: f }).then(() => refreshAll(true));
};

// ---------------------------------------------------------------- menus, decorations, report, usage, error log
document.addEventListener('click', (e) => {  // one menu open at a time; a click outside closes it
  $$('details.menu[open]').forEach((d) => { if (!d.contains(e.target)) d.open = false; });
});
$$('details.menu').forEach((d) => d.addEventListener('toggle', () => { if (d.open) $$('details.menu[open]').forEach((o) => { if (o !== d) o.open = false; }); }));
$('#chkProps').onchange = (e) => patch([{ op: 'set', key: 'props', value: e.target.checked }], e.target.checked ? 'украшения показаны' : 'украшения скрыты');
$('#btnPropsAuto').onclick = () => patch([{ op: 'props_clear' }, { op: 'props_auto', density: Number($('#rngPropsDens').value) / 100 }], 'украшения расставлены');
$('#btnPropsClear').onclick = () => patch([{ op: 'props_clear' }], 'украшения убраны');
$('#btnFixFloat').onclick = () => patch([{ op: 'fix_floating' }], 'висящие части опущены');
$('#btnReport').onclick = async () => {
  try {
    const r = await api('report/save', {});
    feedLine({ type: 'exported', agent: 'ui', note: 'Отчёт: ' + r.path });
    showTab('right', 'feed');
  } catch (e) { feedLine({ type: 'error', agent: 'ui', note: e.message }); }
};
async function renderUsage() {
  const u = await api('usage').catch(() => null);
  const t = u?.total;
  if (!t) return;
  $('#usageBar').innerHTML = t.runs
    ? `Потрачено на проект: <b>${(t.input + t.output).toLocaleString('ru')}</b> токенов (вход ${t.input.toLocaleString('ru')}, выход ${t.output.toLocaleString('ru')})`
      + ` · <b>$${t.cost_usd.toFixed(4)}</b>${t.subscription_runs ? ` + ${t.subscription_runs} запуск(ов) по подписке` : ''} · запусков ИИ: ${t.runs}`
    : 'ИИ ещё не работал над этим проектом.';
}
window.addEventListener('error', (e) => { api('log', { where: 'window', error: e.message, src: e.filename + ':' + e.lineno }).catch(() => {}); });
window.addEventListener('unhandledrejection', (e) => { api('log', { where: 'promise', error: String(e.reason?.message || e.reason) }).catch(() => {}); });

function showTab(where, tab) {
  $$(`.tabs[data-for="${where}"] button`).forEach((b) => b.classList.toggle('on', b.dataset.tab === tab));
  const parent = where === 'left' ? $('#left') : $('#right');
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
    if (ev.type === 'chat') { chatEvent(ev); return; }
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
initI18n();
