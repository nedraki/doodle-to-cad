/* CadViewer — one persistent three.js scene for the result stage.
 * Uses the CAD Z-up frame and starts in the recorded drawing direction.
 * replaceStl() swaps geometry in-place: camera, zoom and lighting NEVER reset,
 * which is what makes live slider edits feel real-time. */
class CadViewer {
  constructor(container) {
    this.container = container;
    this.token = 0;
    this._build();
  }

  _build() {
    this.viewport = document.createElement('div');
    this.viewport.className = 'viewer-viewport';
    this.container.querySelector('.viewer-tools').insertAdjacentElement('afterend', this.viewport);
    const w = this.viewport.clientWidth || 640;
    const h = this.viewport.clientHeight || 400;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(w, h);
    this.viewport.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(38, w / h, 0.1, 5000);
    this.camera.up.set(0, 0, 1);
    this.camera.position.set(160, -190, 130);
    this.primaryView = 'front';
    this.fitted = true;

    this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.autoRotate = false;
    this.controls.autoRotateSpeed = 1.6;
    // Stop the idle spin the moment the user takes over; never fight them.
    this.controls.addEventListener('start', () => {
      this.setAutoRotate(false);
      this.fitted = false;
      this._syncViewChip(null);
    });

    const key = new THREE.DirectionalLight(0xffffff, 0.95);
    key.position.set(1, -1.4, 1.2);
    this.scene.add(key, new THREE.HemisphereLight(0xbfd4ff, 0x2a2f3a, 0.55));
    const rim = new THREE.DirectionalLight(0x88aaff, 0.35);
    rim.position.set(-1.2, -0.4, -1);
    this.scene.add(rim);

    this.grid = new THREE.GridHelper(400, 20, 0x3a4a63, 0x222c3d);
    this.grid.rotation.x = Math.PI / 2;
    this.grid.position.z = -0.02;
    this.scene.add(this.grid);

    this.material = new THREE.MeshStandardMaterial({
      color: 0x4f83cc, metalness: 0.18, roughness: 0.55,
      polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1,
    });
    this.edgeMaterial = new THREE.LineBasicMaterial({ color: 0x1c2836, transparent: true, opacity: 0.35 });

    this.featureParams = [];
    this.featureOverlay = new THREE.Group();
    this.scene.add(this.featureOverlay);
    this.featureCaption = document.createElement('div');
    this.featureCaption.className = 'feature-caption';
    this.featureCaption.hidden = true;
    this.viewport.appendChild(this.featureCaption);
    this.mesh = null;
    this.edges = null;
    this.loader = new THREE.STLLoader();

    this._resize = () => {
      const cw = this.viewport.clientWidth, ch = this.viewport.clientHeight;
      if (!cw || !ch) return;
      this.camera.aspect = cw / ch;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(cw, ch);
      if (this.fitted) this.fitView();
    };
    this._observer = new ResizeObserver(this._resize);
    this._observer.observe(this.viewport);

    const loop = () => {
      this._raf = requestAnimationFrame(loop);
      this.controls.update();
      this.renderer.render(this.scene, this.camera);
    };
    loop();
  }

  _syncRotateChip(on) {
    const chip = this.container.querySelector('[data-rotate]');
    if (chip) {
      chip.classList.toggle('active', on);
      chip.setAttribute('aria-pressed', String(on));
    }
  }

  setAutoRotate(on) {
    this.controls.autoRotate = on;
    this._syncRotateChip(on);
    if (on) {
      this._syncViewChip(null);
      this.fitView();
    }
  }

  _syncViewChip(name) {
    this.container.querySelectorAll('[data-camera-view]').forEach(button => {
      const active = button.dataset.cameraView === name;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
  }

  setView(name) {
    const direction = name === 'drawing' ? this.primaryView : name;
    // Position relative to the target. Top/bottom retain +X screen-right;
    // a tiny Y offset avoids the Z-up orbit pole singularity.
    const directions = {
      front: [0, -1, 0], rear: [0, 1, 0],
      right: [1, 0, 0], left: [-1, 0, 0],
      top: [0, -0.00001, 1], bottom: [0, 0.00001, -1],
      isometric: [1, -1, 0.8],
    };
    if (!directions[direction] || !this.mesh) return;
    this.setAutoRotate(false);
    // Flush pending drag damping before applying an explicit camera preset.
    this.controls.enableDamping = false;
    this.controls.update();
    this.controls.enableDamping = true;
    this.camera.position.copy(this.controls.target).add(new THREE.Vector3(...directions[direction]));
    this.camera.lookAt(this.controls.target);
    this.fitView();
    this._syncViewChip(name);
  }

  fitView() {
    if (!this.mesh) return;
    const box = new THREE.Box3().setFromObject(this.mesh);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const dir = this.camera.position.clone().sub(this.controls.target).normalize();
    this.controls.target.copy(center);
    this.camera.position.copy(center).add(dir);
    this.camera.lookAt(center);
    const right = new THREE.Vector3(1, 0, 0).applyQuaternion(this.camera.quaternion);
    const up = new THREE.Vector3(0, 1, 0).applyQuaternion(this.camera.quaternion);
    const tanY = Math.tan(this.camera.fov * Math.PI / 360);
    const tanX = tanY * this.camera.aspect;
    let dist = 1;
    // Fit all eight corners in both dimensions, including perspective depth.
    for (const x of [box.min.x, box.max.x])
      for (const y of [box.min.y, box.max.y])
        for (const z of [box.min.z, box.max.z]) {
          const corner = new THREE.Vector3(x, y, z).sub(center);
          dist = Math.max(dist, corner.dot(dir) + 1.15 * Math.max(
            Math.abs(corner.dot(right)) / tanX, Math.abs(corner.dot(up)) / tanY));
        }
    // Reserve space for every angle during automatic orbit, including long parts.
    if (this.controls.autoRotate) {
      dist = Math.max(dist, 1.1 * size.length() / 2 / Math.sin(Math.atan(Math.min(tanX, tanY))));
    }
    this.camera.position.copy(center).addScaledVector(dir, dist);
    this.camera.near = Math.max(dist / 1000, 0.05);
    this.camera.far = Math.max(dist * 20, size.length() * 20, 1000);
    this.camera.updateProjectionMatrix();
    this.controls.update();
    this.fitted = true;
  }

  /* Start in the saved drawing view; orbit is an explicit user action. */
  showStl(url, primaryView = 'front') {
    this.primaryView = ['front', 'rear', 'top', 'bottom', 'right', 'left'].includes(primaryView) ? primaryView : 'front';
    return this._load(url, true);
  }

  /* Live parameter edit: swap geometry only, camera stays exactly where it is. */
  replaceStl(url, params = [], isCurrent = () => true) {
    return this._load(url, false, params, isCurrent);
  }

  _load(url, reframe, params = [], isCurrent = () => true) {
    const mine = ++this.token;
    return new Promise((resolve, reject) => {
      this.loader.load(url, (geo) => {
        if (mine !== this.token || !isCurrent()) { geo.dispose(); return resolve(false); }
        geo.computeVertexNormals();
        if (this.mesh) {
          this.scene.remove(this.mesh);
          this.mesh.geometry.dispose();
          if (this.edges) { this.scene.remove(this.edges); this.edges.geometry.dispose(); this.edges = null; }
        }
        this.mesh = new THREE.Mesh(geo, this.material);
        this.scene.add(this.mesh);
        // Thin outline on top of the surface makes small features readable.
        const lines = new THREE.EdgesGeometry(geo, 30);
        this.edges = new THREE.LineSegments(lines, this.edgeMaterial);
        this.scene.add(this.edges);
        this.setFeatureParams(params);
        if (reframe) {
          this.setView('drawing');
        }
        resolve(true);
      }, undefined, (err) => reject(err));
    });
  }

  setFeatureParams(params) {
    this.featureParams = params;
    this.highlightParameter(this.activeParameter);
  }

  highlightParameter(name) {
    this.activeParameter = name;
    for (const child of [...this.featureOverlay.children]) {
      this.featureOverlay.remove(child);
      child.traverse(object => { object.geometry?.dispose(); object.material?.dispose(); });
    }
    this.featureCaption.hidden = !name;
    if (!name) return;
    const feature = this.featureParams.find(p => p.name === name)?.feature;
    this.featureCaption.textContent = 'Geometry indication unavailable for this parameter';
    if (!feature || !this.mesh) return;
    const color = 0xfbbf24;
    const box = new THREE.Box3().setFromObject(this.mesh);
    if (feature.kind === 'dimension') {
      const axis = feature.axis;
      if (!['x', 'y', 'z'].includes(axis)) return;
      const size = box.getSize(new THREE.Vector3());
      const margin = Math.max(size.length() * 0.06, 1);
      const start = box.min.clone().addScalar(-margin);
      const end = start.clone();
      start[axis] = box.min[axis]; end[axis] = box.max[axis];
      const length = end.distanceTo(start);
      if (!length) return;
      const direction = end.clone().sub(start).normalize();
      for (const [origin, dir] of [[start, direction], [end, direction.clone().negate()]]) {
        const arrow = new THREE.ArrowHelper(dir, origin, length, color, Math.min(margin, length / 4), Math.min(margin / 2, length / 8));
        arrow.traverse(object => { if(object.material) {object.material.depthTest=false;object.renderOrder=10;} });
        this.featureOverlay.add(arrow);
      }
      this.featureCaption.textContent = `${feature.label}: ${length.toFixed(2)} mm · dimension arrows`;
    } else if (feature.kind === 'region') {
      const region = new THREE.Box3(new THREE.Vector3(...feature.min), new THREE.Vector3(...feature.max));
      const outline = new THREE.Box3Helper(region, color);
      outline.material.depthTest = false; outline.renderOrder = 10;
      this.featureOverlay.add(outline);
      this.featureCaption.textContent = `${feature.label} · outlined feature region`;
    }
  }

  dispose() {
    this.highlightParameter(null);
    cancelAnimationFrame(this._raf);
    this._observer.disconnect();
    this.controls.dispose();
    this.renderer.dispose();
    this.container.innerHTML = '';
  }
}
/* `class` declarations are lexical globals — NOT window properties.
   app.js guards on window.CadViewer, so publish it or the 3D stage never mounts. */
window.CadViewer = CadViewer;
