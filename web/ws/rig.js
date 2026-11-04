// Workshop "rig": skeleton, automatic weights, animation presets/keys, motion checks (backend: pazl/core/rig, no Blender).
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const post = async (url, body) => {
  const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const j = await r.json();
  if (!r.ok) throw new Error(j.detail || r.status);
  return j;
};
const S = { rig: null, gltf: null, mixer: null, action: null, helper: null, t: 0, play: true, speed: 1, inPlace: true, check: null, raf: 0 };

export async function mount(el, ctx) {
  const { pazl } = ctx;
  const meta = await fetch('/api/ws/rig/templates').then((r) => r.json());
  const glbs = await fetch('/api/glbs').then((r) => r.json()).catch(() => []);
  const bl = document.querySelector('#wsBlender');
  if (bl) bl.textContent = '✓ Встроенные инструменты: Blender не нужен';
  const opt = (o) => Object.entries(o).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('');
  const row = 'style="display:flex;gap:4px;align-items:center;margin:3px 0"';
  el.innerHTML = `<h4>1. Модель и скелет</h4>
    <div ${row}><select id="rgOpen" style="flex:1"><option value="">— открыть риг —</option>${meta.rigs.map((r) => `<option>${esc(r)}</option>`).join('')}</select></div>
    <div ${row}><select id="rgSrc" style="flex:1"><option value="">— меш (GLB) —</option>${glbs.map((g) => `<option>${esc(g.path)}</option>`).join('')}</select>
      <button id="rgMan" title="Сделать тестовый манекен-человечка">Манекен</button></div>
    <div ${row}><input id="rgName" placeholder="имя рига" style="flex:1"><select id="rgTpl">${opt(meta.templates)}</select></div>
    <button id="rgAuto" style="width:100%">Создать скелет</button>
    <h4>2. Кости и веса</h4>
    <div ${row}><select id="rgBone" style="flex:1"></select></div>
    <div ${row}>голова <input id="rgHx" type="number" step="0.01" style="width:58px"><input id="rgHy" type="number" step="0.01" style="width:58px"><input id="rgHz" type="number" step="0.01" style="width:58px"></div>
    <div ${row}><button id="rgBoneSet" style="flex:1">Сдвинуть сустав</button><button id="rgW" style="flex:1">Пересчитать веса</button></div>
    <h4>3. Анимация</h4>
    <div ${row}><select id="rgPreset" style="flex:1">${opt(meta.presets)}</select><button id="rgMake">Создать</button></div>
    <div ${row}><select id="rgClip" style="flex:1"></select><button id="rgPlay">⏸</button></div>
    <input id="rgScrub" type="range" min="0" max="1" step="1" value="0" style="width:100%">
    <div id="rgStrip" style="display:flex;height:10px;gap:1px;margin:2px 0;cursor:pointer"></div>
    <div class="hint" id="rgFrame"></div>
    <div ${row} class="hint"><label><input id="rgBones" type="checkbox" checked> кости</label>
      <label><input id="rgXray" type="checkbox"> рентген</label><label><input id="rgInPlace" type="checkbox" checked> на месте</label>
      <select id="rgSpeed"><option>0.25</option><option>0.5</option><option selected>1</option><option>2</option></select></div>
    <div ${row} class="hint">ключ x/y/z° <input id="rgKx" type="number" value="0" style="width:44px"><input id="rgKy" type="number" value="0" style="width:44px"><input id="rgKz" type="number" value="0" style="width:44px"><button id="rgKey" title="Поворот выбранной кости на текущем кадре; соседние кадры плавно подстроятся">Ключ</button></div>
    <h4>4. Проверка движения</h4>
    <button id="rgCheck" style="width:100%">Проверить клип</button>
    <pre id="rgOut" class="hint" style="white-space:pre-wrap;font-size:11px;margin:4px 0"></pre>`;
  const $ = (s) => el.querySelector(s);
  const out = (t) => { $('#rgOut').textContent = t; };
  const busy = async (msg, fn) => { out('⏳ ' + msg); try { return await fn(); } catch (e) { out('⚠ ' + e.message); throw e; } };

  const fillRig = () => {
    const r = S.rig;
    $('#rgName').value = r.name; $('#rgTpl').value = r.template;
    $('#rgBone').innerHTML = r.bones.map((b) => `<option>${esc(b.name)}</option>`).join('');
    $('#rgClip').innerHTML = Object.keys(r.clips).map((c) => `<option>${esc(c)}</option>`).join('') || '<option value="">нет клипов</option>';
    showBone();
  };
  const showBone = () => {
    const b = S.rig?.bones.find((x) => x.name === $('#rgBone').value);
    if (!b) return;
    ['x', 'y', 'z'].forEach((a, i) => { $('#rgH' + a).value = b.head[i]; });
  };
  const loadRig = async (name, clip) => {
    S.rig = await fetch('/api/ws/rig/get/' + encodeURIComponent(name)).then((r) => r.json());
    fillRig();
    if (clip) $('#rgClip').value = clip;
    const ex = await post('/api/ws/rig/export', { name });
    await ctx.refresh();
    S.gltf = await ctx.open(ex.path);
    setupView();
    return ex;
  };
  const clipObj = () => S.gltf?.animations.find((a) => a.name === $('#rgClip').value) || S.gltf?.animations[0];
  const setupView = () => {
    const { THREE, root } = pazl;
    if (!S.gltf) return;
    S.helper = new THREE.SkeletonHelper(S.gltf.scene);
    S.helper.material.depthTest = false; S.helper.material.linewidth = 2; S.helper.renderOrder = 10;
    S.helper.visible = $('#rgBones').checked;
    root.add(S.helper);
    S.gltf.scene.traverse((o) => { if (o.isSkinnedMesh) o.frustumCulled = false; });
    xray();
    S.mixer = new THREE.AnimationMixer(S.gltf.scene);
    playClip();
  };
  const xray = () => S.gltf?.scene.traverse((o) => {
    if (o.isMesh) { o.material.transparent = $('#rgXray').checked; o.material.opacity = $('#rgXray').checked ? 0.35 : 1; o.material.needsUpdate = true; }
  });
  const playClip = () => {
    S.mixer.stopAllAction(); S.action = null; S.check = null; drawStrip();
    const c0 = clipObj();
    if (!c0) { $('#rgFrame').textContent = 'Нет клипов: создайте анимацию'; return; }
    const c = c0.clone();
    if (S.inPlace) c.tracks.forEach((tr) => {  // drop forward root motion for viewing
      if (tr.name.endsWith('.position')) for (let i = 0; i < tr.values.length; i += 3) tr.values[i + 2] = tr.values[2];
    });
    S.action = S.mixer.clipAction(c); S.action.play(); S.t = 0;
    const info = S.rig.clips[c0.name] || { fps: 30, frames: Math.round(c.duration * 30) };
    S.fps = info.fps; S.frames = info.frames;
    $('#rgScrub').max = S.frames;
    $('#rgCheck').disabled = false;
  };
  const frame = () => Math.round(S.t * (S.fps || 30));
  const drawStrip = () => {
    const st = $('#rgStrip');
    if (!S.check || !S.frames) { st.innerHTML = ''; return; }
    st.innerHTML = Array.from({ length: S.frames + 1 }, (_, f) => {
      const bad = S.check.frames[f];
      return `<div data-f="${f}" title="кадр ${f}${bad ? ': ' + esc(bad.join(', ')) : ''}" style="flex:1;background:${bad ? '#e0533d' : '#3d9e5a'}"></div>`;
    }).join('');
    st.querySelectorAll('div').forEach((d) => { d.onclick = () => { S.play = false; $('#rgPlay').textContent = '▶'; S.t = +d.dataset.f / S.fps; }; });
  };

  const tick = () => {
    S.raf = requestAnimationFrame(tick);
    if (document.body.dataset.ws !== 'rig' || !el.isConnected) { cancelAnimationFrame(S.raf); return; }
    const now = performance.now(), dt = Math.min(0.1, (now - (S.last || now)) / 1000); S.last = now;
    if (!S.action || !S.mixer) return;
    const dur = S.action.getClip().duration || 1;
    if (S.play) S.t = (S.t + dt * S.speed) % dur;
    S.action.time = S.t; S.mixer.update(0);
    const f = frame();
    if (+$('#rgScrub').value !== f) $('#rgScrub').value = f;
    const bad = S.check?.frames[f];
    $('#rgFrame').textContent = `кадр ${f}/${S.frames}` + (bad ? ' ⚠ ' + bad.join(', ') : '');
    pazl.invalidate();
  };
  cancelAnimationFrame(S.raf); S.last = 0; tick();

  $('#rgOpen').onchange = (e) => e.target.value && busy('открываю…', () => loadRig(e.target.value)).then(() => out(''));
  $('#rgMan').onclick = () => busy('строю манекен…', async () => {
    const m = await post('/api/ws/rig/mannequin', { name: 'mannequin' });
    $('#rgSrc').insertAdjacentHTML('afterbegin', `<option>${esc(m.src)}</option>`); $('#rgSrc').value = m.src;
    $('#rgName').value ||= 'mannequin';
    await ctx.refresh(); S.gltf = null; await ctx.open(m.src);
    out(`✓ манекен ${m.verts} вершин, ${m.tris} треуг. Теперь «Создать скелет».`);
  });
  $('#rgAuto').onclick = () => busy('подгоняю скелет и считаю веса…', async () => {
    const src = $('#rgSrc').value || S.rig?.src;
    if (!src) throw new Error('выберите меш или сделайте манекен');
    const r = await post('/api/ws/rig/auto', { name: $('#rgName').value || src.split('/').pop().replace('.glb', ''), src, template: $('#rgTpl').value });
    const ex = await loadRig(r.name);
    out(`✓ ${r.bones} костей, меш ${r.size_m.join('×')} м; веса: без весов ${ex.unweighted}, пустые кости: ${ex.empty_bones.join(', ') || 'нет'}`);
  });
  $('#rgBone').onchange = showBone;
  $('#rgBoneSet').onclick = () => busy('двигаю сустав…', async () => {
    const name = $('#rgBone').value, b = S.rig.bones.find((x) => x.name === name);
    const head = ['x', 'y', 'z'].map((a) => +$('#rgH' + a).value);
    const d = head.map((v, i) => v - b.head[i]);
    // move the joint: this bone's head, the parent's tail if it ended there, children heads stay
    const ch = [{ name, head, tail: b.tail }];
    const p = S.rig.bones.find((x) => x.name === b.parent);
    if (p && p.tail.every((v, i) => Math.abs(v - b.head[i]) < 1e-4)) ch.push({ name: p.name, tail: head });
    await post('/api/ws/rig/bones', { name: S.rig.name, bones: ch });
    await loadRig(S.rig.name, $('#rgClip').value); $('#rgBone').value = name; showBone();
    out(`✓ ${name} сдвинут на ${d.map((v) => v.toFixed(2)).join(', ')} м, веса пересчитаны`);
  });
  $('#rgW').onclick = () => busy('считаю веса…', async () => {
    const st = await post('/api/ws/rig/weights', { name: S.rig.name });
    await loadRig(S.rig.name, $('#rgClip').value);
    out(`✓ веса: ${st.verts} вершин, без весов ${st.unweighted}, в среднем ${st.avg_influences} кости на вершину`);
  });
  $('#rgMake').onclick = () => busy('создаю анимацию…', async () => {
    if (!S.rig) throw new Error('сначала создайте скелет');
    const a = await post('/api/ws/rig/anim', { name: S.rig.name, preset: $('#rgPreset').value });
    await loadRig(S.rig.name, a.clip);
    out(`✓ ${a.clip}: ${a.frames} кадров @${a.fps}, проход ${a.travel_m} м за цикл. Нажмите «Проверить клип».`);
  });
  $('#rgClip').onchange = () => S.mixer && playClip();
  $('#rgPlay').onclick = () => { S.play = !S.play; $('#rgPlay').textContent = S.play ? '⏸' : '▶'; };
  $('#rgScrub').oninput = (e) => { S.play = false; $('#rgPlay').textContent = '▶'; S.t = +e.target.value / (S.fps || 30); };
  $('#rgBones').onchange = (e) => { if (S.helper) S.helper.visible = e.target.checked; pazl.invalidate(); };
  $('#rgXray').onchange = () => { xray(); pazl.invalidate(); };
  $('#rgInPlace').onchange = (e) => { S.inPlace = e.target.checked; if (S.mixer) playClip(); };
  $('#rgSpeed').onchange = (e) => { S.speed = +e.target.value; };
  $('#rgKey').onclick = () => busy('ставлю ключ…', async () => {
    const clip = $('#rgClip').value, f = frame();
    await post('/api/ws/rig/key', { name: S.rig.name, clip, bone: $('#rgBone').value, frame: f, euler: ['x', 'y', 'z'].map((a) => +$('#rgK' + a).value) });
    await loadRig(S.rig.name, clip); S.play = false; $('#rgPlay').textContent = '▶'; S.t = f / S.fps;
    out(`✓ ключ ${$('#rgBone').value} на кадре ${f}`);
  });
  $('#rgCheck').onclick = () => busy('проверяю движение…', async () => {
    const r = await post('/api/ws/rig/check', { name: S.rig.name, clip: $('#rgClip').value });
    S.check = r; drawStrip();
    out(r.text.replace(/ BAD/g, ' ⚠').replace(/ OK/g, ' ✓'));
  });
}
