// Dijital ikiz: CAD mesh'leri telemetrideki motor açıları ve P konumuyla pozlanır.
// Çerçeveler cad/README.md ve delta_server/frames.py ile aynıdır (robot çerçevesi, mm, +Z yukarı):
//   bicep_i        orijin A_i = R·u_i, dönme Rz(a_i)·Ry(θ_i)
//   forearm_i_a/b  orijin B_i ± s·t_i, X alt küreye (C_i ± s·t_i), Y = t_i'nin X'e dik bileşeni
//   platform       orijin P, dönmesiz
// Mesh yüklenemezse aynı yerel çerçevede basit bir şekil (kutu/çubuk/disk) gösterilir.
import * as THREE from "three";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const DEG = Math.PI / 180;
const MESH_URL = (name) => `/assets/meshes/${name}.stl`;

const COLORS = {
  base: 0x8a929b,
  bicep: 0xb9c4ce,
  forearm: 0x5f6b78,
  platform: 0xe0a040,
  magnetOff: 0x6b7280,
  magnetOn: 0xff3030,
};

export class Twin {
  constructor(container, robot) {
    const g = robot.geometry;
    this.g = {
      R: g.R,
      L1: g.L1,
      L2: g.L2,
      r: g.r,
      tool: g.tool_offset_mm,
      // Sözleşmede yok: varsa sunucudan, yoksa config/robot.yaml değerleri.
      angles: g.arm_angles_deg ?? [0, 120, 240],
      s: (g.rod_spacing_mm ?? 30) / 2,
    };
    this.container = container;
    this.links = {};
    this.lastState = null;
    this.updates = 0;

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(40, 1, 1, 5000);
    this.camera.up.set(0, 0, 1);
    this.camera.position.set(240, -410, -70);
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(this.renderer.domElement);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.target.set(0, 0, -180);
    this.controls.update();

    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x404050, 1.4));
    const sun = new THREE.DirectionalLight(0xffffff, 1.6);
    sun.position.set(300, -400, 600);
    this.scene.add(sun);

    this.buildStatic(robot);
    this.buildLinks();
    this.applyTheme();
    window
      .matchMedia("(prefers-color-scheme: dark)")
      .addEventListener("change", () => this.applyTheme());

    new ResizeObserver(() => this.resize()).observe(container);
    this.resize();
    this.renderer.setAnimationLoop(() => this.renderer.render(this.scene, this.camera));
  }

  // Zemin ızgarası, çalışma alanı silindiri, taban mesh'i
  buildStatic(robot) {
    const floorZ = -(robot.geometry.base_to_floor_mm ?? 240);
    this.grid = new THREE.GridHelper(400, 20);
    this.grid.rotation.x = Math.PI / 2;
    this.grid.position.z = floorZ;
    this.scene.add(this.grid);

    const ws = robot.workspace;
    const rad = ws.cylinder_diameter_mm / 2;
    const h = ws.z_top_mm - ws.z_bottom_mm;
    const cyl = new THREE.CylinderGeometry(rad, rad, h, 64, 1, true);
    cyl.rotateX(Math.PI / 2);
    const wsGroup = new THREE.Group();
    wsGroup.position.z = (ws.z_top_mm + ws.z_bottom_mm) / 2;
    wsGroup.add(
      new THREE.Mesh(
        cyl,
        new THREE.MeshBasicMaterial({
          color: 0x3b82f6,
          transparent: true,
          opacity: 0.07,
          side: THREE.DoubleSide,
          depthWrite: false,
        }),
      ),
    );
    wsGroup.add(
      new THREE.LineSegments(
        new THREE.EdgesGeometry(cyl),
        new THREE.LineBasicMaterial({ color: 0x3b82f6, transparent: true, opacity: 0.35 }),
      ),
    );
    this.scene.add(wsGroup);

    const base = this.makeLink("base", COLORS.base, null);
    base.matrixAutoUpdate = true;
    this.links.base = base;

    // Mıknatıs ucu göstergesi: P'nin tool_offset altında
    this.magnet = new THREE.Mesh(
      new THREE.SphereGeometry(4, 20, 12),
      new THREE.MeshStandardMaterial({ color: COLORS.magnetOff }),
    );
    this.scene.add(this.magnet);
  }

  buildLinks() {
    const { L1, L2, r } = this.g;
    for (let i = 1; i <= 3; i++) {
      const bicep = new THREE.Mesh(
        new THREE.BoxGeometry(L1, 4, 10).translate(L1 / 2, 0, 0),
        this.material(COLORS.bicep),
      );
      this.links[`bicep_${i}`] = this.makeLink(`bicep_${i}`, COLORS.bicep, bicep);
      for (const tag of ["a", "b"]) {
        const rod = new THREE.Mesh(
          new THREE.CylinderGeometry(2.5, 2.5, L2, 12)
            .rotateZ(-Math.PI / 2)
            .translate(L2 / 2, 0, 0),
          this.material(COLORS.forearm),
        );
        const name = `forearm_${i}_${tag}`;
        this.links[name] = this.makeLink(name, COLORS.forearm, rod);
      }
    }
    const disc = new THREE.Mesh(
      new THREE.CylinderGeometry(r, r, 5, 36).rotateX(Math.PI / 2),
      this.material(COLORS.platform),
    );
    this.links.platform = this.makeLink("platform", COLORS.platform, disc);
  }

  material(color) {
    return new THREE.MeshStandardMaterial({ color, metalness: 0.2, roughness: 0.6 });
  }

  // Bağ nesnesi: önce yer tutucu şekil, STL gelince onunla değiştirilir.
  makeLink(name, color, placeholder) {
    const obj = new THREE.Group();
    obj.matrixAutoUpdate = false;
    if (placeholder) obj.add(placeholder);
    this.scene.add(obj);
    new STLLoader().load(
      MESH_URL(name),
      (geom) => {
        obj.clear();
        obj.add(new THREE.Mesh(geom, this.material(color)));
        obj.userData.mesh = true;
      },
      undefined,
      () => {
        obj.userData.mesh = false;
      },
    );
    return obj;
  }

  applyTheme() {
    const css = getComputedStyle(document.documentElement);
    const bg = css.getPropertyValue("--twin-bg").trim() || "#eef1f4";
    this.scene.background = new THREE.Color(bg);
    const gridColor = new THREE.Color(css.getPropertyValue("--twin-grid").trim() || "#b0b8c0");
    for (const m of [].concat(this.grid.material)) m.color = gridColor;
  }

  resize() {
    const w = this.container.clientWidth || 1;
    const h = this.container.clientHeight || 1;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  // Telemetri durumu ile bağları pozlar.
  update(state) {
    this.lastState = state;
    const { R, L1, r, tool, angles, s } = this.g;
    const th = state.angles_deg;
    const P = state.position_mm;
    const solved = Array.isArray(P) && Array.isArray(th);
    for (let i = 0; i < 3; i++) {
      const a = angles[i] * DEG;
      const u = new THREE.Vector3(Math.cos(a), Math.sin(a), 0);
      const tv = new THREE.Vector3(-Math.sin(a), Math.cos(a), 0);
      const theta = (th?.[i] ?? 0) * DEG;
      const bicep = this.links[`bicep_${i + 1}`];
      bicep.matrix
        .makeRotationZ(a)
        .multiply(new THREE.Matrix4().makeRotationY(theta))
        .setPosition(u.clone().multiplyScalar(R));
      bicep.matrixWorldNeedsUpdate = true;

      const B = u
        .clone()
        .multiplyScalar(R + L1 * Math.cos(theta))
        .add(new THREE.Vector3(0, 0, -L1 * Math.sin(theta)));
      for (const [tag, sign] of [
        ["a", 1],
        ["b", -1],
      ]) {
        const fa = this.links[`forearm_${i + 1}_${tag}`];
        fa.visible = solved;
        if (!solved) continue;
        const C = new THREE.Vector3(...P).add(u.clone().multiplyScalar(r));
        const top = B.clone().add(tv.clone().multiplyScalar(sign * s));
        const bottom = C.add(tv.clone().multiplyScalar(sign * s));
        const x = bottom.sub(top).normalize();
        const y = tv
          .clone()
          .sub(x.clone().multiplyScalar(tv.dot(x)))
          .normalize();
        const z = new THREE.Vector3().crossVectors(x, y);
        fa.matrix.makeBasis(x, y, z).setPosition(top);
        fa.matrixWorldNeedsUpdate = true;
      }
    }
    const plat = this.links.platform;
    plat.visible = solved;
    this.magnet.visible = solved;
    if (solved) {
      plat.matrix.makeTranslation(P[0], P[1], P[2]);
      plat.matrixWorldNeedsUpdate = true;
      // Göstergenin üst ucu mıknatıs ucuna değer; mesh içinde kaybolmasın
      this.magnet.position.set(P[0], P[1], P[2] - tool - 4);
    }
    this.updates += 1;
    const on = !!state.magnet;
    this.magnet.material.color.setHex(on ? COLORS.magnetOn : COLORS.magnetOff);
    this.magnet.material.emissive.setHex(on ? 0x660000 : 0x000000);
    this.magnet.scale.setScalar(on ? 1.4 : 1);
  }

  // Tic-tac-toe tablası ve taşlar (F4.5): /board yanıtından. Tabla bir kez kurulur, taşlar her
  // çağrıda konumlanır (alt yüz merkezi -> silindir merkezi).
  updateBoard(board) {
    const g = board.geometry;
    if (!this.board) {
      const size = 3 * g.cell_mm;
      const thick = 4;
      this.board = new THREE.Group();
      const slab = new THREE.Mesh(
        new THREE.BoxGeometry(size, size, thick),
        new THREE.MeshStandardMaterial({ color: 0x33373f }),
      );
      slab.position.set(g.center_mm[0], g.center_mm[1], g.board_top_mm - thick / 2);
      this.board.add(slab);
      const pts = [];
      const half = size / 2;
      for (let n = 0; n <= 3; n++) {
        const d = -half + n * g.cell_mm;
        pts.push(-half, d, 0, half, d, 0, d, -half, 0, d, half, 0);
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
      const grid = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ color: 0xeeeeee }));
      grid.position.set(g.center_mm[0], g.center_mm[1], g.board_top_mm + 0.3);
      this.board.add(grid);
      // Hücre adları (A–C sütun −X→+X, 1–3 satır +Y→−Y): hamle listesindeki adlarla aynı
      const z = g.board_top_mm + 1;
      for (let n = 0; n < 3; n++) {
        const d = (n - 1) * g.cell_mm;
        this.board.add(this.label("ABC"[n], g.center_mm[0] + d, g.center_mm[1] + half + 9, z));
        this.board.add(this.label(String(n + 1), g.center_mm[0] - half - 9, g.center_mm[1] - d, z));
      }
      this.pieceMeshes = new Map();
      this.scene.add(this.board);
    }
    for (const p of board.pieces) {
      let m = this.pieceMeshes.get(p.id);
      if (!m) {
        m = new THREE.Mesh(
          new THREE.CylinderGeometry(
            g.piece_diameter_mm / 2,
            g.piece_diameter_mm / 2,
            g.piece_height_mm,
            28,
          ),
          new THREE.MeshStandardMaterial({ color: p.kind === "X" ? 0x1a73e6 : 0xf2cc1a }),
        );
        m.rotation.x = Math.PI / 2; // three.js silindiri Y ekseninde; robot çerçevesi +Z yukarı
        this.board.add(m);
        this.pieceMeshes.set(p.id, m);
      }
      m.position.set(p.pos_mm[0], p.pos_mm[1], p.pos_mm[2] + g.piece_height_mm / 2);
    }
  }

  // Küçük metin etiketi (tuval dokulu sprite)
  label(text, x, y, z) {
    const c = document.createElement("canvas");
    c.width = c.height = 64;
    const ctx = c.getContext("2d");
    ctx.fillStyle = "#e0a040";
    ctx.font = "bold 44px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, 32, 34);
    const sprite = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), depthWrite: false }),
    );
    sprite.scale.set(10, 10, 1);
    sprite.position.set(x, y, z);
    return sprite;
  }

  // Test ve hata ayıklama için salt okunur poz: sahnedeki bağ matrislerinden geri okunur.
  pose() {
    const thetas = [1, 2, 3].map((i) => {
      const e = this.links[`bicep_${i}`].matrix.elements; // sütun öncelikli; 1. sütun = kol ekseni
      return Math.round(Math.atan2(-e[2], Math.hypot(e[0], e[1])) * (1800 / Math.PI)) / 10;
    });
    const plat = this.links.platform;
    const pe = plat.matrix.elements;
    const s = this.lastState;
    return Object.freeze({
      angles_deg: thetas,
      position_mm: plat.visible
        ? [pe[12], pe[13], pe[14]].map((v) => Math.round(v * 10) / 10)
        : null,
      magnet: !!s?.magnet,
      state_angles_deg: s?.angles_deg ? [...s.angles_deg] : null,
      updates: this.updates,
      meshes: this.meshStatus(),
    });
  }

  // Bağlantı yoksa ikiz soluk gösterilir.
  setStale(stale) {
    this.renderer.domElement.style.opacity = stale ? "0.45" : "1";
  }

  meshStatus() {
    const vals = Object.values(this.links).map((o) => o.userData.mesh);
    return { loaded: vals.filter((v) => v === true).length, total: vals.length };
  }
}
