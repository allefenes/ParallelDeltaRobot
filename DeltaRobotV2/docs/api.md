# Komut API'si, Python istemcisi ve sandbox sözleşmesi (F4)

Bu belge F4 bileşenleri arasındaki tek sözleşmedir: `api/` (ağ geçidi), `client/` (pip istemcisi), `sandbox/` (koşucu + kullanıcı kodu konteyneri) ve `web/` (tarayıcı arayüzü). Bir alan değişirse önce burası değişir. Sürüm: `v1`.

## Bileşenler ve akış

```
Tarayıcı (web/)  ──HTTPS + WSS, token──┐
VS Code (client/) ──HTTPS + WSS, token──┤
                                        ▼
                 api (FastAPI, rclpy)  ── ROS2 (localhost, server ağ ad alanı) ──  ROS2 yığını
                        │  ws://runner:8100/run (iç ağ)
                        ▼
                 runner ── docker run (ağsız, salt okunur, kaynak sınırlı) ── sandbox: kullanıcı kodu
                                        stdin/stdout satır protokolü        + client/ (stdio taşıması)
```

- `api` konteyneri `server` konteynerinin ağ ad alanını paylaşır (`network_mode: service:server`). ROS2 trafiği yalnız localhost'ta kalır; ağ üzerinden DDS yoktur (mimari ilke).
- Dışarı açık tek port: `https://localhost:8000` (yerel, kendinden imzalı sertifika, `certs` birimi). Kenar uç noktası `wss://server:8443/edge` iç ağdadır (F5'te Pi için açılır).
- Kullanıcı kodu robotta da sunucu sürecinde de çalışmaz; yalnız bu API'nin komutlarını kullanır (G11).

## Kimlik doğrulama

- REST: `Authorization: Bearer <token>`.
- WebSocket: `?token=<token>` sorgu parametresi (tarayıcı WS başlığı gönderemez).
- Yerel geliştirmede belirteçler `api/config/tokens.yaml` ya da `DELTA_API_TOKENS` ortam değişkeninden (`ad:belirteç,ad2:belirteç2`). Kiralama ve kullanıcı hesapları F6'dadır.
- Geçersiz/eksik belirteç: `401 {"error": "unauthorized", "message": "..."}`.

## Kontrol kilidi

Tek robot vardır. Bir iş (sandbox'ta kod) çalışırken robot komutları yalnız o işten kabul edilir; diğer çağrılar `409 {"error": "busy", "message": "...", "job_id": "..."}` alır. İş yokken belirteç sahibi doğrudan komut verebilir. `POST /stop` her zaman kabul edilir (güvenlik). Duruştan sonra robot HOLDING'dedir; yeniden hareket için `POST /torque {"on": true}` ile IDLE'a dönülür. İş bitmeden sonlanırsa (hata, iptal, zaman aşımı) API robotu durdurur.

Statik dosyalar (`/`, `/assets/meshes/*`, `/i18n/*`) belirteç gerektirmez; robot verisi ve komutlar gerektirir.

## REST uç noktaları (`/api/v1`)

Tüm gövdeler JSON. Uzunluk mm, açı derece, süre saniye. Hata gövdesi: `{"error": <kod>, "message": <Türkçe metin>}`; kodlar `bad_request` (400), `unauthorized` (401), `not_found` (404), `busy` (409), `rate_limited` (429, F6), `robot_unavailable` (503), `capacity` (503, F6: oturum sınırı dolu). `GET /health` yanıtında `mode`: `robot` (tek robot, kontrol kilidi) ya da `sim` (F6: ziyaretçi başına simülasyon oturumu; kilit oturum başına). İşler yalnız sahibine görünür; başkasının işi `404`.

| Yöntem | Yol                 | Gövde                                                                | Yanıt                                                                                      |
| ------ | ------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| GET    | `/health`           | —                                                                    | `{"ok": true, "edge_connected": bool, "version": "v1"}` (belirteç gerekmez)                |
| GET    | `/robot`            | —                                                                    | Robot tanımı (aşağıda)                                                                     |
| GET    | `/state`            | —                                                                    | Durum (aşağıda)                                                                            |
| POST   | `/move`             | `{"x", "y", "z", "duration_s": number \| null, "wait": bool = true}` | Hareket sonucu (aşağıda)                                                                   |
| POST   | `/magnet`           | `{"on": bool}`                                                       | `{"ok": true, "magnet": bool}`                                                             |
| POST   | `/torque`           | `{"on": bool}`                                                       | `{"ok": true}`                                                                             |
| POST   | `/stop`             | `{}`                                                                 | `{"ok": true}`; robot o anki konumda durur ve tutar (HOLD)                                 |
| GET    | `/board`            | —                                                                    | Tabla ikizi (F4.5, aşağıda)                                                                |
| POST   | `/board/reset`      | `{}`                                                                 | `{"ok": true}`; taşlar başlangıç dizilişine (yalnız simülasyon); robot hareket ederken 409 |
| POST   | `/jobs`             | `{"code": str, "name": str?}`                                        | `202 {"job_id": str, "status": "queued"}`; kod ≤ 64 KB                                     |
| GET    | `/jobs/{id}`        | —                                                                    | İş (aşağıda)                                                                               |
| POST   | `/jobs/{id}/cancel` | `{}`                                                                 | `{"ok": true}`                                                                             |

### Robot tanımı (`GET /robot`)

```json
{
  "name": "Delta Robotics V2",
  "geometry": {
    "R": 65,
    "L1": 64,
    "L2": 201,
    "r": 35,
    "tool_offset_mm": 15,
    "arm_angles_deg": [0, 120, 240],
    "base_to_floor_mm": 240,
    "rod_spacing_mm": 30
  },
  "limits": {
    "motor_min_deg": -70,
    "motor_max_deg": 150,
    "rod_tilt_max_deg": 13,
    "min_tool_z_mm": -236,
    "max_joint_velocity_deg_s": 300,
    "max_joint_acceleration_deg_s2": 3000
  },
  "workspace": {
    "cylinder_diameter_mm": 82,
    "z_top_mm": -145,
    "z_bottom_mm": -221,
    "reference": "P"
  },
  "home_mm": [0, 0, -200]
}
```

Değerler `config/robot.yaml` ve datasheet hesaplarından gelir; istemciler sabit değer gömmez, buradan okur. Çalışma alanı z değerleri P içindir. `z_bottom_mm` kinematik alt sınır (−250) ile G14 sınırının (mıknatıs ucu tabla üstü −236'nın altına inemez: P ≥ −236 + 15 = −221) büyüğüdür.

### Tabla ikizi (`GET /board`, F4.5)

Kaydırmalı tic-tac-toe tablası; kurallar ve geometri `ros2_ws/src/delta_server/delta_server/board_game.py`.

```json
{
  "cells": "XXX...OOO",
  "winner": null,
  "pieces": [{ "id": "X1", "kind": "X", "pos_mm": [-20, 20, -236], "held": false }],
  "metrics": {
    "picks": 0,
    "places": 0,
    "dropped": 0,
    "off_board": 0,
    "missed_picks": 0,
    "placement_error_mean_mm": null,
    "placement_error_max_mm": null
  },
  "geometry": {
    "center_mm": [0, 0],
    "cell_mm": 20,
    "board_top_mm": -236,
    "piece_height_mm": 8,
    "piece_diameter_mm": 16,
    "pick_P_mm": -213,
    "travel_P_mm": -185
  }
}
```

Hücre sırası `satır * 3 + sütun`; satır 0 = +Y tarafı, sütun 0 = −X tarafı. İstemci: `robot.board()`, `robot.reset_board()`, `robot.cell_xy(i)`, `robot.pick_place(src, dst)`.

### Durum (`GET /state`, telemetri akışı)

```json
{
  "state": "IDLE | RUNNING | HOLDING | TORQUE_OFF | FAULT | ESTOP | DISCONNECTED",
  "angles_deg": [0.0, 0.0, 0.0],
  "position_mm": [0.0, 0.0, -200.0],
  "magnet": false,
  "temps_c": [30, 30, 30],
  "loads": [0, 0, 0],
  "voltages": [12.0, 12.0, 12.0],
  "trajectory_id": "traj-0001-ab12cd",
  "edge_connected": true,
  "job_id": null
}
```

`position_mm` platform eklem düzlemi merkezi P'dir (ileri kinematik); çözümsüzse `null`.

### Hareket sonucu (`POST /move`)

Kapı reddi HTTP hatası değildir; `200` ile `accepted: false` döner.

```json
{ "accepted": true, "trajectory_id": "traj-0002-...", "done": true, "position_mm": [20, 10, -200] }
{ "accepted": false, "requirement": "G2", "reason": "G2: rot başı açı limiti (hedef yol, kol 2, örnek 66)" }
```

`wait: true` ise yanıt yörünge bitince (kenar IDLE, aynı `trajectory_id`) ya da hata/bekçi durumunda döner (`done: false`, `reason`). Bekleme üst sınırı: yörünge süresi + 5 s. `duration_s: null` güvenli süreyi planlayıcı seçer.

### İş (`GET /jobs/{id}`)

```json
{
  "job_id": "job-0001-ab12",
  "name": "tic-tac-toe",
  "status": "queued | running | done | failed | timeout | cancelled",
  "exit_code": 0,
  "output": "kırpılmış stdout+stderr (≤ 64 KB)",
  "reason": "...",
  "created_at": "ISO-8601",
  "started_at": "...",
  "finished_at": "..."
}
```

## WebSocket uç noktaları

- `GET /api/v1/ws/telemetry?token=...` → sunucu 20 Hz'de `{"type": "state", ...durum}` gönderir; süpervizör olaylarında `{"type": "event", "accepted": bool, "requirement": "G2", "reason": "...", "trajectory_id": "..."}`.
- `GET /api/v1/ws/jobs/{id}?token=...` → `{"type": "stdout" | "stderr", "data": str}`, `{"type": "status", "status": ..., "exit_code": int?, "reason": str?}`. İş bitince sunucu bağlantıyı kapatır.

## Python istemcisi (`client/`, pip paketi `delta-robot-client`, içe aktarma `delta_robot`)

```python
from delta_robot import Robot, CommandRejected

robot = Robot()                      # DELTA_URL, DELTA_TOKEN, DELTA_CA_FILE ortam değişkenleri
robot = Robot("https://localhost:8000", token="...", verify="ca.crt")
info = robot.info()                  # /robot
s = robot.state()                    # State dataclass
robot.move_to(20, 10, -200)          # bekler; reddedilirse CommandRejected(requirement, reason)
r = robot.move_to(0, 0, -300, check=False)  # MoveResult; istisna yok
robot.magnet(True); robot.magnet(False)
robot.stop(); robot.torque(True)
for s in robot.telemetry():          # WS akışı (yalnız ağ taşımasında)
    ...
```

- Taşıma: `DELTA_TRANSPORT=stdio` ise (sandbox) aşağıdaki satır protokolü, yoksa HTTPS.
- Bağımlılıklar: `httpx`, `websockets`. Python ≥ 3.10. Saf Python (C++ derlemesi gerekmez).

## Sandbox (`sandbox/`)

### Kullanıcı kodu konteyneri

`docker run` bayrakları (koşucu tarafından, değiştirilemez): `--network none --read-only --tmpfs /tmp:rw,size=16m,noexec --memory 256m --memory-swap 256m --cpus 0.5 --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges --user 65534:65534 -i --rm`; duvar saati sınırı 120 s (`timeout`), çıktı sınırı 1 MB (aşınca iş durdurulur). İmaj: `deltarobotv2-sandbox:latest` (python:3.12-slim + `client/`, başka paket yok). Kod `stdin` ile değil, ilk satırdaki `{"code": ...}` başlangıç mesajıyla gelir ve `/tmp` yerine bellekte `exec` edilir.

### stdio satır protokolü (kullanıcı kodu ↔ koşucu)

- İstek (konteyner `stdout`'una, tek satır): `\x1eDELTA {"id": 1, "method": "move", "params": {...}}`
- Yanıt (konteyner `stdin`'ine, tek satır JSON): `{"id": 1, "result": {...}}` ya da `{"id": 1, "error": {"code": "busy", "message": "..."}}`
- `\x1eDELTA ` önekiyle başlamayan `stdout` satırları kullanıcı çıktısıdır. `method`: `robot`, `state`, `move`, `magnet`, `torque`, `stop`, `board`, `board_reset`; `params` ve `result` REST gövdeleriyle aynıdır.

### Koşucu ↔ API (`ws://runner:8100/run`, iç ağ, paylaşılan gizli anahtar `DELTA_RUNNER_SECRET`)

API → koşucu: `{"type": "start", "job_id", "code", "secret", "timeout_s"?}` (`timeout_s`: işe özel süre, koşucu sınırını aşamaz), `{"type": "rpc_result", "id", "result" | "error"}`, `{"type": "cancel"}`.
Koşucu → API: `{"type": "rpc", "id", "method", "params"}`, `{"type": "stdout" | "stderr", "data"}`, `{"type": "exit", "exit_code", "reason": "ok | timeout | output_limit | cancelled | error"}`.

## Güvenlik gereksinimi G11 testleri

`sandbox/tests/` ağ erişimi (DNS, TCP, kenar uç noktası), dosya sistemine yazma (`/`, `/home`, `/tmp` boyut sınırı, `noexec`), bellek, süreç sayısı (fork bombası), CPU/duvar saati, çıktı taşması, yetki yükseltme ve konteynerden kaçış denemelerinin hepsinin engellendiğini doğrular. Test adları `G11_` ile başlar.

## F6 deneyim arayüzü (simülasyon modu, üyeliksiz)

Kullanıcı kararı (2026-11-12): nihai site üyeliksiz, tek sayfalık bir deneyim arayüzüdür; robot dijital ikizde (simülasyon) çalışır. API `DELTA_API_MODE=sim` ile başlar; her ziyaretçi kendi yalıtılmış simülasyon oturumunu alır.

### Anonim oturum

| Yöntem | Yol        | Gövde                    | Yanıt                                                                                                                                                                   |
| ------ | ---------- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| POST   | `/session` | `{}` (belirteç gerekmez) | `201 {"token": str, "idle_timeout_s": 600}`; IP başına dakikada 10 oturum → `429 {"error": "rate_limited"}`; eşzamanlı oturum sınırı dolu → `503 {"error": "capacity"}` |

- Dönen belirteç diğer uç noktalarda `Authorization: Bearer` / WS `?token=` olarak kullanılır. Oturum `idle_timeout_s` boyunca istek ya da açık telemetri bağlantısı olmazsa silinir; sonraki çağrı `401` alır, arayüz yeni oturum açar.
- Oturum başına istek sınırı: saniyede 20 istek → `429`.

### Manuel mod

| Yöntem | Yol              | Gövde                                                                             | Yanıt                                                                                                                                |
| ------ | ---------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| POST   | `/move_joints`   | `{"angles_deg": [θ1, θ2, θ3], "duration_s": number \| null, "wait": bool = true}` | Hareket sonucu (`/move` ile aynı); eklem uzayında yumuşak (quintic) yörünge, aynı 1. kapıdan (G1–G5, G14) geçer                      |
| POST   | `/kinematics/fk` | `{"angles_deg": [θ1, θ2, θ3]}`                                                    | `{"ok": bool, "position_mm": [x, y, z] \| null, "requirement": str?, "reason": str?}`; hareket yok, nokta denetimi (G1, G2, G3, G14) |
| POST   | `/kinematics/ik` | `{"x", "y", "z"}`                                                                 | `{"ok": bool, "angles_deg": [θ1, θ2, θ3] \| null, "requirement": str?, "reason": str?}`; hareket yok                                 |

### Otomatik mod (tic-tac-toe)

| Yöntem | Yol           | Gövde | Yanıt                                                                                                                                               |
| ------ | ------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| POST   | `/auto/start` | `{}`  | `{"ok": true}`; robot iki minimaks oyuncuyla kendi kendine oynar (taşları gerçekten al-taşı-bırak ile taşır). Çalışırken manuel komutlar `409 busy` |
| POST   | `/auto/stop`  | `{}`  | `{"ok": true}`; hareket kesilir, robot durur (HOLDING) ve IDLE'a alınır                                                                             |

`GET /board` yanıtına `auto` alanı eklenir:

```json
{
  "auto": {
    "status": "idle | playing | finished | stopped | error",
    "turn": "X",
    "reason": null,
    "moves": [{ "n": 1, "kind": "X", "from": 1, "to": 4 }]
  }
}
```

`POST /stop` otomatik oyunu da durdurur. `POST /board/reset` oyun bitmiş ya da durmuşken taşları başlangıca alır.
