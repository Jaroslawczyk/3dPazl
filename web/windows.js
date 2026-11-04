// Window manager (Unity / Adobe style): side panels and the GLB picker can be dragged out into floating windows,
// resized, hidden, docked back, and everything can be reset to defaults. State lives in localStorage 'pazl.win'.
// API: window.pazlWin = { adopt(key, el, title), show, hide, toggle, isOpen, reset }
const $ = (s) => document.querySelector(s);
const KEY = 'pazl.win';
const TITLES = { left: 'Левая панель', right: 'Свойства · ИИ · журнал', glb: '🗂 GLB-модели' };
const DEF = () => ({ left: { float: false, hid: false }, right: { float: false, hid: false }, glb: { float: true, hid: true } });
let st = DEF();
let zTop = 40;
const adopted = {};   // key -> element (floating-only windows such as the GLB picker)

function load() {
  try { const j = JSON.parse(localStorage.getItem(KEY) || 'null'); if (j) { st = Object.assign(DEF(), j); return; } } catch (e) { /* ignore */ }
  try { const o = JSON.parse(localStorage.getItem('pazl.panels') || '{}'); st.left.hid = !!o.l; st.right.hid = !!o.r; } catch (e) { /* ignore */ }
}
function save() { try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) { /* storage blocked */ } }

const leftEl = () => ($('body').dataset.ws === 'build' ? $('#left') : $('#wsLeft'));
const elOf = (k) => (k === 'left' ? leftEl() : k === 'right' ? $('#right') : adopted[k]);
const side = (k) => (k === 'left' ? 'l' : 'r');

function defRect(k) {
  const W = innerWidth, H = innerHeight;
  if (k === 'glb') return { x: Math.max(20, W - 560), y: 60, w: 420, h: Math.min(560, H - 100) };
  if (k === 'left') return { x: 80, y: 70, w: 320, h: Math.min(620, H - 110) };
  return { x: Math.max(20, W - 420), y: 70, w: 380, h: Math.min(640, H - 110) };
}
function rectOf(k) {
  const s = st[k];
  const d = defRect(k);
  const r = { x: s.x ?? d.x, y: s.y ?? d.y, w: s.w ?? d.w, h: s.h ?? d.h };
  r.w = Math.min(r.w, innerWidth - 20); r.h = Math.min(r.h, innerHeight - 60);
  r.x = Math.min(Math.max(0, r.x), Math.max(0, innerWidth - 120)); r.y = Math.min(Math.max(48, r.y), Math.max(48, innerHeight - 60));
  return r;
}

function ensureBar(el, k) {
  if (!el || (el.firstElementChild && el.firstElementChild.classList.contains('win-bar'))) return;
  const bar = document.createElement('div');
  bar.className = 'win-bar'; bar.dataset.k = k;
  bar.innerHTML = `<span class="wt">${TITLES[k]}</span><span class="sp"></span>` +
    (k === 'glb' ? '' : '<button data-a="float" title="Оторвать в плавающее окно / закрепить обратно">⧉</button>') +
    '<button data-a="hide" title="Скрыть окно (вернуть: меню «🪟 Окна»)">✕</button>';
  el.prepend(bar);
  bar.onpointerdown = (e) => { if (e.target.closest('button')) return; startDrag(e, k); };
  bar.ondblclick = (e) => { if (!e.target.closest('button') && k !== 'glb') toggleFloat(k); };
  bar.querySelector('[data-a="float"]')?.addEventListener('click', () => toggleFloat(k));
  bar.querySelector('[data-a="hide"]').addEventListener('click', () => hide(k));
}
function ensureGrip(el, k) {
  if (!el || k === 'glb' || el.querySelector(':scope > .win-grip')) return;
  const g = document.createElement('div');
  g.className = 'win-grip ' + k; g.title = 'Потяните, чтобы изменить ширину панели';
  g.onpointerdown = (e) => {
    e.preventDefault(); g.setPointerCapture(e.pointerId);
    const left = $('main').getBoundingClientRect().left, right = $('main').getBoundingClientRect().right;
    g.onpointermove = (ev) => {
      if (k === 'left') st.wl = Math.round(Math.min(700, Math.max(140, ev.clientX - left - 64)));
      else st.wr = Math.round(Math.min(800, Math.max(200, right - ev.clientX)));
      applyVars();
    };
    g.onpointerup = () => { g.onpointermove = g.onpointerup = null; save(); window.dispatchEvent(new Event('resize')); };
  };
  el.appendChild(g);
}

function applyVars() {
  const b = document.body, m = $('main');
  b.classList.toggle('win-sz', st.wl != null || st.wr != null);
  if (st.wl != null) m.style.setProperty('--wl', st.wl + 'px'); else m.style.removeProperty('--wl');
  if (st.wr != null) m.style.setProperty('--wr', st.wr + 'px'); else m.style.removeProperty('--wr');
}

function placeRail(floating) {
  const rail = $('nav.rail'), l = $('#left');
  if (!rail || !l) return;
  if (floating && rail.parentElement !== l) { rail.classList.add('rail-in'); l.insertBefore(rail, l.children[1] || null); }
  else if (!floating && rail.parentElement === l) { rail.classList.remove('rail-in'); $('main').insertBefore(rail, l); }
}

function apply() {
  const b = document.body, bm = (k, c) => b.classList.toggle(c, !!k);
  for (const k of ['left', 'right']) {
    const s = st[k], el = elOf(k);
    const other = k === 'left' ? [$('#left'), $('#wsLeft')].find((x) => x !== el) : null;
    if (other) clearFloat(other);
    if (!el) continue;
    ensureBar(el, k); ensureGrip(el, k);
    const flt = s.float && !s.hid;
    bm(s.hid, 'hide-' + (k === 'left' ? 'left' : 'right'));
    bm(s.hid || s.float, 'win-off' + side(k));
    if (flt) setFloat(el, rectOf(k)); else clearFloat(el);
    if (k === 'left') placeRail(flt && b.dataset.ws === 'build');
    el.querySelector('.win-bar [data-a="float"]')?.classList.toggle('on', !!s.float);
  }
  const g = adopted.glb;
  if (g) { g.hidden = st.glb.hid; if (!st.glb.hid) setFloat(g, rectOf('glb')); }
  $('#btnHideL')?.classList.toggle('on', st.left.hid); $('#btnHideR')?.classList.toggle('on', st.right.hid);
  applyVars(); renderMenu();
  requestAnimationFrame(() => window.dispatchEvent(new Event('resize')));
}

function setFloat(el, r) {
  el.classList.add('win-float');
  Object.assign(el.style, { left: r.x + 'px', top: r.y + 'px', width: r.w + 'px', height: r.h + 'px', right: 'auto', bottom: 'auto' });
}
function clearFloat(el) {
  if (!el) return;
  el.classList.remove('win-float');
  ['left', 'top', 'width', 'height', 'right', 'bottom', 'zIndex'].forEach((p) => { el.style[p] = ''; });
}
function raise(el) { el.style.zIndex = ++zTop; }

function toggleFloat(k) { st[k].float = !st[k].float; st[k].hid = false; save(); apply(); }
function hide(k) { st[k].hid = true; save(); apply(); }
function show(k) { st[k].hid = false; save(); apply(); if (adopted[k]) raise(adopted[k]); }
function toggle(k) { st[k].hid ? show(k) : hide(k); }
const isOpen = (k) => !st[k].hid;
function reset() {
  st = DEF(); save(); try { localStorage.removeItem('pazl.panels'); } catch (e) { /* */ }
  document.body.classList.remove('hide-left', 'hide-right');
  apply();
}

// ---- dragging / tear-off / dock-by-edge
let dropEl = null;
function startDrag(e, k) {
  const el = elOf(k); if (!el) return;
  const s = st[k]; const r0 = el.getBoundingClientRect();
  const dx = e.clientX - r0.left, dy = e.clientY - r0.top, sx = e.clientX, sy = e.clientY;
  let floating = el.classList.contains('win-float');
  const bar = e.currentTarget; bar.setPointerCapture(e.pointerId);
  const edge = 56;
  bar.onpointermove = (ev) => {
    if (!floating) {   // tear a docked panel off once the pointer has moved a bit
      if (Math.hypot(ev.clientX - sx, ev.clientY - sy) < 24) return;
      Object.assign(s, { float: true, x: r0.left, y: r0.top, w: Math.max(260, r0.width), h: r0.height });
      apply(); floating = true;
    }
    s.x = Math.min(Math.max(-s.w + 120, ev.clientX - dx), innerWidth - 120); s.y = Math.min(Math.max(48, ev.clientY - dy), innerHeight - 40);
    el.style.left = s.x + 'px'; el.style.top = s.y + 'px'; raise(el);
    const home = k === 'left' ? ev.clientX < edge : k === 'right' ? ev.clientX > innerWidth - edge : false;
    if (home && !dropEl) { dropEl = document.createElement('div'); dropEl.id = 'winDrop'; document.body.appendChild(dropEl); }
    if (dropEl) { dropEl.style.cssText = `left:${k === 'left' ? 0 : 'auto'};right:${k === 'right' ? 0 : 'auto'}`; dropEl.hidden = !home; }
    s._dock = home;
  };
  bar.onpointerup = () => {
    bar.onpointermove = bar.onpointerup = null; dropEl?.remove(); dropEl = null;
    if (floating && s._dock) { s.float = false; }
    delete s._dock; save(); apply();
  };
}
document.addEventListener('pointerdown', (e) => { const w = e.target.closest('.win-float'); if (w) raise(w); }, true);

// ---- remember sizes of floating windows after a native resize
const ro = new ResizeObserver((es) => {
  for (const en of es) {
    const el = en.target, k = el.dataset.winKey; if (!k || !el.classList.contains('win-float')) continue;
    const w = Math.round(el.offsetWidth), h = Math.round(el.offsetHeight);
    if (st[k].w !== w || st[k].h !== h) { st[k].w = w; st[k].h = h; clearTimeout(ro.t); ro.t = setTimeout(save, 300); }
  }
});
function watch(el, k) { el.dataset.winKey = k; ro.observe(el); }

// ---- header menu
function renderMenu() {
  const box = $('#winMenu'); if (!box) return;
  const row = (k) => `<div class="win-row"><label><input type="checkbox" data-vis="${k}" ${st[k].hid ? '' : 'checked'}> ${TITLES[k]}</label>` +
    (k === 'glb' ? '' : `<button data-fl="${k}" title="${st[k].float ? 'Закрепить в окне программы' : 'Сделать плавающим окном'}">${st[k].float ? '📌 закрепить' : '⧉ оторвать'}</button>`) + '</div>';
  box.innerHTML = '<div class="hint">Окна можно таскать за заголовок, растягивать за край (док — за границу панели), скрывать и закреплять. Перетащите плавающую панель к её краю — она закрепится.</div>' +
    ['left', 'right', 'glb'].map(row).join('') + '<button id="winReset" class="act">↺ Вернуть окна по умолчанию</button>';
  box.querySelectorAll('[data-vis]').forEach((c) => { c.onchange = () => (c.checked ? show(c.dataset.vis) : hide(c.dataset.vis)); });
  box.querySelectorAll('[data-fl]').forEach((b) => { b.onclick = () => toggleFloat(b.dataset.fl); });
  $('#winReset').onclick = reset;
}

function adopt(k, el, title) {
  TITLES[k] = title || TITLES[k]; adopted[k] = el; el.classList.add('win-box');
  el.hidden = st[k].hid; ensureBar(el, k); watch(el, k); apply();
}

window.pazlWin = { adopt, show, hide, toggle, isOpen, reset };

function init() {
  load();
  $('#btnHideL').onclick = () => toggle('left'); $('#btnHideR').onclick = () => toggle('right');
  $('#settingsWinReset')?.addEventListener('click', reset);
  watch($('#left'), 'left'); watch($('#wsLeft'), 'left'); watch($('#right'), 'right');
  // #wsLeft is rebuilt with innerHTML by the workshops: put our bar back each time
  new MutationObserver(() => { const el = $('#wsLeft'); if (el && !el.querySelector(':scope > .win-bar')) { ensureBar(el, 'left'); ensureGrip(el, 'left'); } })
    .observe($('#wsLeft'), { childList: true });
  new MutationObserver(() => { apply(); window.dispatchEvent(new CustomEvent('pazl-ws', { detail: document.body.dataset.ws })); })
    .observe(document.body, { attributes: true, attributeFilter: ['data-ws'] });
  addEventListener('resize', () => { for (const k of ['left', 'right']) if (st[k].float && !st[k].hid) { const el = elOf(k); if (el) setFloat(el, rectOf(k)); } });
  apply();
}
// app.js runs first as a module and sets its own hide handlers; ours must win, so run after DOM is ready
if (document.readyState === 'loading') addEventListener('DOMContentLoaded', () => setTimeout(init, 0)); else setTimeout(init, 0);
