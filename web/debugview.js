// Viewport checks for any model on screen (project, GLB viewer, every workshop):
// UV checker — a numbered coloured grid instead of the materials, shows stretching, seams and flipped islands;
// vertex normals — a short line out of every vertex, coloured by its direction. Meshes without UVs turn magenta.
export function initDebugView({ THREE, scene, root, invalidate, uvBox, nBox }) {
  const D = { model: null, lines: null, meshes: [], tex: null, len: 0 };

  function checker() {
    const S = 1024, n = 8, c = S / n, cv = document.createElement('canvas');
    cv.width = cv.height = S;
    const g = cv.getContext('2d');
    const quads = [['#c81e1e', '#e23a3a'], ['#16a31a', '#2cc431'], ['#3a4fd8', '#5b6ef0'], ['#e08a12', '#f5a63a']];
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
      const q = quads[(y < n / 2 ? 0 : 2) + (x < n / 2 ? 0 : 1)];
      g.fillStyle = q[(x + y) % 2]; g.fillRect(x * c, y * c, c, c);
      g.fillStyle = 'rgba(0,0,0,.18)';  // finer grid inside each cell
      for (let k = 1; k < 4; k++) { g.fillRect(x * c + k * c / 4, y * c, 1, c); g.fillRect(x * c, y * c + k * c / 4, c, 1); }
      g.fillStyle = '#fff'; g.font = `bold ${c * .26}px sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText('ABCDEFGH'[x] + (n - y), x * c + c / 2, y * c + c / 2);
      g.beginPath(); g.moveTo(x * c + c * .14, y * c + c * .3); g.lineTo(x * c + c * .14, y * c + c * .12); g.lineTo(x * c + c * .32, y * c + c * .12);
      g.strokeStyle = 'rgba(255,255,255,.75)'; g.lineWidth = 3; g.stroke();  // corner tick: shows which way the island is turned
    }
    g.strokeStyle = '#000'; g.lineWidth = 4;
    for (let i = 0; i <= n; i++) { g.beginPath(); g.moveTo(i * c, 0); g.lineTo(i * c, S); g.moveTo(0, i * c); g.lineTo(S, i * c); g.stroke(); }
    const t = new THREE.CanvasTexture(cv);
    t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8;
    return t;
  }

  function setUV(on) {
    root.traverse((o) => {
      if (!o.isMesh) return;
      if (on && !o.userData.dbgMat) {
        D.tex ||= checker();
        o.userData.dbgMat = o.material;
        const has = !!o.geometry.attributes.uv;
        o.material = new THREE.MeshStandardMaterial({ map: has ? D.tex : null, color: has ? 0xffffff : 0xff00ff, roughness: .75, side: THREE.DoubleSide, wireframe: !!o.userData.dbgMat.wireframe });
      } else if (!on && o.userData.dbgMat) {
        o.material.dispose(); o.material = o.userData.dbgMat; delete o.userData.dbgMat;
      }
    });
  }

  function dropNormals() {
    if (!D.lines) return;
    D.lines.removeFromParent(); D.lines.geometry.dispose(); D.lines.material.dispose(); D.lines = null; D.meshes = [];
  }
  function buildNormals() {
    dropNormals();
    root.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(root);
    if (box.isEmpty()) return;
    D.len = box.getSize(new THREE.Vector3()).length() * .012;
    let total = 0;
    root.traverse((o) => { if (o.isMesh && o.geometry.attributes.normal) { D.meshes.push(o); total += o.geometry.attributes.position.count; } });
    D.step = Math.max(1, Math.ceil(total / 150000));  // huge scenes: every k-th vertex, keeps it interactive
    const count = D.meshes.reduce((s, o) => s + Math.ceil(o.geometry.attributes.position.count / D.step), 0);
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(count * 6), 3));
    geo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(count * 6), 3));
    D.lines = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ vertexColors: true, depthTest: true }));
    D.lines.frustumCulled = false; D.lines.renderOrder = 2;
    scene.add(D.lines);
    D.skinned = D.meshes.some((o) => o.isSkinnedMesh);
    updateNormals();
  }
  const p = new THREE.Vector3(), q = new THREE.Vector3(), nm = new THREE.Matrix3();
  function updateNormals() {
    const P = D.lines.geometry.attributes.position.array, C = D.lines.geometry.attributes.color.array;
    let k = 0;
    for (const o of D.meshes) {
      const pos = o.geometry.attributes.position, nor = o.geometry.attributes.normal;
      nm.getNormalMatrix(o.matrixWorld);
      for (let i = 0; i < pos.count; i += D.step) {
        p.fromBufferAttribute(pos, i); q.fromBufferAttribute(nor, i).add(p);
        if (o.isSkinnedMesh) { o.applyBoneTransform(i, p); o.applyBoneTransform(i, q); q.sub(p).normalize(); } else q.sub(p);
        p.applyMatrix4(o.matrixWorld); q.applyMatrix3(nm).normalize();
        const r = Math.abs(q.x) * .8 + .2, g = Math.abs(q.y) * .8 + .2, b = Math.abs(q.z) * .8 + .2;
        P[k] = p.x; P[k + 1] = p.y; P[k + 2] = p.z;
        P[k + 3] = p.x + q.x * D.len; P[k + 4] = p.y + q.y * D.len; P[k + 5] = p.z + q.z * D.len;
        C[k] = r * .4; C[k + 1] = g * .4; C[k + 2] = b * .4; C[k + 3] = r; C[k + 4] = g; C[k + 5] = b;
        k += 6;
      }
    }
    D.lines.geometry.attributes.position.needsUpdate = D.lines.geometry.attributes.color.needsUpdate = true;
  }

  const apply = () => {
    D.model = root.children[0] || null;
    setUV(uvBox.checked);
    if (nBox.checked) buildNormals(); else dropNormals();
    invalidate();
  };
  uvBox.onchange = apply; nBox.onchange = apply;
  // called from the render loop: a newly loaded model gets the active checks; skinned normals follow the animation
  return function tick() {
    if (!uvBox.checked && !nBox.checked) { if (D.lines) dropNormals(); return; }
    if ((root.children[0] || null) !== D.model) apply();
    else if (D.lines && D.skinned) { root.updateMatrixWorld(true); updateNormals(); }
  };
}
