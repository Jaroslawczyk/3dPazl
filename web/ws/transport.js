// Workshop "transport": parametric vehicles (backend: pazl/core/vehicles/).
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

export async function mount(el, ctx) {
  const cat = await fetch('/api/ws/transport/kinds').then((r) => r.json());
  const opts = cat.groups.map((g) => `<optgroup label="${esc(g.title)}">${g.kinds.map((k) => `<option value="${k.id}">${esc(k.title)}</option>`).join('')}</optgroup>`).join('');
  const row = 'class="hint" style="display:flex;gap:6px;align-items:center;margin:3px 0"';
  const num = (id, label, v, step, min, max) => `<label ${row}>${label}<input id="${id}" type="number" value="${v}" step="${step}" min="${min}" max="${max}" style="width:70px;margin-left:auto"></label>`;
  const color = (id, label, v) => `<label ${row}>${label} <input id="${id}Use" type="checkbox"><input id="${id}" type="color" value="${v}" style="margin-left:auto"></label>`;
  el.innerHTML = `<h4>Генератор транспорта</h4>
    <select id="trKind" style="width:100%">${opts}</select>
    <label ${row}>Детали<select id="trDetail" style="margin-left:auto">
      <option value="1">Силуэт</option><option value="2" selected>Обычные</option><option value="3">Все мелочи</option></select></label>
    <label ${row}>Окраска<select id="trLivery" style="margin-left:auto">${Object.entries(cat.liveries).map(([k, t]) => `<option value="${k}">${esc(t)}</option>`).join('')}</select></label>
    ${color('trCol', 'Основной цвет', '#c8342c')}${color('trCol2', 'Второй цвет', '#eef0f4')}
    ${num('trLen', 'Длина', 1, 0.05, 0.7, 1.5)}${num('trSize', 'Масштаб', 1, 0.1, 0.1, 5)}${num('trSeed', 'Вариант', 1, 1, 0, 9999)}
    <input id="trText" placeholder="номер, маршрут или надпись" style="width:100%;margin:3px 0" maxlength="14">
    <input id="trName" placeholder="имя файла (по умолчанию — вид)" style="width:100%;margin:3px 0">
    <button id="trGo" style="width:100%">Создать</button><div class="hint" id="trOut"></div>`;
  const $ = (s) => el.querySelector(s);
  const pick = (id) => ($(`#${id}Use`).checked ? $(`#${id}`).value : '');
  $('#trGo').onclick = async () => {
    const kind = $('#trKind').value, out = $('#trOut');
    out.textContent = '⏳ собираю…';
    const body = { kind, name: $('#trName').value.trim() || `${kind}_${$('#trSeed').value}`, params: {
      color: pick('trCol'), color2: pick('trCol2'), livery: $('#trLivery').value, text: $('#trText').value.trim(), detail: +$('#trDetail').value,
      length: +$('#trLen').value, size: +$('#trSize').value, seed: +$('#trSeed').value } };
    const r = await fetch('/api/ws/transport/make', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const j = await r.json();
    if (!r.ok) { out.textContent = '⚠ ' + (j.detail || r.status); return; }
    const [x, y, z] = j.size_m;
    out.textContent = `✓ ${j.path}: ${x}×${y}×${z} м, ${j.tris} треуг., узлов ${j.nodes.length}${j.decals.length ? ', декалей ' + j.decals.length : ''}`;
    await ctx.refresh(); await ctx.open(j.path);
  };
}
