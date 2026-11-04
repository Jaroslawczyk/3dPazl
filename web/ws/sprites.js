// 2D workshop "sprites": import, colour key, trim, pivot, sprite sheet pack/unpack, animation preview (backend: pazl/core/sprites.py).
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const post = (u, b) => fetch(u, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b || {}) })
  .then(async (r) => { const j = await r.json(); if (!r.ok) throw new Error(j.detail || r.status); return j; });
const readURL = (f) => new Promise((ok) => { const r = new FileReader(); r.onload = () => ok(r.result); r.readAsDataURL(f); });

export async function mount(el, ctx) {
  const row = 'display:flex;gap:6px;align-items:center;margin:3px 0';
  el.innerHTML = `<h4>Спрайт</h4>
    <div style="${row}"><label class="hint" style="cursor:pointer;flex:1">📂 Импорт PNG/JPG<input id="spFiles" type="file" accept="image/*" multiple hidden></label><button id="spSample">Пример</button></div>
    <div class="hint" id="spCur">Выберите файл слева</div>
    <label class="hint" style="${row}">Фон-ключ <input id="spAuto" type="checkbox" checked>авто <input id="spCol" type="color" value="#ff00ff"> допуск <input id="spTol" type="number" value="0.12" step="0.02" min="0" max="1" style="width:55px"></label>
    <div style="${row}"><button id="spKey" style="flex:1">Убрать фон</button><button id="spTrim" style="flex:1">Обрезать</button><button id="spPiv" style="flex:1" title="Затем кликните по спрайту">Точка опоры</button></div>
    <h4>Лист спрайтов</h4>
    <div style="${row}"><button id="spAdd" style="flex:1">+ в лист</button><button id="spClr">очистить</button></div>
    <div class="hint" id="spList">кадров в листе: 0</div>
    <div style="${row}"><input id="spName" value="sheet" style="flex:1"><label class="hint">колонок <input id="spCols" type="number" value="0" min="0" style="width:45px"></label></div>
    <button id="spPack" style="width:100%">Собрать лист</button>
    <label class="hint" style="${row}">Разрезать: кол. <input id="spUc" type="number" value="0" min="0" style="width:45px"> стр. <input id="spUr" type="number" value="0" min="0" style="width:45px"><button id="spUnpack" style="margin-left:auto">Разрезать</button></label>
    <div style="${row}"><button id="spAnim" style="flex:1">▶ Анимация листа</button><span class="hint">FPS</span><input id="spFps" type="number" value="10" min="1" max="60" style="width:50px"></div>
    <div class="hint" id="spOut"></div>`;
  const $ = (s) => el.querySelector(s), v = ctx.view2d, say = (t) => { $('#spOut').innerHTML = t; };
  let cur = null, meta = {}, picking = false, timer = null, list = [];
  const stop = () => { clearInterval(timer); timer = null; $('#spAnim').textContent = '▶ Анимация листа'; };
  const show = async () => {
    if (!cur) return;
    const im = await v.img(`/files/${cur}?t=${meta.t}`);
    v.draw([{ img: im }], (g, f) => {
      const [px, py] = meta.pivot || [0.5, 1];
      const x = f.x + px * f.w, y = f.y + py * f.h, r = 8 * f.d;
      g.strokeStyle = '#e33'; g.lineWidth = 2 * f.d; g.beginPath(); g.moveTo(x - r, y); g.lineTo(x + r, y); g.moveTo(x, y - r); g.lineTo(x, y + r); g.stroke();
      if (meta.frames && !timer) { g.strokeStyle = 'rgba(60,140,255,.7)'; g.lineWidth = f.d;
        meta.frames.forEach(([a, b, w, h]) => g.strokeRect(f.x + a * f.s, f.y + b * f.s, w * f.s, h * f.s)); }
    });
  };
  const pick = async (path) => {
    stop(); cur = path; meta = { ...(await fetch(`/api/ws/sprites/info?path=${encodeURIComponent(path)}`).then((r) => r.json())), t: Date.now() };
    document.querySelectorAll('#wsModels .ws-model').forEach((m) => m.classList.toggle('on', m.dataset.p === path));
    $('#spCur').innerHTML = `<b>${esc(path)}</b> ${meta.size.join('×')}${meta.pivot ? ' · опора ' + meta.pivot.join(', ') : ''}${meta.count ? ` · лист ${meta.cols}×${meta.rows}, ${meta.count} кадров` : ''}`;
    await show();
  };
  ctx.pick = pick;
  v.canvas.onclick = async (e) => {
    if (!picking || !cur) return; picking = false; v.canvas.style.cursor = '';
    const f = v.draw([{ img: await v.img(`/files/${cur}?t=${meta.t}`) }]), r = v.canvas.getBoundingClientRect();
    const x = ((e.clientX - r.left) * f.d - f.x) / f.w, y = ((e.clientY - r.top) * f.d - f.y) / f.h;
    await post('/api/ws/sprites/op', { path: cur, op: 'pivot', x: Math.max(0, Math.min(1, x)), y: Math.max(0, Math.min(1, y)) });
    await pick(cur); say('✓ точка опоры сохранена');
  };
  const op = async (body, msg) => { if (!cur) return say('Сначала выберите спрайт'); stop();
    try { const j = await post('/api/ws/sprites/op', { path: cur, ...body }); await ctx.refresh(); await pick(j.path || cur); say(msg(j)); } catch (er) { say('⚠ ' + esc(er.message)); } };
  $('#spKey').onclick = () => op({ op: 'colorkey', color: $('#spAuto').checked ? 'auto' : $('#spCol').value, tol: +$('#spTol').value },
    (j) => `✓ фон ${j.key} убран (${Math.round(j.transparent * 100)}% прозрачно) → ${esc(j.path)}`);
  $('#spTrim').onclick = () => op({ op: 'trim' }, (j) => `✓ обрезано до ${j.size.join('×')}`);
  $('#spPiv').onclick = () => { if (!cur) return; picking = true; v.canvas.style.cursor = 'crosshair'; say('Кликните по спрайту, где должна быть опора'); };
  $('#spUnpack').onclick = () => op({ op: 'unpack', cols: +$('#spUc').value, rows: +$('#spUr').value }, (j) => `✓ ${j.count} кадров → ${esc(j.dir)}/`);
  const showList = () => { $('#spList').textContent = `кадров в листе: ${list.length}` + (list.length ? ' — ' + list.map((p) => p.split('/').pop()).join(', ') : ''); };
  $('#spAdd').onclick = () => { if (cur) { list.push(cur); showList(); } };
  $('#spClr').onclick = () => { list = []; showList(); };
  $('#spPack').onclick = async () => {
    if (!list.length) return say('Добавьте кадры кнопкой «+ в лист»');
    try { const j = await post('/api/ws/sprites/pack', { paths: list, name: $('#spName').value, cols: +$('#spCols').value });
      await ctx.refresh(); await pick(j.path); say(`✓ лист ${j.size.join('×')}: ${j.count} кадров по ${j.cell.join('×')}`); } catch (er) { say('⚠ ' + esc(er.message)); }
  };
  $('#spAnim').onclick = async () => {
    if (timer) { stop(); return show(); }
    if (!meta.frames) return say('У выбранного файла нет разметки листа: соберите лист или выберите sheet.png');
    const im = await v.img(`/files/${cur}?t=${meta.t}`), [cw, ch] = meta.cell; let i = 0;
    const cell = document.createElement('canvas'); cell.width = cw; cell.height = ch; const cg = cell.getContext('2d');
    $('#spAnim').textContent = '⏸ Стоп';
    timer = setInterval(() => { const [x, y] = meta.frames[i]; cg.clearRect(0, 0, cw, ch); cg.drawImage(im, x, y, cw, ch, 0, 0, cw, ch);
      v.draw([{ img: cell }]); i = (i + 1) % meta.frames.length; }, 1000 / Math.max(1, +$('#spFps').value));
  };
  $('#spSample').onclick = async () => { const j = await post('/api/ws/sprites/sample'); await ctx.refresh(); await pick(j.path); };
  $('#spFiles').onchange = async (e) => {
    const files = await Promise.all([...e.target.files].map(async (f) => ({ name: f.name, data: await readURL(f) })));
    const j = await post('/api/ws/sprites/upload', { files }); await ctx.refresh(); if (j.paths[0]) await pick(j.paths[0]); e.target.value = '';
  };
}
