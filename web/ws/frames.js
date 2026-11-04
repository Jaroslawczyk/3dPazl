// 2D workshop "frames": keyframe sequences, inbetweening, player with onion skin, export (backend: pazl/core/frames2d.py).
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const post = (u, b) => fetch(u, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b || {}) })
  .then(async (r) => { const j = await r.json(); if (!r.ok) throw new Error(j.detail || r.status); return j; });
const readURL = (f) => new Promise((ok) => { const r = new FileReader(); r.onload = () => ok(r.result); r.readAsDataURL(f); });

export async function mount(el, ctx) {
  const row = 'display:flex;gap:6px;align-items:center;margin:3px 0';
  el.innerHTML = `<h4>Последовательность</h4>
    <div style="${row}"><select id="frSeq" style="flex:1"></select><button id="frSample" title="Создать тестовые кадры (мяч: скетч и цвет)">Пример</button></div>
    <div style="${row}"><input id="frNew" placeholder="новая / имя" style="flex:1"><label class="hint" style="cursor:pointer">📂 PNG<input id="frFiles" type="file" accept="image/png,image/*" multiple hidden></label></div>
    <h4>Промежуточные кадры</h4>
    <label class="hint" style="${row}">Между ключами <input id="frN" type="number" value="3" min="1" max="15" style="width:60px;margin-left:auto"></label>
    <label class="hint" style="${row}">Метод <select id="frMethod" style="margin-left:auto"><option value="flow">оптический поток (встроенный)</option><option value="blend">смешивание</option><option value="rife">RIFE (внешний)</option></select></label>
    <label class="hint" style="${row}">Линии <select id="frLine" style="margin-left:auto"><option value="auto">авто</option><option value="true">чёткие линии (скетч)</option><option value="false">цвет / заливка</option></select></label>
    <button id="frGo" style="width:100%">Сгенерировать</button>
    <h4>Просмотр</h4>
    <div style="${row}"><button id="frPlay">▶</button><input id="frScrub" type="range" min="0" value="0" style="flex:1"><span id="frNo" class="hint">0/0</span></div>
    <label class="hint" style="${row}">FPS <input id="frFps" type="number" value="12" min="1" max="60" style="width:55px"><span style="margin-left:auto"></span>
      <input id="frOnion" type="checkbox">калька <input id="frKeys" type="checkbox">только ключи</label>
    <h4>Проверка и экспорт</h4>
    <div style="${row}"><button id="frCheck" style="flex:1" title="Сводка качества + контактный лист">Проверить</button><button id="frGif" style="flex:1">GIF</button><button id="frSheet" style="flex:1">Лист</button></div>
    <div class="hint" id="frOut"></div>`;
  const $ = (s) => el.querySelector(s), out = $('#frOut'), v = ctx.view2d;
  let seq = null, frames = [], imgs = [], cur = 0, timer = null;
  const say = (t) => { out.innerHTML = t; };

  const shown = () => ($('#frKeys').checked ? frames.map((f, i) => [f, i]).filter(([f]) => f.key) : frames.map((f, i) => [f, i]));
  const draw = () => {
    const list = shown(); if (!list.length) return;
    cur = Math.max(0, Math.min(cur, list.length - 1));
    const [f, i] = list[cur], L = [];
    if ($('#frOnion').checked && !timer) {
      if (cur > 0) L.push({ img: imgs[list[cur - 1][1]], alpha: 0.25 });
      if (cur < list.length - 1) L.push({ img: imgs[list[cur + 1][1]], alpha: 0.25 });
    }
    L.push({ img: imgs[i], alpha: L.length ? 0.85 : 1 });
    v.draw(L, (g, fit) => { g.fillStyle = f.key ? '#4a8cff' : '#ff9628'; g.fillRect(fit.x, fit.y - 6 * fit.d, fit.w, 4 * fit.d); });
    $('#frScrub').max = list.length - 1; $('#frScrub').value = cur;
    $('#frNo').textContent = `${cur + 1}/${list.length}${f.key ? ' ключ' : ''}`;
  };
  const stop = () => { clearInterval(timer); timer = null; $('#frPlay').textContent = '▶'; };
  $('#frPlay').onclick = () => {
    if (timer) { stop(); draw(); return; }
    $('#frPlay').textContent = '⏸';
    timer = setInterval(() => { cur = (cur + 1) % shown().length; draw(); }, 1000 / Math.max(1, +$('#frFps').value));
  };
  $('#frScrub').oninput = () => { stop(); cur = +$('#frScrub').value; draw(); };
  $('#frOnion').onchange = draw; $('#frKeys').onchange = () => { cur = 0; draw(); };
  $('#frFps').onchange = () => { if (timer) { stop(); $('#frPlay').onclick(); } };

  const load = async (name) => {
    stop(); seq = name; if (!name) return;
    const j = await fetch(`/api/ws/frames/seq/${encodeURIComponent(name)}`).then((r) => r.json());
    frames = j.frames; $('#frFps').value = j.fps || 12;
    const t = Date.now();
    imgs = await Promise.all(frames.map((f) => v.img(`/files/${f.path}?t=${t}`)));
    cur = 0; draw();
    document.querySelectorAll('#wsModels .ws-model').forEach((m) => m.classList.toggle('on', m.dataset.p.split('/')[1] === name));
    say(`${esc(name)}: ${j.keys.length} ключ., ${frames.length} кадров${j.method ? ', ' + esc(j.method) : ''}`);
  };
  const seqs = async (sel) => {
    const l = await fetch('/api/ws/frames/seqs').then((r) => r.json());
    $('#frSeq').innerHTML = l.map((s) => `<option value="${esc(s.name)}">${esc(s.name)} (${s.keys}/${s.frames || s.keys})</option>`).join('') || '<option value="">— пусто —</option>';
    if (sel) $('#frSeq').value = sel;
    await ctx.refresh(); await load($('#frSeq').value);
  };
  ctx.pick = (path) => { const n = path.split('/')[1]; $('#frSeq').value = n; return load(n); };
  $('#frSeq').onchange = () => load($('#frSeq').value);
  $('#frSample').onclick = async () => { say('⏳ создаю пример…'); const j = await post('/api/ws/frames/sample'); await seqs(j.name); };
  $('#frFiles').onchange = async (e) => {
    const name = $('#frNew').value.trim() || seq || 'seq';
    const files = await Promise.all([...e.target.files].map(async (f) => ({ name: f.name, data: await readURL(f) })));
    try { const j = await post('/api/ws/frames/upload', { seq: name, files }); await seqs(j.name); } catch (er) { say('⚠ ' + esc(er.message)); }
    e.target.value = '';
  };
  $('#frGo').onclick = async () => {
    if (!seq) return say('Сначала выберите последовательность');
    stop(); say('⏳ считаю промежуточные кадры…'); const t0 = performance.now();
    try {
      const j = await post('/api/ws/frames/interpolate', { seq, n: +$('#frN').value, method: $('#frMethod').value,
        lineart: $('#frLine').value === 'auto' ? null : $('#frLine').value === 'true', fps: +$('#frFps').value });
      await seqs(seq);
      say(`✓ ${j.frames} кадров за ${((performance.now() - t0) / 1000).toFixed(1)} с<br>` +
        j.pairs.map((p) => `${esc(p.pair)}: двоение ${p.ghost.map((g) => g == null ? '—' : (g > 0.3 ? `<b style="color:#e66">${g}</b>` : g)).join(' ')}`).join('<br>'));
      $('#frPlay').onclick();
    } catch (er) { say('⚠ ' + esc(er.message)); }
  };
  $('#frCheck').onclick = async () => {
    if (!seq) return; stop(); say('⏳ проверяю…');
    const j = await fetch(`/api/ws/frames/check/${encodeURIComponent(seq)}`).then((r) => r.json());
    await v.show(`/files/${j.contact}?t=${Date.now()}`);
    say(`${j.frames} кадров ${j.size.join('×')}, неровность темпа ${j.pacing_flicker}${j.jumps_at.length ? ', скачки: ' + j.jumps_at.join(',') : ''}<br><span class="hint">синие — ключи, оранжевые — промежуточные. Клик по ползунку — вернуться к плееру.</span>`);
  };
  const exp = async (kind) => {
    if (!seq) return; say('⏳ экспорт…');
    try { const j = await post('/api/ws/frames/export', { seq, kind, fps: +$('#frFps').value });
      say(`✓ <a href="/files/${esc(j.path)}" target="_blank">${esc(j.path)}</a>${j.count ? ` · ${j.count} кадров, ${j.cols}×${j.rows}` : ''}`); } catch (er) { say('⚠ ' + esc(er.message)); }
  };
  $('#frGif').onclick = () => exp('gif'); $('#frSheet').onclick = () => exp('sheet');
  await seqs();
}
