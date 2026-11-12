// Delta Robotics deneyim arayüzü (F6): üyeliksiz tek sayfa. Ziyaretçi anonim simülasyon oturumu
// alır; dijital ikiz telemetriyle pozlanır. Otomatik mod: robot kendi kendine tic-tac-toe oynar.
// Manuel mod: eklem kaydırıcıları (FK önizleme) ve XYZ girişleri (IK önizleme).
import { applyI18n, has, loadCatalog, t } from "./i18n.js";
import { api, createSession, onSession, wsUrl } from "./api.js";

const $ = (id) => document.getElementById(id);

const STATE_KEYS = {
  IDLE: "robot.state.idle",
  RUNNING: "robot.state.running",
  HOLDING: "robot.state.holding",
  TORQUE_OFF: "robot.state.torque_off",
  FAULT: "robot.state.fault",
  ESTOP: "robot.state.estop",
  DISCONNECTED: "robot.state.disconnected",
};
const AUTO_KEYS = {
  idle: "web.auto.status.idle",
  playing: "web.auto.status.playing",
  finished: "web.auto.status.finished",
  stopped: "web.auto.status.stopped",
  error: "web.auto.status.error",
};
const BOARD_POLL_MS = 250; // ~4 Hz
const PREVIEW_DELAY_MS = 150;
const AXES = ["x", "y", "z"];

let robotInfo = null;
let twin = null;
let lastState = null;
let lastBoard = null;
let autoPlaying = false;
let lastAutoStatus = null;

// --- Yardımcılar -------------------------------------------------------------------------------

const fmt = (v, d = 1) => (typeof v === "number" && isFinite(v) ? v.toFixed(d) : "—");
const fmtVec = (a, d = 1) => (Array.isArray(a) ? a.map((v) => fmt(v, d)).join(", ") : "—");

// Hücre adı: sütun A–C (−X → +X), satır 1–3 (+Y → −Y); idx = satır * 3 + sütun (docs/api.md).
export const cellName = (i) => "ABC"[i % 3] + (Math.floor(i / 3) + 1);

function errorText(e) {
  if (e?.status === 0) return t("web.error.network");
  if (e?.status === 401) return t("web.error.unauthorized");
  if (e?.status === 409) return t("web.error.busy", { message: e.message });
  if (e?.status === 429) return t("web.exp.rate_limited");
  if (e?.status === 503 && e.code === "capacity") return t("web.exp.capacity");
  return e?.body?.message || t("web.error.http", { status: e?.status ?? "?" });
}

// Ret metni: gereksinim kodu + katalogdaki kısa açıklama + sunucunun ayrıntısı.
function rejectText(requirement, reason) {
  const req = requirement || "—";
  const key = `web.req.${String(req).toLowerCase()}`;
  const detail = String(reason || "").replace(new RegExp(`^${req}:\\s*`), "");
  return t("web.req.format", { requirement: req, title: has(key) ? t(key) : "", detail });
}

function setResult(el, kind, text) {
  el.dataset.kind = kind;
  el.textContent = text;
}

function showNotice(text) {
  const n = $("notice");
  n.textContent = text || "";
  n.hidden = !text;
}

// --- Oturum ve başlangıç ----------------------------------------------------------------------

let sessionRetry = null;

async function openSession() {
  clearTimeout(sessionRetry);
  try {
    await createSession();
    showNotice("");
    return true;
  } catch (e) {
    const wait = e.status === 429 ? 15 : 10;
    showNotice(t("web.exp.session_retry", { message: errorText(e), seconds: wait }));
    sessionRetry = setTimeout(start, wait * 1000);
    return false;
  }
}

async function start() {
  if (!(await openSession())) return;
  try {
    robotInfo = await api.robot();
  } catch (e) {
    showNotice(errorText(e));
    sessionRetry = setTimeout(start, 10000);
    return;
  }
  initManualLimits();
  telemetry.open();
  startBoardPolling();
  await initTwin();
}

// Yeni oturum (ör. boşta zaman aşımından sonra): telemetri yeni belirteçle yeniden bağlanır.
onSession(() => {
  if (telemetry.wanted) telemetry.open();
});

async function initTwin() {
  if (twin) return;
  try {
    const { Twin } = await import("./twin.js");
    twin = new Twin($("twin"), robotInfo);
    $("twin-msg").hidden = true;
    if (lastState) twin.update(lastState);
    if (lastBoard) twin.updateBoard(lastBoard);
  } catch (e) {
    console.error(e);
    $("twin-msg").textContent = t("web.twin.load_failed");
  }
}

// Test ve hata ayıklama için salt okunur kanca: ikizin sahnedeki pozu.
Object.defineProperty(window, "__twinPose", {
  get: () => (twin ? twin.pose() : null),
  configurable: true,
});

// --- Telemetri ----------------------------------------------------------------------------------

const telemetry = {
  ws: null,
  retry: 1000,
  timer: null,
  wanted: false,
  open() {
    this.wanted = true;
    this.close(true);
    const ws = new WebSocket(wsUrl("/ws/telemetry"));
    this.ws = ws;
    ws.onopen = () => {
      this.retry = 1000;
    };
    ws.onmessage = (m) => {
      let msg;
      try {
        msg = JSON.parse(m.data);
      } catch {
        return;
      }
      if (msg.type === "state") renderState(msg);
      else if (msg.type === "event") renderEvent(msg);
    };
    ws.onclose = () => {
      if (this.ws !== ws) return;
      this.ws = null;
      renderDisconnected();
      if (this.wanted) {
        this.timer = setTimeout(() => this.reconnect(), this.retry);
        this.retry = Math.min(this.retry * 2, 10000);
      }
    };
  },
  // WS 401 göremez: önce REST ile oturum doğrulanır (401 ise yeni oturum açılır, onSession açar).
  async reconnect() {
    try {
      await api.state();
    } catch {
      // ağ yoksa yine de denenir; sıradaki kapanışta geri çekilme sürer
    }
    if (this.wanted && !this.ws) this.open();
  },
  close(keepWanted = false) {
    if (!keepWanted) this.wanted = false;
    clearTimeout(this.timer);
    if (this.ws) {
      const ws = this.ws;
      this.ws = null;
      ws.close();
    }
  },
};

function renderBadge(state) {
  const b = $("state-badge");
  b.dataset.state = state;
  b.textContent = t(STATE_KEYS[state] || "robot.state.unknown");
}

function renderState(s) {
  lastState = s;
  renderBadge(s.state);
  $("tele-angles").textContent = fmtVec(s.angles_deg) + " °";
  $("tele-pos").textContent = Array.isArray(s.position_mm)
    ? fmtVec(s.position_mm) + " mm"
    : t("web.telemetry.no_solution");
  const mb = $("magnet-badge");
  mb.dataset.on = String(!!s.magnet);
  mb.textContent = s.magnet ? t("web.magnet.on") : t("web.magnet.off");
  $("magnet-toggle").textContent = s.magnet ? t("web.jog.magnet_off") : t("web.jog.magnet_on");
  $("magnet-toggle").setAttribute("aria-pressed", String(!!s.magnet));
  $("torque-on").disabled = !["HOLDING", "TORQUE_OFF"].includes(s.state) || autoPlaying;
  if (twin) {
    twin.setStale(s.state === "DISCONNECTED" || !s.edge_connected);
    twin.update(s);
  }
  manual.follow(s);
}

function renderDisconnected() {
  renderBadge("DISCONNECTED");
  if (twin) twin.setStale(true);
}

function renderEvent(ev) {
  if (ev.accepted) return; // kabuller sık; yalnız retler gösterilir
  const el = $("tele-event");
  const time = new Date().toLocaleTimeString(document.documentElement.lang || "tr");
  el.dataset.kind = "error";
  el.textContent = t("web.exp.event_rejected", {
    time,
    text: rejectText(ev.requirement, ev.reason),
  });
}

// --- Tabla ve otomatik mod ---------------------------------------------------------------------

let boardTimer = null;
let boardBusy = false;

async function refreshBoard() {
  if (boardBusy || document.hidden) return;
  boardBusy = true;
  try {
    const b = await api.board();
    if (b) {
      lastBoard = b;
      if (twin) twin.updateBoard(b);
      renderGame(b);
    }
  } catch (e) {
    if (e.status === 429) return;
    setResult($("auto-result"), "error", t("web.board.unavailable"));
  } finally {
    boardBusy = false;
  }
}

function startBoardPolling() {
  clearInterval(boardTimer);
  refreshBoard();
  boardTimer = setInterval(refreshBoard, BOARD_POLL_MS);
}

function buildBoardDiagram() {
  const el = $("board-diagram");
  el.textContent = "";
  const add = (cls, text = "") => {
    const d = document.createElement("div");
    d.className = cls;
    d.textContent = text;
    el.appendChild(d);
    return d;
  };
  add("corner");
  for (const c of "ABC") add("head", c);
  for (let r = 0; r < 3; r++) {
    add("head", String(r + 1));
    for (let c = 0; c < 3; c++) {
      const cell = add("cell");
      cell.dataset.idx = String(r * 3 + c);
      cell.dataset.kind = ".";
    }
  }
}

function renderGame(b) {
  const a = b.auto || { status: "idle", turn: "X", moves: [] };
  const changed = lastAutoStatus !== null && lastAutoStatus !== a.status;
  lastAutoStatus = a.status;
  autoPlaying = a.status === "playing";
  document.body.dataset.auto = a.status;
  const st = $("auto-status");
  st.dataset.status = a.status;
  st.textContent = t(AUTO_KEYS[a.status] || "web.auto.status.idle");
  $("auto-turn").textContent = autoPlaying ? pieceName(a.turn) : "—";
  const w = a.winner ?? b.winner ?? null;
  const moves = a.moves || [];
  $("auto-winner").textContent = w
    ? t("web.auto.winner_is", { piece: pieceName(w) })
    : a.status === "finished"
      ? t("web.auto.draw", { n: moves.length })
      : "—";
  $("auto-start").disabled = autoPlaying;
  $("auto-stop").disabled = !autoPlaying;
  $("auto-reset").disabled = autoPlaying;
  const res = $("auto-result");
  if (a.status === "error")
    setResult(res, "error", t("web.auto.error", { reason: a.reason || "" }));
  else if (changed && a.status !== "playing") setResult(res, "", ""); // eski "başladı" iletisi

  // Diyagram
  const last = moves[moves.length - 1];
  const cells = b.cells || ".........";
  const labels = [];
  for (const el of $("board-diagram").querySelectorAll(".cell")) {
    const i = Number(el.dataset.idx);
    const k = cells[i] || ".";
    el.dataset.kind = k;
    el.textContent = k === "." ? "" : k;
    el.classList.toggle("from", !!last && last.from === i);
    el.classList.toggle("to", !!last && last.to === i);
    labels.push(`${cellName(i)} ${k === "." ? t("web.auto.empty") : k}`);
  }
  $("board-diagram").setAttribute(
    "aria-label",
    t("web.auto.board_aria", { cells: labels.join(", ") }),
  );

  // Hamle listesi (yalnız değişince yeniden çizilir)
  const body = $("moves-body");
  if (body.childElementCount !== moves.length) {
    body.textContent = "";
    for (const m of moves) {
      const tr = document.createElement("tr");
      tr.dataset.kind = m.kind;
      for (const text of [String(m.n), m.kind, `${cellName(m.from)}→${cellName(m.to)}`]) {
        const td = document.createElement("td");
        td.textContent = text;
        tr.appendChild(td);
      }
      body.appendChild(tr);
    }
    $("moves-empty").hidden = moves.length > 0;
    const scroll = body.closest(".moves-scroll");
    scroll.scrollTop = scroll.scrollHeight;
  }
  manual.setLocked(autoPlaying);
}

const pieceName = (k) => t(k === "X" ? "web.auto.piece_x" : "web.auto.piece_o");

function initAuto() {
  buildBoardDiagram();
  const res = $("auto-result");
  const run = async (fn, okKey) => {
    try {
      await fn();
      setResult(res, "ok", t(okKey));
    } catch (e) {
      setResult(res, "error", errorText(e));
    }
    refreshBoard();
  };
  $("auto-start").addEventListener("click", () => run(api.autoStart, "web.auto.started"));
  $("auto-stop").addEventListener("click", () => run(api.autoStop, "web.auto.stopped"));
  $("auto-reset").addEventListener("click", () => run(api.resetBoard, "web.auto.reset_ok"));
}

// --- Manuel mod ---------------------------------------------------------------------------------

// İki giriş grubu (eklem, kartezyen). Kullanıcı bir grubu düzenleyince o grup "kirli" olur ve
// telemetriyi izlemeyi bırakır; hareket bitince ya da "Şu anki pozu al" ile yeniden izler.
const manual = {
  dirty: { joints: false, cart: false },
  seq: { joints: 0, cart: 0 },
  timers: {},
  locked: false,

  values(group) {
    const ids =
      group === "joints"
        ? [0, 1, 2].map((i) => `joint-num-${i}`)
        : AXES.map((k) => `cart-num-${k}`);
    return ids.map((id) => Number($(id).value));
  },

  setValues(group, vals) {
    vals.forEach((v, i) => {
      const k = group === "joints" ? i : AXES[i];
      const num = $(`${group === "joints" ? "joint" : "cart"}-num-${k}`);
      const rng = $(`${group === "joints" ? "joint" : "cart"}-range-${k}`);
      const s = (Math.round(v * 10) / 10).toString();
      if (document.activeElement !== num && num.value !== s) num.value = s;
      if (document.activeElement !== rng && rng.value !== s) rng.value = s;
    });
  },

  follow(s) {
    if (!robotInfo) return;
    if (!this.dirty.joints && Array.isArray(s.angles_deg)) {
      this.setValues("joints", s.angles_deg);
      setResult($("fk-preview"), "info", t("web.manual.live_pos", { pos: fmtVec(s.position_mm) }));
    }
    if (!this.dirty.cart && Array.isArray(s.position_mm)) {
      this.setValues("cart", s.position_mm);
      setResult(
        $("ik-preview"),
        "info",
        t("web.manual.live_angles", { angles: fmtVec(s.angles_deg) }),
      );
    }
  },

  edited(group) {
    this.dirty[group] = true;
    clearTimeout(this.timers[group]);
    this.timers[group] = setTimeout(() => this.preview(group), PREVIEW_DELAY_MS);
  },

  release() {
    this.dirty.joints = this.dirty.cart = false;
    if (lastState) this.follow(lastState);
  },

  async preview(group) {
    const vals = this.values(group);
    const out = $(group === "joints" ? "fk-preview" : "ik-preview");
    if (!vals.every(Number.isFinite)) {
      setResult(out, "error", t("web.manual.invalid"));
      return null;
    }
    const n = ++this.seq[group];
    try {
      const r = group === "joints" ? await api.fk(vals) : await api.ik(...vals);
      if (n !== this.seq[group] || !this.dirty[group]) return r; // eski yanıt
      if (group === "joints") {
        const pos = Array.isArray(r.position_mm) ? fmtVec(r.position_mm) : "—";
        if (r.ok) setResult(out, "ok", t("web.manual.fk_ok", { pos }));
        else
          setResult(
            out,
            "error",
            t("web.manual.fk_bad", { pos, text: rejectText(r.requirement, r.reason) }),
          );
      } else {
        const angles = Array.isArray(r.angles_deg) ? fmtVec(r.angles_deg) : "—";
        if (r.ok) setResult(out, "ok", t("web.manual.ik_ok", { angles }));
        else
          setResult(
            out,
            "error",
            t("web.manual.ik_bad", { angles, text: rejectText(r.requirement, r.reason) }),
          );
      }
      return r;
    } catch (e) {
      if (n === this.seq[group]) setResult(out, "error", errorText(e));
      return null;
    }
  },

  async go(group) {
    const out = $("manual-result");
    const vals = this.values(group);
    if (!vals.every(Number.isFinite)) {
      setResult(out, "error", t("web.manual.invalid"));
      return;
    }
    clearTimeout(this.timers[group]);
    setResult(
      out,
      "info",
      t(group === "joints" ? "web.manual.moving_joints" : "web.manual.moving_cart", {
        v: fmtVec(vals),
      }),
    );
    try {
      const r = group === "joints" ? await api.moveJoints(vals) : await api.move(...vals);
      if (!r.accepted) {
        setResult(
          out,
          "error",
          t("web.move.rejected_text", { text: rejectText(r.requirement, r.reason) }),
        );
        return;
      }
      if (r.done === false)
        setResult(out, "warn", t("web.move.not_done", { reason: r.reason || "" }));
      else setResult(out, "ok", t("web.move.done", { pos: fmtVec(r.position_mm) }));
      this.release();
    } catch (e) {
      setResult(out, "error", errorText(e));
    }
  },

  setLocked(locked) {
    if (this.locked === locked) return;
    this.locked = locked;
    for (const id of ["joints-go", "cart-go", "cart-home", "magnet-toggle"])
      $(id).disabled = locked;
    $("manual-result").dataset.kind = locked ? "warn" : "";
    $("manual-result").textContent = locked ? t("web.manual.locked") : "";
  },
};

function makeRow(host, { id, label, min, max, step, unit, onInput }) {
  const row = document.createElement("div");
  row.className = "slider-row";
  const lab = document.createElement("label");
  lab.htmlFor = `${id.replace("{}", "num")}`;
  lab.textContent = label;
  const rng = document.createElement("input");
  Object.assign(rng, { type: "range", id: id.replace("{}", "range"), min, max, step });
  rng.setAttribute("aria-label", label);
  const num = document.createElement("input");
  Object.assign(num, { type: "number", id: id.replace("{}", "num"), step, inputMode: "decimal" });
  const u = document.createElement("span");
  u.className = "muted unit";
  u.textContent = unit;
  // Kaydırıcı sürüklerken sayı alanı izler; bırakınca (change) önizleme.
  rng.addEventListener("input", () => {
    num.value = rng.value;
    onInput(false);
  });
  rng.addEventListener("change", () => onInput(true));
  num.addEventListener("input", () => {
    if (num.value !== "" && Number.isFinite(Number(num.value))) rng.value = num.value;
    onInput(true);
  });
  num.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") onInput("go");
  });
  row.append(lab, rng, num, u);
  host.appendChild(row);
}

function initManualLimits() {
  if ($("joint-rows").childElementCount) return;
  const lim = robotInfo.limits;
  const ws = robotInfo.workspace;
  const handler = (group) => (mode) => {
    if (mode === "go") return manual.go(group);
    manual.dirty[group] = true;
    if (mode) manual.edited(group);
  };
  for (let i = 0; i < 3; i++) {
    makeRow($("joint-rows"), {
      id: `joint-{}-${i}`,
      label: t("web.manual.joint_label", { n: i + 1 }),
      min: lim.motor_min_deg,
      max: lim.motor_max_deg,
      step: 0.5,
      unit: "°",
      onInput: handler("joints"),
    });
  }
  const rad = ws.cylinder_diameter_mm / 2;
  const ranges = { x: [-rad, rad], y: [-rad, rad], z: [ws.z_bottom_mm, ws.z_top_mm] };
  for (const k of AXES) {
    makeRow($("cart-rows"), {
      id: `cart-{}-${k}`,
      label: k.toUpperCase(),
      min: ranges[k][0],
      max: ranges[k][1],
      step: 0.5,
      unit: "mm",
      onInput: handler("cart"),
    });
  }
  $("joints-hint-range").textContent = t("web.manual.joint_range", {
    min: lim.motor_min_deg,
    max: lim.motor_max_deg,
  });
  $("cart-range").textContent = t("web.jog.range", {
    d: ws.cylinder_diameter_mm,
    top: ws.z_top_mm,
    bottom: ws.z_bottom_mm,
  });
  manual.setValues("joints", lastState?.angles_deg || [0, 0, 0]);
  manual.setValues("cart", lastState?.position_mm || robotInfo.home_mm || [0, 0, -200]);
}

function initManual() {
  $("joints-go").addEventListener("click", () => manual.go("joints"));
  $("cart-go").addEventListener("click", () => manual.go("cart"));
  $("joints-sync").addEventListener("click", () => manual.release());
  $("cart-sync").addEventListener("click", () => manual.release());
  $("cart-home").addEventListener("click", () => {
    const home = robotInfo?.home_mm;
    if (!home) return;
    manual.dirty.cart = true;
    manual.setValues("cart", home);
    manual.go("cart");
  });
  $("magnet-toggle").addEventListener("click", async () => {
    try {
      const r = await api.magnet(!lastState?.magnet);
      setResult($("manual-result"), "ok", r.magnet ? t("web.magnet.on") : t("web.magnet.off"));
    } catch (e) {
      setResult($("manual-result"), "error", errorText(e));
    }
  });
  $("torque-on").addEventListener("click", async () => {
    try {
      await api.torque(true);
      setResult($("manual-result"), "ok", t("web.manual.ready_ok"));
    } catch (e) {
      setResult($("manual-result"), "error", errorText(e));
    }
  });
}

// Dur: her zaman etkin; otomatik oyunu da keser (sözleşme).
function initStop() {
  for (const b of document.querySelectorAll('[data-action="stop"]')) {
    b.addEventListener("click", async () => {
      const out = $("panel-manual").hidden ? $("auto-result") : $("manual-result");
      try {
        await api.stop();
        setResult(out, "warn", t("web.manual.stopped"));
      } catch (e) {
        setResult(out, "error", errorText(e));
      }
      refreshBoard();
    });
  }
}

// --- Sekmeler -----------------------------------------------------------------------------------

const TABS = [
  { tab: "tab-auto", panel: "panel-auto", hash: "#otomatik" },
  { tab: "tab-manual", panel: "panel-manual", hash: "#manuel" },
];

function selectTab(idx, focus = false) {
  TABS.forEach((x, i) => {
    const on = i === idx;
    const tab = $(x.tab);
    tab.setAttribute("aria-selected", String(on));
    tab.tabIndex = on ? 0 : -1;
    $(x.panel).hidden = !on;
    if (on && focus) tab.focus();
  });
  document.body.dataset.mode = idx === 0 ? "auto" : "manual";
  if (location.hash !== TABS[idx].hash) history.replaceState(null, "", TABS[idx].hash);
}

function initTabs() {
  TABS.forEach((x, i) => {
    $(x.tab).addEventListener("click", () => selectTab(i));
    $(x.tab).addEventListener("keydown", (ev) => {
      const n = { ArrowRight: 1, ArrowLeft: -1, Home: -i, End: TABS.length - 1 - i }[ev.key];
      if (n === undefined) return;
      ev.preventDefault();
      selectTab((i + n + TABS.length) % TABS.length, true);
    });
  });
  const fromHash = () =>
    Math.max(
      0,
      TABS.findIndex((x) => x.hash === location.hash),
    );
  window.addEventListener("hashchange", () => selectTab(fromHash()));
  selectTab(fromHash());
}

// --- Başlangıç ----------------------------------------------------------------------------------

async function main() {
  const lang = new URLSearchParams(location.search).get("lang") === "en" ? "en" : "tr";
  document.documentElement.lang = lang;
  await loadCatalog(lang);
  document.title = t("app.title");
  applyI18n();
  renderDisconnected();
  $("magnet-badge").textContent = t("web.magnet.off");
  initTabs();
  initAuto();
  initManual();
  initStop();
  start();
}

main();
