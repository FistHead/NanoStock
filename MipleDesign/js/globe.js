/* global THREE */
const COUNTRY_META = {  sun: { title: 'Республика Солнца', color: 0xfff3c4 },
  amber: { title: 'Союз Янтаря', color: 0xf0d890 },
  risk: { title: 'Остров Риска', color: 0xe8d574 },
  system: { title: 'Королевство Системы', color: 0xfffef5 },
  intuit: { title: 'Интуитивная Федерация', color: 0xf5e6a3 },
  north: { title: 'Северный Альянс', color: 0xe8c860 }
};

const COUNTRY_IDS = Object.keys(COUNTRY_META);

function latLonToVec3(lat, lon) {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -Math.sin(phi) * Math.cos(theta),
    Math.cos(phi),
    Math.sin(phi) * Math.sin(theta)
  ).normalize();
}

function randomSeeds(count = 6) {
  const seeds = [];
  const ids = [...COUNTRY_IDS];
  for (let i = ids.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [ids[i], ids[j]] = [ids[j], ids[i]];
  }
  for (let i = 0; i < count; i++) {
    const lat = (Math.random() - 0.5) * 140;
    const lon = Math.random() * 360 - 180;
    seeds.push({ id: ids[i % ids.length], pos: latLonToVec3(lat, lon) });
  }
  return seeds;
}

function nearestCountryId(point, seeds) {
  let best = seeds[0].id;
  let bestDot = -Infinity;
  for (const s of seeds) {
    const d = point.dot(s.pos);
    if (d > bestDot) {
      bestDot = d;
      best = s.id;
    }
  }
  return best;
}

class ProceduralGlobe {
  constructor(container, options = {}) {
    this.container = container;
    this.onSelect = options.onSelect || (() => {});
    this.seeds = options.seeds || randomSeeds();
    this.detail = 5;
    this.selectedId = options.initialCountry || 'risk';

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xfff9e6);

    const w = container.clientWidth || 640;
    const h = container.clientHeight || 480;
    this.camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    this.camera.position.set(0, 0, 2.8);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(this.renderer.domElement);

    const amb = new THREE.AmbientLight(0xffffff, 0.85);
    const dir = new THREE.DirectionalLight(0xffffff, 0.55);
    dir.position.set(2, 2, 3);
    this.scene.add(amb, dir);

    this.root = new THREE.Group();
    this.scene.add(this.root);

    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.faceCountryIds = [];
    this.countryMesh = null;
    this.borderLines = null;
    this.isDragging = false;
    this.dragMoved = false;
    this.prevPointer = { x: 0, y: 0 };
    this.rotVelocity = { x: 0, y: 0 };

    this._buildMesh();
    this._bindEvents();
    this._animate();
    this.setSelectedCountry(this.selectedId);
  }

  regenerate() {
    this.seeds = randomSeeds();
    this._disposeMesh();
    this._buildMesh();
    if (this.selectedId) this.setSelectedCountry(this.selectedId);
  }

  setSelectedCountry(id) {
    this.selectedId = id;
    if (!this.countryMesh) return;
    const attr = this.countryMesh.geometry.attributes.color;
    const base = new THREE.Color();
    const geo = this.countryMesh.geometry;
    const index = geo.index;
    const triCount = index.count / 3;
    for (let t = 0; t < triCount; t++) {
      const cid = this.faceCountryIds[t];
      const isSel = cid === id;
      const meta = COUNTRY_META[cid] || { color: 0xfffef5 };
      base.setHex(meta.color);
      if (isSel) base.offsetHSL(0, 0, -0.08);
      const verts = [index.getX(t * 3), index.getX(t * 3 + 1), index.getX(t * 3 + 2)];
      verts.forEach(vi => attr.setXYZ(vi, base.r, base.g, base.b));
    }
    attr.needsUpdate = true;
  }

  _disposeMesh() {
    if (this.countryMesh) {
      this.countryMesh.geometry.dispose();
      this.countryMesh.material.dispose();
      this.root.remove(this.countryMesh);
    }
    if (this.borderLines) {
      this.borderLines.geometry.dispose();
      this.borderLines.material.dispose();
      this.root.remove(this.borderLines);
    }
  }

  _buildMesh() {
    const geo = new THREE.IcosahedronGeometry(1, this.detail);
    const pos = geo.attributes.position;
    const index = geo.index;
    const triCount = index.count / 3;

    const vertexColors = new Float32Array(pos.count * 3);
    this.faceCountryIds = [];
    const borderVerts = [];

    for (let t = 0; t < triCount; t++) {
      const ia = index.getX(t * 3);
      const ib = index.getX(t * 3 + 1);
      const ic = index.getX(t * 3 + 2);
      const va = new THREE.Vector3(pos.getX(ia), pos.getY(ia), pos.getZ(ia)).normalize();
      const vb = new THREE.Vector3(pos.getX(ib), pos.getY(ib), pos.getZ(ib)).normalize();
      const vc = new THREE.Vector3(pos.getX(ic), pos.getY(ic), pos.getZ(ic)).normalize();
      const centroid = va.clone().add(vb).add(vc).divideScalar(3).normalize();
      const cid = nearestCountryId(centroid, this.seeds);
      this.faceCountryIds.push(cid);
      const c = new THREE.Color(COUNTRY_META[cid]?.color ?? 0xfffef5);
      [ia, ib, ic].forEach(vi => {
        vertexColors[vi * 3] = c.r;
        vertexColors[vi * 3 + 1] = c.g;
        vertexColors[vi * 3 + 2] = c.b;
      });
    }

    geo.setAttribute('color', new THREE.BufferAttribute(vertexColors, 3));
    geo.computeVertexNormals();

    this.countryMesh = new THREE.Mesh(
      geo,
      new THREE.MeshLambertMaterial({ vertexColors: true, flatShading: true })
    );
    this.root.add(this.countryMesh);

    const edgeMap = new Map();
    const faceOfTri = (t, edgeKey) => {
      if (!edgeMap.has(edgeKey)) edgeMap.set(edgeKey, []);
      edgeMap.get(edgeKey).push(t);
    };

    for (let t = 0; t < triCount; t++) {
      const verts = [
        index.getX(t * 3),
        index.getX(t * 3 + 1),
        index.getX(t * 3 + 2)
      ];
      for (let e = 0; e < 3; e++) {
        const a = verts[e];
        const b = verts[(e + 1) % 3];
        const key = a < b ? `${a}_${b}` : `${b}_${a}`;
        faceOfTri(t, key);
      }
    }

    const scale = 1.002;
    edgeMap.forEach((faces, key) => {
      if (faces.length !== 2) return;
      if (this.faceCountryIds[faces[0]] === this.faceCountryIds[faces[1]]) return;
      const [a, b] = key.split('_').map(Number);
      const pa = new THREE.Vector3(pos.getX(a), pos.getY(a), pos.getZ(a)).normalize().multiplyScalar(scale);
      const pb = new THREE.Vector3(pos.getX(b), pos.getY(b), pos.getZ(b)).normalize().multiplyScalar(scale);
      borderVerts.push(pa.x, pa.y, pa.z, pb.x, pb.y, pb.z);
    });

    const borderGeo = new THREE.BufferGeometry();
    borderGeo.setAttribute('position', new THREE.Float32BufferAttribute(borderVerts, 3));
    this.borderLines = new THREE.LineSegments(
      borderGeo,
      new THREE.LineBasicMaterial({ color: 0x2a2618, linewidth: 1 })
    );
    this.root.add(this.borderLines);

    if (this.selectedId) this.setSelectedCountry(this.selectedId);
  }

  _bindEvents() {
    const el = this.renderer.domElement;
    el.style.cursor = 'grab';

    const updatePointer = e => {
      const rect = el.getBoundingClientRect();
      this.pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    };

    el.addEventListener('pointerdown', e => {
      this.isDragging = true;
      this.dragMoved = false;
      this.prevPointer = { x: e.clientX, y: e.clientY };
      updatePointer(e);
      el.style.cursor = 'grabbing';
    });

    window.addEventListener('pointerup', e => {
      if (!this.isDragging) return;
      this.isDragging = false;
      el.style.cursor = 'grab';
      if (!this.dragMoved) {
        updatePointer(e);
        this._pick();
      }
    });

    el.addEventListener('pointermove', e => {
      if (!this.isDragging) return;
      const dx = e.clientX - this.prevPointer.x;
      const dy = e.clientY - this.prevPointer.y;
      if (Math.abs(dx) + Math.abs(dy) > 4) this.dragMoved = true;
      this.rotVelocity.x = dy * 0.005;
      this.rotVelocity.y = dx * 0.005;
      this.root.rotation.y += this.rotVelocity.y;
      this.root.rotation.x += this.rotVelocity.x;
      this.root.rotation.x = THREE.MathUtils.clamp(this.root.rotation.x, -1.2, 1.2);
      this.prevPointer = { x: e.clientX, y: e.clientY };
    });

    window.addEventListener('resize', () => this._resize());
  }

  _pick() {
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hits = this.raycaster.intersectObject(this.countryMesh);
    if (!hits.length) return;
    const faceIndex = hits[0].faceIndex;
    const id = this.faceCountryIds[faceIndex];
    if (id) {
      this.setSelectedCountry(id);
      this.onSelect(id);
    }
  }

  _resize() {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  _animate() {
    requestAnimationFrame(() => this._animate());
    if (!this.isDragging) {
      this.root.rotation.y += 0.0012 + this.rotVelocity.y * 0.3;
      this.rotVelocity.x *= 0.92;
      this.rotVelocity.y *= 0.92;
    }
    this.renderer.render(this.scene, this.camera);
  }
}

window.ProceduralGlobe = ProceduralGlobe;
