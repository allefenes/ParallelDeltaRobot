// API istemcisi (docs/api.md, v1 + F6). REST: Bearer başlığı; WebSocket: ?token= sorgu parametresi.
// F6: belirteç anonim oturumdan (POST /session) gelir; 401'de oturum sessizce yeniden açılır.
const TOKEN_KEY = "delta.session";
const BASE = "/api/v1";

let token = "";
try {
  token = sessionStorage.getItem(TOKEN_KEY) || "";
} catch {
  token = "";
}

const sessionListeners = new Set();
let pendingSession = null;

export function getToken() {
  return token;
}

export function setToken(value) {
  token = (value || "").trim();
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // Depolama kapalıysa belirteç yalnız bellekte tutulur.
  }
}

// Yeni oturum açıldığında (ör. telemetriyi yeni belirteçle yeniden bağlamak için) çağrılır.
export function onSession(fn) {
  sessionListeners.add(fn);
  return () => sessionListeners.delete(fn);
}

// Sunucu hatası: gövdedeki {error, message} korunur.
export class ApiError extends Error {
  constructor(status, body) {
    super(body?.message || `HTTP ${status}`);
    this.status = status;
    this.code = body?.error || null;
    this.body = body;
  }
}

async function rawRequest(method, path, body) {
  const headers = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, { error: "network" });
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

// Anonim oturum açar; eşzamanlı çağrılar aynı isteği paylaşır. 429/503 ApiError olarak döner.
export function createSession() {
  if (!pendingSession) {
    pendingSession = (async () => {
      const saved = token;
      token = "";
      try {
        const r = await rawRequest("POST", "/session", {});
        setToken(r.token);
        for (const fn of sessionListeners) fn(r);
        return r;
      } catch (e) {
        token = saved;
        throw e;
      } finally {
        pendingSession = null;
      }
    })();
  }
  return pendingSession;
}

export async function ensureSession() {
  if (!token) await createSession();
  return token;
}

// 401: oturum silinmiş (boşta zaman aşımı); bir kez yeni oturumla yeniden denenir.
export async function request(method, path, body) {
  if (pendingSession) await pendingSession.catch(() => {});
  try {
    return await rawRequest(method, path, body);
  } catch (e) {
    if (e.status !== 401 || path === "/session") throw e;
    await createSession();
    return rawRequest(method, path, body);
  }
}

export const api = {
  health: () => request("GET", "/health"),
  robot: () => request("GET", "/robot"),
  state: () => request("GET", "/state"),
  move: (x, y, z) => request("POST", "/move", { x, y, z, duration_s: null, wait: true }),
  moveJoints: (angles) =>
    request("POST", "/move_joints", { angles_deg: angles, duration_s: null, wait: true }),
  fk: (angles) => request("POST", "/kinematics/fk", { angles_deg: angles }),
  ik: (x, y, z) => request("POST", "/kinematics/ik", { x, y, z }),
  magnet: (on) => request("POST", "/magnet", { on }),
  torque: (on) => request("POST", "/torque", { on }),
  stop: () => request("POST", "/stop", {}),
  board: () => request("GET", "/board"),
  resetBoard: () => request("POST", "/board/reset", {}),
  autoStart: () => request("POST", "/auto/start", {}),
  autoStop: () => request("POST", "/auto/stop", {}),
  // F4 iş uç noktaları: bu sayfa kullanmaz; istemciler için korunur.
  submitJob: (code, name) => request("POST", "/jobs", { code, name }),
  job: (id) => request("GET", `/jobs/${encodeURIComponent(id)}`),
  cancelJob: (id) => request("POST", `/jobs/${encodeURIComponent(id)}/cancel`, {}),
};

// Aynı kökene ws(s):// adresi; belirteç sorgu parametresinde.
export function wsUrl(path) {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${location.host}${BASE}${path}?token=${encodeURIComponent(token)}`;
}
