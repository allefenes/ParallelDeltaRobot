# delta-robot-client

Delta Robotics V2 uzak robot API'si için Python istemcisi (içe aktarma adı `delta_robot`). Sözleşme: [`../docs/api.md`](../docs/api.md). Saf Python, Python ≥ 3.10; bağımlılıklar `httpx` ve `websockets`.

## Kurulum

```bash
pip install ./client                      # DeltaRobotV2/ kökünden
pip install "delta-robot-client @ git+https://github.com/allefenes/ParallelDeltaRobot.git#subdirectory=DeltaRobotV2/client"
```

## Ortam değişkenleri

| Değişken          | Anlam                                                             | Varsayılan               |
| ----------------- | ----------------------------------------------------------------- | ------------------------ |
| `DELTA_URL`       | API adresi                                                        | `https://localhost:8000` |
| `DELTA_TOKEN`     | Erişim belirteci (`Authorization: Bearer`, WS'de `?token=`)       | —                        |
| `DELTA_CA_FILE`   | Kendinden imzalı sunucu için CA sertifikası                       | sistem sertifikaları     |
| `DELTA_TRANSPORT` | `stdio` ise sandbox satır protokolü; sandbox bunu kendisi ayarlar | HTTPS                    |

Yapıcıya verilen `url`, `token`, `verify` değerleri ortam değişkenlerinden önce gelir.

## VS Code'dan kullanım

```python
from delta_robot import CommandRejected, Robot

with Robot() as robot:              # ya da Robot("https://localhost:8000", token="...", verify="ca.crt")
    print(robot.info()["workspace"])
    robot.move_to(20, 10, -200)     # yörünge bitene kadar bekler
    robot.magnet(True)
    try:
        robot.move_to(0, 0, -300)
    except CommandRejected as e:
        print(e.requirement, e.reason)
    r = robot.move_to(0, 0, -300, check=False)   # istisna yok, r.accepted False
    for s in robot.telemetry():     # 20 Hz durum akışı
        print(s.state, s.position_mm)
        break
```

Hatalar: `AuthError` (401), `RobotBusy` (409, `job_id`), `RobotUnavailable` (503), diğerleri `DeltaError`. Kapı reddi `CommandRejected`, kabul edilip tamamlanmayan hareket `MoveNotCompleted` olur (`check=False` ile ikisi de kapanır). NaN, sonsuz ve bool koordinatlar istemcide `ValueError` ile reddedilir; sunucu yine de denetler.

Tam örnek: [`examples/hello.py`](examples/hello.py).

## Sandbox notu

Web arayüzünden gönderilen kod ağsız bir konteynerde çalışır; aynı paket orada `DELTA_TRANSPORT=stdio` ile koşucuya `stdout`/`stdin` üzerinden bağlanır. Kod değişmeden iki ortamda da çalışır; tek fark `telemetry()` yalnız ağ taşımasında vardır, sandbox'ta durum için `state()` kullanılır. `\x1eDELTA ` ile başlayan satırlar protokole aittir, kullanıcı `print` çıktısı etkilenmez.

## Test

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "$(cygpath -w "$PWD"):/w" -w /w/client python:3.12-slim \
  bash -c "pip install -q -e .[test] && pytest -q --cov=delta_robot"
```
