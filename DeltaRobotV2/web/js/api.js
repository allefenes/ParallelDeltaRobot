// API istemcisi (docs/api.md, v1). REST: Bearer başlığı; WebSocket: ?token= sorgu parametresi.
const TOKEN_KEY = "delta.token";
const BASE = "/api/v1";

let token = "";
try {
  token = localStorage.getItem(TOKEN_KEY) || "";
} catch {
  token = "";
}

export function getToken() {
  return token;
}

export function setToken(value) {
  token = value.trim();
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Depolama kapalıysa belirteç yalnız bu sekmede tutulur.
  }
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

export async function request(method, path, body) {
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

export const api = {
  health: () => request("GET", "/health"),
  robot: () => request("GET", "/robot"),
  state: () => request("GET", "/state"),
  move: (x, y, z) => request("POST", "/move", { x, y, z, duration_s: null, wait: true }),
  magnet: (on) => request("POST", "/magnet", { on }),
  torque: (on) => request("POST", "/torque", { on }),
  stop: () => request("POST", "/stop", {}),
  submitJob: (code, name) => request("POST", "/jobs", { code, name }),
  job: (id) => request("GET", `/jobs/${encodeURIComponent(id)}`),
  cancelJob: (id) => request("POST", `/jobs/${encodeURIComponent(id)}/cancel`, {}),
};

// Aynı kökene ws(s):// adresi; belirteç sorgu parametresinde.
export function wsUrl(path) {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${location.host}${BASE}${path}?token=${encodeURIComponent(token)}`;
}
