// Shared by the characters and clothes workshops: show a character GLB and play its clips.
export const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
export const post = async (url, body) => {
  const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const j = await r.json();
  if (!r.ok) throw new Error(j.detail || r.status);
  return j;
};
export const getJson = (url) => fetch(url).then((r) => r.json());

export function viewer(ctx, ws) {
  const { pazl } = ctx;
  const V = { gltf: null, mixer: null, clip: '', raf: 0, last: 0 };
  V.pose = () => {  // rest pose: clay strokes and fitting are done on it
    V.mixer?.stopAllAction();
    V.gltf?.scene.traverse((o) => { if (o.isSkinnedMesh) o.skeleton.pose(); });
    pazl.invalidate();
  };
  V.play = (name) => {
    V.clip = name ?? V.clip;
    if (!V.mixer) return;
    V.mixer.stopAllAction();
    const c = V.gltf.animations.find((a) => a.name === V.clip);
    if (!c) return V.pose();
    const k = c.clone();  // walk on the spot: drop root travel
    k.tracks.forEach((t) => { if (t.name.endsWith('.position')) for (let i = 0; i < t.values.length; i += 3) t.values[i + 2] = t.values[2]; });
    V.mixer.clipAction(k).play();
  };
  V.show = async (path) => {
    const keep = pazl.camera.position.clone(), tgt = pazl.orbit.target.clone(), first = !V.gltf;
    V.gltf = await ctx.open(path);
    if (!V.gltf) return;
    if (!first) { pazl.camera.position.copy(keep); pazl.orbit.target.copy(tgt); pazl.orbit.update(); }
    V.gltf.scene.traverse((o) => { if (o.isSkinnedMesh) o.frustumCulled = false; });
    V.mixer = new pazl.THREE.AnimationMixer(V.gltf.scene);
    V.play();
  };
  const tick = () => {
    V.raf = requestAnimationFrame(tick);
    if (document.body.dataset.ws !== ws) { cancelAnimationFrame(V.raf); return; }
    const now = performance.now(), dt = Math.min(.1, (now - (V.last || now)) / 1000); V.last = now;
    if (V.mixer && V.clip) { V.mixer.update(dt); pazl.invalidate(); }
  };
  tick();
  return V;
}
