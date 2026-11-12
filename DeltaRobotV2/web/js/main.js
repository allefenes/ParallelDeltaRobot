// Delta Robotics tarayıcı arayüzü: giriş, kod editörü + iş konsolu, dijital ikiz, telemetri, elle sürme.
import { applyI18n, loadCatalog, t } from "./i18n.js";
import { api, getToken, setToken, wsUrl } from "./api.js";

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
const JOB_KEYS = {
  none: "web.job.status.none",
  queued: "web.job.status.queued",
  running: "web.job.status.running",
  done: "web.job.status.done",
  failed: "web.job.status.failed",
  timeout: "web.job.status.timeout",
  cancelled: "web.job.status.cancelled",
};
const JOB_FINAL = new Set(["done", "failed", "timeout", "cancelled"]);
const CONSOLE_MAX_LINES = 5000;

let robotInfo = null;
let twin = null;
let lastState = null;
let editor = null;

// --- Yardımcılar -------------------------------------------------------------------------------

function errorText(e) {
  if (e?.status === 0) return t("web.error.network");
  if (e?.status === 401) return t("web.error.unauthorized");
  if (e?.status === 409) return t("web.error.busy", { message: e.message });
  return e?.body?.message || t("web.error.http", { status: e?.status ?? "?" });
}

const fmt = (v, d = 1) => (typeof v === "number" && isFinite(v) ? v.toFixed(d) : "—");
const fmtVec = (a, d = 1) => (Array.isArray(a) ? a.map((v) => fmt(v, d)).join(", ") : "—");

function setResult(el, kind, text) {
  el.dataset.kind = kind;
  el.textContent = text;
}

// --- Giriş --------------------------------------------------------------------------------------

function initLogin() {
  $("token").value = getToken();
  $("login").addEventListener("submit", (ev) => {
    ev.preventDefault();
    setToken($("token").value);
    connectAll();
  });
  $("token-clear").addEventListener("click", () => {
    setToken("");
    $("token").value = "";
    telemetry.close();
    $("login-status").textContent = t("web.login.need_token");
  });
}

async function connectAll() {
  if (!getToken()) {
    $("login-status").textContent = t("web.login.need_token");
    return;
  }
  $("login-status").textContent = t("web.login.connecting");
  try {
    robotInfo = await api.robot();
    $("login-status").textContent = t("web.login.ok", { name: robotInfo.name });
    onRobotInfo();
  } catch (e) {
    $("login-status").textContent = errorText(e);
    return;
  }
  telemetry.open();
}

// --- Dijital ikiz -------------------------------------------------------------------------------

async function onRobotInfo() {
  const ws = robotInfo.workspace;
  const home = robotInfo.home_mm || [0, 0, -200];
  for (const [i, k] of ["x", "y", "z"].entries()) {
    const el = $(`jog-${k}`);
    if (el.value === "") el.value = home[i];
  }
  $("jog-range").textContent = t("web.jog.range", {
    d: ws.cylinder_diameter_mm,
    top: ws.z_top_mm,
    bottom: ws.z_bottom_mm,
  });
  if (twin) return;
  try {
    const { Twin } = await import("./twin.js");
    twin = new Twin($("twin"), robotInfo);
    $("twin-msg").hidden = true;
    if (lastState) twin.update(lastState);
    startBoardPolling();
  } catch (e) {
    console.error(e);
    $("twin-msg").textContent = t("web.twin.load_failed");
  }
}

// --- Tic-tac-toe tablası (F4.5) -----------------------------------------------------------------

let boardTimer = null;

async function refreshBoard() {
  try {
    const b = await api.board();
    const winner = b.winner ? t("web.board.winner", { kind: b.winner }) : t("web.board.no_winner");
    $("board-status").textContent = t("web.board.status", { cells: b.cells, winner });
    if (twin) twin.updateBoard(b);
  } catch (e) {
    $("board-status").textContent = t("web.board.unavailable");
  }
}

function startBoardPolling() {
  if (boardTimer) clearInterval(boardTimer);
  refreshBoard();
  boardTimer = setInterval(refreshBoard, 500);
}

$("btn-board-reset").addEventListener("click", async () => {
  try {
    await api.resetBoard();
  } catch (e) {
    $("board-status").textContent = e.message;
  }
  refreshBoard();
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
        this.timer = setTimeout(() => this.open(), this.retry);
        this.retry = Math.min(this.retry * 2, 10000);
      }
    };
  },
  close(keepWanted = false) {
    if (!keepWanted) this.wanted = false;
    clearTimeout(this.timer);
    if (this.ws) {
      const ws = this.ws;
      this.ws = null;
      ws.close();
    }
    if (!keepWanted) renderDisconnected();
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
  $("tele-edge").textContent = s.edge_connected
    ? t("web.telemetry.edge_ok")
    : t("web.telemetry.edge_lost");
  $("tele-edge").dataset.ok = String(!!s.edge_connected);
  $("tele-angles").textContent = fmtVec(s.angles_deg) + " °";
  $("tele-pos").textContent = Array.isArray(s.position_mm)
    ? fmtVec(s.position_mm) + " mm"
    : t("web.telemetry.no_solution");
  $("tele-magnet").textContent = s.magnet ? t("web.magnet.on") : t("web.magnet.off");
  $("tele-job").textContent = s.job_id || "—";
  for (let i = 0; i < 3; i++) {
    $(`temp-${i}`).textContent = fmt(s.temps_c?.[i], 0) + " °C";
    $(`load-${i}`).textContent = fmt(s.loads?.[i], 0);
    $(`volt-${i}`).textContent = fmt(s.voltages?.[i], 1) + " V";
  }
  const mb = $("magnet-badge");
  mb.dataset.on = String(!!s.magnet);
  mb.textContent = s.magnet ? t("web.magnet.on") : t("web.magnet.off");
  $("magnet-toggle").textContent = s.magnet ? t("web.jog.magnet_off") : t("web.jog.magnet_on");
  if (twin) {
    twin.setStale(s.state === "DISCONNECTED" || !s.edge_connected);
    twin.update(s);
  }
}

function renderDisconnected() {
  renderBadge("DISCONNECTED");
  $("tele-edge").textContent = t("web.telemetry.no_stream");
  $("tele-edge").dataset.ok = "false";
  if (twin) twin.setStale(true);
}

function renderEvent(ev) {
  const el = $("tele-event");
  const time = new Date().toLocaleTimeString("tr-TR");
  if (ev.accepted) {
    el.dataset.kind = "ok";
    el.textContent = t("web.event.accepted", { time, trajectory: ev.trajectory_id || "—" });
  } else {
    el.dataset.kind = "error";
    el.textContent = t("web.event.rejected", {
      time,
      requirement: ev.requirement || "—",
      reason: ev.reason || "",
    });
  }
}

// --- Elle sürme ---------------------------------------------------------------------------------

function initJog() {
  $("jog").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const [x, y, z] = ["x", "y", "z"].map((k) => Number($(`jog-${k}`).value));
    await doMove(x, y, z);
  });
  $("jog-home").addEventListener("click", async () => {
    const home = robotInfo?.home_mm;
    if (!home) return;
    ["x", "y", "z"].forEach((k, i) => ($(`jog-${k}`).value = home[i]));
    await doMove(...home);
  });
  $("magnet-toggle").addEventListener("click", async () => {
    const on = !lastState?.magnet;
    try {
      const r = await api.magnet(on);
      setResult($("jog-result"), "ok", r.magnet ? t("web.magnet.on") : t("web.magnet.off"));
    } catch (e) {
      setResult($("jog-result"), "error", errorText(e));
    }
  });
  $("torque-on").addEventListener("click", async () => {
    try {
      await api.torque(true);
      setResult($("jog-result"), "ok", t("web.jog.torque_ok"));
    } catch (e) {
      setResult($("jog-result"), "error", errorText(e));
    }
  });
  // Dur: her zaman etkin; iş çalışırken de kabul edilir (sözleşme).
  for (const b of document.querySelectorAll('[data-action="stop"]')) {
    b.addEventListener("click", async () => {
      try {
        await api.stop();
        setResult($("jog-result"), "warn", t("web.jog.stopped"));
      } catch (e) {
        setResult($("jog-result"), "error", errorText(e));
      }
    });
  }
}

async function doMove(x, y, z) {
  const out = $("jog-result");
  if (![x, y, z].every(Number.isFinite)) {
    setResult(out, "error", t("web.jog.invalid"));
    return;
  }
  setResult(out, "info", t("web.jog.moving", { x, y, z }));
  try {
    const r = await api.move(x, y, z);
    if (!r.accepted) {
      setResult(
        out,
        "error",
        t("web.move.rejected", { requirement: r.requirement || "—", reason: r.reason || "" }),
      );
    } else if (r.done === false) {
      setResult(out, "warn", t("web.move.not_done", { reason: r.reason || "" }));
    } else {
      setResult(out, "ok", t("web.move.done", { pos: fmtVec(r.position_mm) }));
    }
  } catch (e) {
    setResult(out, "error", errorText(e));
  }
}

// --- Kod editörü ve işler -----------------------------------------------------------------------

async function initEditor() {
  let starter = "";
  try {
    const res = await fetch("examples/baslangic.py");
    if (res.ok) starter = await res.text();
  } catch {
    starter = "";
  }
  const host = $("editor");
  if (window.CodeMirror) {
    editor = window.CodeMirror(host, {
      value: starter,
      mode: "python",
      lineNumbers: true,
      indentUnit: 4,
      extraKeys: { "Ctrl-Enter": runJob, "Cmd-Enter": runJob, Tab: "indentMore" },
    });
  } else {
    // CDN yoksa düz metin alanı
    const ta = document.createElement("textarea");
    ta.className = "editor-fallback";
    ta.value = starter;
    ta.spellcheck = false;
    host.appendChild(ta);
    editor = { getValue: () => ta.value };
  }
  $("run").addEventListener("click", runJob);
  $("cancel").addEventListener("click", cancelJob);
  $("console-clear").addEventListener("click", () => ($("console").textContent = ""));
}

const job = { id: null, ws: null, status: "none" };

function consoleWrite(text, kind = "stdout") {
  const c = $("console");
  const span = document.createElement("span");
  span.className = kind;
  span.textContent = text;
  c.appendChild(span);
  while (c.childNodes.length > CONSOLE_MAX_LINES) c.removeChild(c.firstChild);
  c.scrollTop = c.scrollHeight;
}

function setJobStatus(status, extra = {}) {
  job.status = status;
  const b = $("job-status");
  b.dataset.status = status;
  b.textContent = t(JOB_KEYS[status] || "web.job.status.none");
  const active = status === "queued" || status === "running";
  $("run").disabled = active;
  $("cancel").disabled = !active;
  if (JOB_FINAL.has(status)) {
    const params = { exit_code: extra.exit_code ?? "—", reason: extra.reason || "" };
    consoleWrite(t("web.console.finished", { status: b.textContent, ...params }) + "\n", "meta");
  }
}

async function runJob() {
  if (job.status === "queued" || job.status === "running") return;
  const code = editor.getValue();
  $("console").textContent = "";
  try {
    const r = await api.submitJob(code, "web");
    job.id = r.job_id;
    $("job-id").textContent = r.job_id;
    setJobStatus(r.status || "queued");
    consoleWrite(t("web.console.started", { id: r.job_id }) + "\n", "meta");
    followJob(r.job_id);
  } catch (e) {
    consoleWrite(errorText(e) + "\n", "stderr");
  }
}

function followJob(id) {
  const ws = new WebSocket(wsUrl(`/ws/jobs/${encodeURIComponent(id)}`));
  job.ws = ws;
  ws.onmessage = (m) => {
    let msg;
    try {
      msg = JSON.parse(m.data);
    } catch {
      return;
    }
    if (msg.type === "stdout" || msg.type === "stderr") consoleWrite(msg.data, msg.type);
    else if (msg.type === "status") setJobStatus(msg.status, msg);
  };
  // Sunucu iş bitince kapatır; son durum gelmediyse REST'ten okunur.
  ws.onclose = async () => {
    job.ws = null;
    if (job.id !== id || JOB_FINAL.has(job.status)) return;
    try {
      const j = await api.job(id);
      if (JOB_FINAL.has(j.status)) setJobStatus(j.status, j);
      else consoleWrite(t("web.console.stream_lost") + "\n", "stderr");
    } catch (e) {
      consoleWrite(errorText(e) + "\n", "stderr");
    }
  };
}

async function cancelJob() {
  if (!job.id) return;
  try {
    await api.cancelJob(job.id);
  } catch (e) {
    consoleWrite(errorText(e) + "\n", "stderr");
  }
}

// --- Başlangıç ----------------------------------------------------------------------------------

async function main() {
  await loadCatalog("tr");
  document.title = t("app.title");
  applyI18n();
  renderDisconnected();
  $("magnet-badge").textContent = t("web.magnet.off");
  initLogin();
  initJog();
  await initEditor();
  connectAll();
}

main();
