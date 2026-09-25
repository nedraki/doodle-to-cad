/* CadViewer — one persistent three.js scene for the result stage.
 * Auto-rotates until the user grabs it; free orbit afterwards.
 * replaceStl() swaps geometry in-place: camera, zoom and lighting NEVER reset,
 * which is what makes live slider edits feel real-time. */
class CadViewer {
  constructor(container) {
    this.container = container;
    this.token = 0;
    this._build();
  }

  _build() {
    const w = this.container.clientWidth || 640;
    const h = this.container.clientHeight || 400;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(w, h);
    this.container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(38, w / h, 0.1, 5000);
    this.camera.position.set(160, 130, 190);

    this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.autoRotate = true;
    this.controls.autoRotateSpeed = 1.6;
    // Stop the idle spin the moment the user takes over; never fight them.
    this.controls.addEventListener('start', () => { this.controls.autoRotate = false; this._syncRotateChip(false); });

    const key = new THREE.DirectionalLight(0xffffff, 0.95);
    key.position.set(1, 1.4, 1.2);
    this.scene.add(key, new THREE.HemisphereLight(0xbfd4ff, 0x2a2f3a, 0.55));
    const rim = new THREE.DirectionalLight(0x88aaff, 0.35);
    rim.position.set(-1.2, -0.4, -1);
    this.scene.add(rim);

    this.grid = new THREE.GridHelper(400, 20, 0x3a4a63, 0x222c3d);
    this.grid.position.y = 0;
    this.scene.add(this.grid);

    this.material = new THREE.MeshStandardMaterial({
      color: 0x4f83cc, metalness: 0.18, roughness: 0.55,
      polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1,
    });
    this.edgeMaterial = new THREE.LineBasicMaterial({ color: 0x1c2836, transparent: true, opacity: 0.35 });

    this.mesh = null;
    this.edges = null;
    this.loader = new THREE.STLLoader();

    this._resize = () => {
      const cw = this.container.clientWidth, ch = this.container.clientHeight;
      if (!cw || !ch) return;
      this.camera.aspect = cw / ch;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(cw, ch);
    };
    this._observer = new ResizeObserver(this._resize);
    this._observer.observe(this.container);

    const loop = () => {
      this._raf = requestAnimationFrame(loop);
      this.controls.update();
      this.renderer.render(this.scene, this.camera);
    };
    loop();
  }

  _syncRotateChip(on) {
    const chip = this.container.querySelector('[data-rotate]');
    if (chip) chip.classList.toggle('active', on);
  }

  setAutoRotate(on) {
    this.controls.autoRotate = on;
    this._syncRotateChip(on);
  }

  fitView() {
    if (!this.mesh) return;
    const box = new THREE.Box3().setFromObject(this.mesh);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const radius = Math.max(size.length() / 2, 1);
    this.controls.target.copy(center);
    const dist = radius / Math.sin((this.camera.fov * Math.PI) / 360);
    const dir = this.camera.position.clone().sub(this.controls.target).normalize();
    this.camera.position.copy(center.clone().add(dir.multiplyScalar(dist * 1.15)));
    this.camera.near = Math.max(dist / 1000, 0.05);
    this.camera.far = dist * 20;
    this.camera.updateProjectionMatrix();
    this.controls.update();
  }

  /* First load of a fresh generation: frame the part, restart the idle spin. */
  showStl(url) {
    return this._load(url, true);
  }

  /* Live parameter edit: swap geometry only, camera stays exactly where it is. */
  replaceStl(url) {
    return this._load(url, false);
  }

  _load(url, reframe) {
    const mine = ++this.token;
    return new Promise((resolve, reject) => {
      this.loader.load(url, (geo) => {
        if (mine !== this.token) return resolve(false); // superseded by a newer load
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
        if (reframe) {
          this.fitView();
          this.setAutoRotate(true);
        }
        resolve(true);
      }, undefined, (err) => reject(err));
    });
  }

  dispose() {
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
