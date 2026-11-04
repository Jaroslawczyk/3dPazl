// Workshop "items": parametric generator of dishes, food and small stuff (backend: pazl/core/items.py).
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

export async function mount(el, ctx) {
  const cat = await fetch('/api/ws/items/kinds').then((r) => r.json());
  const opts = cat.groups.map((g) => `<optgroup label="${esc(g.title)}">${g.kinds.map((k) => `<option value="${k.id}">${esc(k.title)}</option>`).join('')}</optgroup>`).join('');
  const num = (id, label, v, step, min, max) => `<label class="hint" style="display:flex;gap:6px;align-items:center;margin:3px 0">${label}<input id="${id}" type="number" value="${v}" step="${step}" min="${min}" max="${max}" style="width:70px;margin-left:auto"></label>`;
  el.innerHTML = `<h4>Генератор предметов</h4>
    <select id="itKind" style="width:100%">${opts}</select>
    ${num('itSize', 'Масштаб', 1, 0.1, 0.2, 5)}${num('itW', 'Ширина', 1, 0.1, 0.3, 3)}${num('itH', 'Высота', 1, 0.1, 0.3, 3)}
    ${num('itSeed', 'Вариант', 1, 1, 0, 9999)}${num('itSeg', 'Детализация', 24, 4, 8, 64)}
    <label class="hint" style="display:flex;gap:6px;align-items:center;margin:3px 0">Свой цвет <input id="itUseCol" type="checkbox"><input id="itCol" type="color" value="#3a6fb0" style="margin-left:auto"></label>
    <input id="itName" placeholder="имя файла (по умолчанию — вид)" style="width:100%;margin:3px 0">
    <button id="itGo" style="width:100%">Создать</button><div class="hint" id="itOut"></div>`;
  const $ = (s) => el.querySelector(s);
  $('#itGo').onclick = async () => {
    const kind = $('#itKind').value, out = $('#itOut');
    out.textContent = '⏳ генерирую…';
    const body = { kind, name: $('#itName').value.trim() || `${kind}_${$('#itSeed').value}`, params: {
      size: +$('#itSize').value, width: +$('#itW').value, height: +$('#itH').value, seed: +$('#itSeed').value,
      seg: +$('#itSeg').value, color: $('#itUseCol').checked ? $('#itCol').value : '' } };
    const r = await fetch('/api/ws/items/make', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const j = await r.json();
    if (!r.ok) { out.textContent = '⚠ ' + (j.detail || r.status); return; }
    const [x, y, z] = j.size_m.map((v) => Math.round(v * 100));
    out.textContent = `✓ ${j.path}: ${x}×${y}×${z} см, ${j.tris} треуг.`;
    await ctx.refresh(); await ctx.open(j.path);
  };
}
