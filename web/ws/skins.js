// Workshop "skins": pattern/picture materials put on any static GLB (backend: pazl/core/skins.py).
import { esc, post, getJson } from './charview.js';

export async function mount(el, ctx) {
  const cat = await getJson('/api/ws/skins/catalog');
  const glbs = (await getJson('/api/glbs').catch(() => [])).filter((g) => !g.path.startsWith('rigs/') && !g.path.startsWith('chars/') && !g.path.startsWith('skins/'));
  const bl = document.querySelector('#wsBlender'); if (bl) bl.textContent = '✓ Встроенные инструменты: Blender не нужен';
  const row = 'style="display:flex;gap:4px;align-items:center;margin:3px 0"';
  const opt = (o) => Object.entries(o).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('');
  el.innerHTML = `<h4>1. Скин</h4>
    <select id="skPreset" style="width:100%"><option value="">— свой узор —</option>${opt(cat.presets)}${cat.saved.map((k) => `<option>${esc(k)}</option>`).join('')}</select>
    <div id="skCustom">
      <div ${row}><select id="skPat" style="flex:1">${opt(Object.fromEntries(Object.entries(cat.patterns).filter(([k]) => k !== 'image')))}</select>
        <input id="skC1" type="color" value="#7a8fa6"><input id="skC2" type="color" value="#26303c"><input id="skC3" type="color" value="#c9a227"></div>
      <div ${row} class="hint"><span style="width:76px">Размер, м</span><input id="skTile" type="range" min="0.03" max="1.5" step="0.01" value="0.3" style="flex:1"></div>
      <div ${row} class="hint"><span style="width:76px">Блеск</span><input id="skRough" type="range" min="0" max="1" step="0.05" value="0.3" style="flex:1"></div>
      <div ${row} class="hint"><span style="width:76px">Металл</span><input id="skMetal" type="range" min="0" max="1" step="0.05" value="0" style="flex:1"></div>
      <div ${row} class="hint"><span style="width:76px">Вариант</span><input id="skSeed" type="number" value="1" style="width:60px"><button id="skRnd">🎲</button></div>
      <div ${row}><input id="skFile" type="file" accept="image/*" style="flex:1;min-width:0" title="Своя картинка как скин"></div>
      <div ${row}><input id="skName" placeholder="имя скина" style="flex:1"><button id="skSave">Сохранить</button></div>
    </div>
    <h4>Из интернета (CC0)</h4>
    <div ${row}><input id="skQ" placeholder="кожа, denim, wood…" style="flex:1"><button id="skFind">Найти</button></div>
    <div id="skWeb" style="display:grid;grid-template-columns:repeat(4,1fr);gap:3px;max-height:190px;overflow:auto"></div>
    <img id="skTileImg" alt="образец" style="width:100%;max-height:120px;object-fit:cover;border-radius:6px;margin:4px 0">
    <h4>2. На что</h4>
    <select id="skSrc" style="width:100%"><option value="">— объект (GLB) —</option>${glbs.map((g) => `<option>${esc(g.path)}</option>`).join('')}</select>
    <div id="skParts" class="hint"></div>
    <button id="skApply" style="width:100%">Надеть скин</button>
    <div class="hint">Персонажам и одежде скин ставится в их вкладках.</div>
    <pre id="skOut" class="hint" style="white-space:pre-wrap;font-size:11px;margin:4px 0"></pre>`;
  const $ = (s) => el.querySelector(s);
  const out = (t) => { $('#skOut').textContent = t; };
  const busy = async (msg, fn) => { out('⏳ ' + msg); try { const r = await fn(); return r; } catch (e) { out('⚠ ' + e.message); } };
  let image = null;
  const skin = () => $('#skPreset').value || { pattern: $('#skPat').value, colors: ['#skC1', '#skC2', '#skC3'].map((i) => $(i).value), tile: +$('#skTile').value,
    rough: 1 - +$('#skRough').value, metal: +$('#skMetal').value, seed: +$('#skSeed').value };
  const preview = async () => {
    if (image) { $('#skTileImg').src = image; return; }
    $('#skTileImg').src = (await post('/api/ws/skins/preview', { skin: skin() })).url;
  };
  $('#skPreset').onchange = () => { $('#skCustom').hidden = !!$('#skPreset').value; image = null; preview().catch((e) => out('⚠ ' + e.message)); };
  el.querySelectorAll('#skCustom input:not([type=file]):not(#skName), #skCustom select').forEach((i) => { i.onchange = () => { image = null; preview().catch((e) => out('⚠ ' + e.message)); }; });
  $('#skFind').onclick = () => busy('ищу текстуры…', async () => {
    const r = await getJson('/api/ws/skins/web?q=' + encodeURIComponent($('#skQ').value));
    $('#skWeb').innerHTML = r.map((t) => `<img src="${esc(t.thumb)}" title="${esc(t.title)} (${esc(t.source)}, ${esc(t.license)})" data-s="${esc(t.source)}" data-i="${esc(t.id)}" style="width:100%;cursor:pointer;border-radius:4px">`).join('');
    out(r.length ? `Найдено ${r.length}. Нажмите на текстуру, чтобы скачать.` : 'Ничего не нашлось: попробуйте по-английски');
    $('#skWeb').querySelectorAll('img').forEach((i) => { i.onclick = () => busy('скачиваю…', async () => {
      const d = await post('/api/ws/skins/web', { source: i.dataset.s, id: i.dataset.i });
      $('#skPreset').insertAdjacentHTML('beforeend', `<option>${esc(d.name)}</option>`); $('#skPreset').value = d.name; $('#skCustom').hidden = true; image = null;
      await preview(); out(`✓ ${d.name} (${d.license}) ${d.source}`);
    }); });
  });
  $('#skRnd').onclick = () => { $('#skSeed').value = 1 + Math.floor(Math.random() * 9999); image = null; preview(); };
  $('#skFile').onchange = (e) => {
    const f = e.target.files[0]; if (!f) return;
    const r = new FileReader(); r.onload = () => { image = r.result; $('#skName').value ||= f.name.replace(/\.\w+$/, ''); preview(); out('Картинка выбрана: нажмите «Сохранить».'); }; r.readAsDataURL(f);
  };
  $('#skSave').onclick = () => busy('сохраняю…', async () => {
    const name = $('#skName').value; if (!name) throw new Error('нужно имя');
    const s = skin(), r = await post('/api/ws/skins/save', { name, skin: typeof s === 'string' ? {} : s, image });
    $('#skPreset').insertAdjacentHTML('beforeend', `<option>${esc(r.name)}</option>`); $('#skPreset').value = r.name; $('#skCustom').hidden = true; image = null;
    await preview(); out(`✓ скин ${r.name} сохранён, он есть и в персонажах, и в одежде`);
  });
  $('#skSrc').onchange = (e) => busy('читаю части…', async () => {
    out(''); if (!e.target.value) { $('#skParts').innerHTML = ''; return; }
    const parts = await getJson('/api/ws/skins/parts?src=' + encodeURIComponent(e.target.value));
    $('#skParts').innerHTML = parts.length > 1 ? parts.slice(0, 40).map((p) => `<label style="display:block"><input type="checkbox" data-part="${esc(p)}" checked> ${esc(p)}</label>`).join('') : '';
    ctx.pazl.viewGlb(e.target.value);
  });
  $('#skApply').onclick = () => busy('натягиваю скин…', async () => {
    const src = $('#skSrc').value; if (!src) throw new Error('выберите объект');
    const boxes = [...el.querySelectorAll('[data-part]')], on = boxes.filter((b) => b.checked).map((b) => b.dataset.part);
    const r = await post('/api/ws/skins/apply', { src, skin: skin(), parts: on.length < boxes.length ? on : null });
    await ctx.refresh(); await ctx.open(r.path); out(`✓ ${r.path}: частей ${r.parts}, ${r.kb} КБ`);
  });
  $('#skCustom').hidden = false; preview().catch((e) => out('⚠ ' + e.message));
}
