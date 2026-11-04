// Workshop "clothes": garments computed from the body, so they fit any character (backend: pazl/core/chars/cloth.py).
import { esc, post, getJson, viewer } from './charview.js';

export async function mount(el, ctx) {
  const cat = await getJson('/api/ws/chars/catalog');
  const bl = document.querySelector('#wsBlender'); if (bl) bl.textContent = '✓ Встроенные инструменты: Blender не нужен';
  const row = 'style="display:flex;gap:4px;align-items:center;margin:3px 0"';
  const models = document.querySelector('#wsModels'); if (models) models.previousElementSibling.hidden = models.hidden = true;
  if (!cat.chars.length) { el.innerHTML = '<div class="hint">Сначала создайте персонажа во вкладке «🧍 Персонажи».</div>'; return; }
  const chars = cat.chars.map((c) => `<option>${esc(c)}</option>`).join('');
  el.innerHTML = `<h4>На ком</h4><select id="clChar" style="width:100%">${chars}</select>
    <div ${row} class="hint"><label><input id="clMove" type="checkbox"> показать в движении</label></div>
    <h4>Надето</h4><div id="clWorn"></div>
    <h4>Новая вещь</h4>
    <select id="clKind" style="width:100%"></select>
    <div ${row} class="hint"><span style="width:76px">Цвет</span><input id="clColor" type="color" style="flex:1"></div>
    <div ${row} class="hint"><span style="width:76px">Скин</span><select id="clSkin" style="flex:1"><option value="">только цвет</option><option value="auto">как задумано</option>${Object.entries(cat.skins.presets).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('')}${cat.skins.saved.map((k) => `<option>${esc(k)}</option>`).join('')}</select></div>
    <div ${row} class="hint"><span style="width:76px">Свобода</span><input id="clEase" type="range" min="0.004" max="0.05" step="0.001" value="0.014" style="flex:1"></div>
    <div ${row} class="hint"><span style="width:76px">Складки</span><input id="clWr" type="range" min="0" max="3" step="0.1" value="1" style="flex:1"></div>
    <div ${row} class="hint" id="clLenRow"><span style="width:76px">Длина</span><input id="clLen" type="range" min="0.4" max="1.3" step="0.02" value="1" style="flex:1"></div>
    <div ${row} class="hint" id="clWrapRow" hidden>высота от <input id="clFrom" type="number" min="0" max="1" step="0.05" value="0.25" style="width:54px"> до <input id="clTo" type="number" min="0" max="1" step="0.05" value="0.75" style="width:54px"></div>
    <button id="clWear" style="width:100%">Надеть</button>
    <h4>Гардероб на другого</h4>
    <div ${row}><select id="clTo2" style="flex:1">${chars}</select><button id="clCopy" title="Те же вещи пересчитаются под другое тело">Одеть так же</button></div>
    <pre id="clOut" class="hint" style="white-space:pre-wrap;font-size:11px;margin:4px 0"></pre>`;
  const $ = (s) => el.querySelector(s);
  const out = (t) => { $('#clOut').textContent = t; };
  const V = viewer(ctx, 'clothes');
  let C = null;
  const busy = async (msg, fn) => { out('⏳ ' + msg); try { return await fn(); } catch (e) { out('⚠ ' + e.message); } };
  const kinds = () => {
    const g = {};
    C.wearable.forEach((k) => (g[k.group] ||= []).push(k));
    $('#clKind').innerHTML = Object.entries(g).map(([n, ks]) => `<optgroup label="${esc(n)}">${ks.map((k) => `<option value="${k.id}">${esc(k.title)}</option>`).join('')}</optgroup>`).join('');
    pick();
  };
  const pick = () => {
    const k = C.wearable.find((x) => x.id === $('#clKind').value);
    if (k) $('#clColor').value = k.color;
    $('#clWrapRow').hidden = k?.id !== 'wrap';
  };
  const worn = () => {
    $('#clWorn').innerHTML = C.outfit.length ? C.outfit.map((g) => `<div ${row}><span style="flex:1">${esc(C.wearable.find((k) => k.id === g.kind)?.title || g.kind)}</span><button data-rm="${esc(g.kind)}" title="Снять">✕</button></div>`).join('') : '<div class="hint">Пока ничего</div>';
    $('#clWorn').querySelectorAll('[data-rm]').forEach((b) => { b.onclick = () => busy('снимаю…', async () => show(await post('/api/ws/clothes/remove', { char: C.name, kind: b.dataset.rm }))); });
  };
  const show = async (r) => {
    C = await getJson('/api/ws/chars/get/' + encodeURIComponent(C.name));
    worn();
    await V.show(r.path);
    out(`✓ ${r.outfit.length} вещ., ${r.tris.toLocaleString('ru')} треуг.` + (r.skipped?.length ? ` · не подошло этому скелету: ${r.skipped.join(', ')}` : ''));
  };
  const load = async (name) => {
    C = await getJson('/api/ws/chars/get/' + encodeURIComponent(name));
    kinds(); worn();
    const r = await post('/api/ws/chars/anim', { name, preset: Object.keys(C.clips)[0] || 'idle' });
    await V.show(r.path); out('');
    try { localStorage.setItem('pazl.char', name); } catch (e) { /* storage blocked */ }
  };
  $('#clChar').onchange = (e) => busy('открываю…', () => load(e.target.value));
  $('#clKind').onchange = pick;
  $('#clMove').onchange = (e) => V.play(e.target.checked ? 'walk' : '');
  $('#clWear').onclick = () => busy('крою по телу…', async () => {
    const sk = $('#clSkin').value, id = $('#clKind').value;
    const body = { char: C.name, kind: id, ease: +$('#clEase').value, wrinkle: +$('#clWr').value, length: +$('#clLen').value, from: +$('#clFrom').value, to: +$('#clTo').value };
    if (sk !== 'auto') { body.color = $('#clColor').value; if (sk) body.skin = sk; }
    show(await post('/api/ws/clothes/wear', body));
  });
  $('#clCopy').onclick = () => busy('перекраиваю под другое тело…', async () => {
    const to = $('#clTo2').value, r = await post('/api/ws/clothes/copy', { from: C.name, to });
    $('#clChar').value = to; C = { name: to }; await load(to); await show(r);
  });
  let last = null; try { last = localStorage.getItem('pazl.char'); } catch (e) { /* storage blocked */ }
  if (last && cat.chars.includes(last)) $('#clChar').value = last;
  busy('открываю…', () => load($('#clChar').value));
}
