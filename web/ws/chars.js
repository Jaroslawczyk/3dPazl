// Workshop "chars": organic bodies, imported bodies, clay, skin, animation (backend: pazl/core/chars).
import { esc, post, getJson, viewer } from './charview.js';

const LABELS = { height: 'Рост, м', length: 'Длина, м', build: 'Комплекция', muscle: 'Мышцы', head: 'Голова', shoulders: 'Плечи', chest: 'Грудь', waist: 'Талия',
  hips: 'Бёдра', belly: 'Живот', bust: 'Бюст', legs: 'Ноги', arms: 'Руки', nose: 'Нос', ears: 'Уши', ear_tip: 'Острые уши', snout: 'Морда', tail: 'Хвост' };
const COLORS = { color: 'Тело', belly_color: 'Живот', eyes: 'Глаза' };
const range = (k) => (k === 'height' || k === 'length' ? [.2, 2.5, .01] : ['belly', 'bust', 'muscle', 'ear_tip'].includes(k) ? [0, 2, .05] : k === 'nose' || k === 'ears' ? [.4, 3, .05] : [.5, 2, .01]);

export async function mount(el, ctx) {
  const cat = await getJson('/api/ws/chars/catalog');
  const glbs = await getJson('/api/glbs').catch(() => []);
  const bl = document.querySelector('#wsBlender'); if (bl) bl.textContent = '✓ Встроенные инструменты: Blender не нужен';
  const row = 'style="display:flex;gap:4px;align-items:center;margin:3px 0"';
  const skinOpts = `<option value="">без скина (цвет тела)</option>${Object.entries(cat.skins.presets).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('')}${cat.skins.saved.map((k) => `<option>${esc(k)}</option>`).join('')}`;
  el.innerHTML = `<h4>1. Новый персонаж</h4>
    <div ${row}><input id="chName" placeholder="имя" style="flex:1"><select id="chPreset">${Object.entries(cat.presets).map(([k, v]) => `<option value="${k}">${esc(v.title)}</option>`).join('')}</select></div>
    <button id="chNew" style="width:100%">Создать тело</button>
    <div ${row}><select id="chSrc" style="flex:1"><option value="">— или своя модель (GLB) —</option>${glbs.filter((g) => !g.path.startsWith('chars/')).map((g) => `<option>${esc(g.path)}</option>`).join('')}</select>
      <select id="chTpl"><option value="humanoid">человек</option><option value="quadruped">зверь</option><option value="simple">объект</option></select></div>
    <button id="chImp" style="width:100%">Сделать персонажем</button>
    <h4>2. Персонаж</h4>
    <select id="chOpen" style="width:100%"></select>
    <div id="chSliders"></div>
    <h4>3. Лепка</h4>
    <div ${row}><label class="hint"><input id="chClay" type="checkbox"> лепить кликом по телу</label></div>
    <div ${row} class="hint">кисть <input id="chR" type="range" min="0.02" max="0.3" step="0.01" value="0.08" style="flex:1"> сила <input id="chA" type="range" min="-0.04" max="0.04" step="0.002" value="0.012" style="flex:1"></div>
    <div ${row}><label class="hint"><input id="chMir" type="checkbox" checked> зеркально</label><button id="chUndo" style="margin-left:auto">↶ Отменить мазок</button></div>
    <h4>4. Скин</h4>
    <select id="chSkin" style="width:100%">${skinOpts}</select>
    <h4>5. Анимация</h4>
    <div ${row}><select id="chClip" style="flex:1"></select><button id="chAdd" title="Добавить ещё движение">+</button><select id="chPre"><option value="run">бег</option><option value="wave">привет</option><option value="jump">прыжок</option><option value="idle">стойка</option><option value="walk">шаг</option></select></div>
    <div class="hint">Кости и ключи правятся в «Риг и анимация» (риг char_имя).</div>
    <pre id="chOut" class="hint" style="white-space:pre-wrap;font-size:11px;margin:4px 0"></pre>`;
  const $ = (s) => el.querySelector(s);
  const out = (t) => { $('#chOut').textContent = t; };
  const V = viewer(ctx, 'chars');
  let C = null;
  const busy = async (msg, fn) => { out('⏳ ' + msg); try { const r = await fn(); return r; } catch (e) { out('⚠ ' + e.message); } };
  const summary = (r) => `✓ ${r.name}: ${r.tris.toLocaleString('ru')} треуг., ${r.kb} КБ, анимации: ${r.clips.join(', ')}`;

  const fillOpen = (names, cur) => { $('#chOpen').innerHTML = '<option value="">— открыть —</option>' + names.map((n) => `<option>${esc(n)}</option>`).join(''); $('#chOpen').value = cur || ''; };
  const sliders = () => {
    const box = $('#chSliders'); const p = C.params || {};
    if (C.import) { box.innerHTML = `<div class="hint">Тело из ${esc(C.import)}: меняйте лепкой.</div>`; return; }
    box.innerHTML = Object.keys(p).map((k) => (COLORS[k]
      ? `<div ${row} class="hint"><span style="flex:1">${COLORS[k]}</span><input type="color" data-k="${k}" value="${esc(p[k])}"></div>`
      : `<div ${row} class="hint"><span style="width:76px">${LABELS[k] || k}</span><input type="range" data-k="${k}" min="${range(k)[0]}" max="${range(k)[1]}" step="${range(k)[2]}" value="${p[k]}" style="flex:1"><span style="width:30px">${(+p[k]).toFixed(2)}</span></div>`)).join('');
    box.querySelectorAll('input').forEach((i) => {
      i.oninput = () => { if (i.nextElementSibling) i.nextElementSibling.textContent = (+i.value).toFixed(2); };
      i.onchange = () => busy('меняю тело и подгоняю одежду…', async () => {
        const r = await post('/api/ws/chars/update', { name: C.name, params: { [i.dataset.k]: i.type === 'color' ? i.value : +i.value } });
        await open(C.name, r);
      });
    });
  };
  const open = async (name, res) => {
    C = await getJson('/api/ws/chars/get/' + encodeURIComponent(name));
    sliders();
    const clips = Object.keys(C.clips);
    $('#chClip').innerHTML = '<option value="">поза (без движения)</option>' + clips.map((c) => `<option>${esc(c)}</option>`).join('');
    $('#chClip').value = V.clip && clips.includes(V.clip) ? V.clip : '';
    V.clip = $('#chClip').value;
    const r = res || await post('/api/ws/chars/anim', { name, preset: clips[0] || 'idle' });
    await ctx.refresh(); await V.show(r.path); out(summary(r));
    try { localStorage.setItem('pazl.char', name); } catch (e) { /* storage blocked */ }
    return r;
  };
  const create = async (body) => {
    const r = await post('/api/ws/chars/create', body);
    const c = await getJson('/api/ws/chars/catalog');
    fillOpen(c.chars, r.name); await open(r.name, r);
  };
  fillOpen(cat.chars);
  $('#chNew').onclick = () => busy('вылепливаю тело, ставлю скелет…', () => create({ name: $('#chName').value || $('#chPreset').value, preset: $('#chPreset').value }));
  $('#chImp').onclick = () => busy('ставлю скелет на модель…', () => {
    const src = $('#chSrc').value; if (!src) throw new Error('выберите GLB');
    return create({ name: $('#chName').value || src.split('/').pop().replace('.glb', ''), src, template: $('#chTpl').value });
  });
  $('#chOpen').onchange = (e) => e.target.value && busy('открываю…', () => open(e.target.value));
  $('#chSkin').onchange = (e) => busy('надеваю скин…', async () => { if (!C) throw new Error('сначала персонаж'); await open(C.name, await post('/api/ws/chars/skin', { name: C.name, skin: e.target.value || null })); });
  $('#chClip').onchange = (e) => V.play(e.target.value);
  $('#chAdd').onclick = () => busy('создаю движение…', async () => { const p = $('#chPre').value; V.clip = p; await open(C.name, await post('/api/ws/chars/anim', { name: C.name, preset: p })); V.play(p); });
  $('#chUndo').onclick = () => busy('отменяю…', async () => { await open(C.name, await post('/api/ws/chars/sculpt', { name: C.name, undo: true })); });

  // clay: a click (not an orbit drag) on the body in the rest pose
  const cv = ctx.pazl.renderer.domElement;
  $('#chClay').onchange = (e) => { if (e.target.checked) { $('#chClip').value = ''; V.play(''); } };
  let down = null;
  const pd = (e) => { down = [e.clientX, e.clientY]; };
  const pu = (e) => {
    if (!el.isConnected) { cv.removeEventListener('pointerdown', pd); cv.removeEventListener('pointerup', pu); return; }
    if (!$('#chClay').checked || !C || !down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 4) return;
    const { THREE, camera, root } = ctx.pazl;
    const b = cv.getBoundingClientRect();
    const ray = new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2(((e.clientX - b.left) / b.width) * 2 - 1, -((e.clientY - b.top) / b.height) * 2 + 1), camera);
    const hit = ray.intersectObject(root, true)[0];
    if (!hit) return;
    busy('леплю…', async () => {
      const r = await post('/api/ws/chars/sculpt', { name: C.name, strokes: [{ p: hit.point.toArray(), r: +$('#chR').value, amount: +$('#chA').value, mirror: $('#chMir').checked }] });
      await open(C.name, r); out(summary(r) + ` · мазков: ${r.strokes}`);
    });
  };
  cv.addEventListener('pointerdown', pd); cv.addEventListener('pointerup', pu);

  let last = null; try { last = localStorage.getItem('pazl.char'); } catch (e) { /* storage blocked */ }
  if (last && cat.chars.includes(last)) { $('#chOpen').value = last; busy('открываю…', () => open(last)); }
}
