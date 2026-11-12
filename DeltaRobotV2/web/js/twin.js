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

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(40, 1, 1, 5000);
    this.camera.up.set(0, 0, 1);
    this.camera.position.set(300, -380, -40);
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(this.renderer.domElement);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.target.set(0, 0, -140);
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
    const on = !!state.magnet;
    this.magnet.material.color.setHex(on ? COLORS.magnetOn : COLORS.magnetOff);
    this.magnet.material.emissive.setHex(on ? 0x660000 : 0x000000);
    this.magnet.scale.setScalar(on ? 1.4 : 1);
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
