# delta_edge — Raspberry Pi kenar servisi

İnce ama güvenli kenar ([mimari](../docs/mimari.md)): sunucudan gelen zaman damgalı yörüngeyi yerel saatle 100 Hz'de oynatır, **son güvenlik kapısını** uygular, kalp atışı bekçisini çalıştırır, telemetri yayınlar ve sunucuya **kendisi bağlanır** (TLS WebSocket). ROS kullanmaz; C++17.

## Yapı

| Dosya                                                           | Görev                                                                                                                       |
| --------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `include/delta_edge/protocol.hpp`                               | Kenar protokolü v1 (JSON); katı ayrıştırıcı, istisna fırlatmaz                                                              |
| `include/delta_edge/gate.hpp`                                   | Son kapı: eklem limitleri (G1), sonlu değer (G4), hız/ivme ve ilk nokta sıçraması (G5), sağlık sınırları (G9), komut kırpma |
| `include/delta_edge/player.hpp`                                 | Yörünge tamponu; enjekte edilen monoton saatle oynatma                                                                      |
| `include/delta_edge/watchdog.hpp`                               | Kalp atışı: T_stop → dur-tut (G6), T_off → tork ve mıknatıs kapalı (G7)                                                     |
| `include/delta_edge/state.hpp`                                  | Durumlar: IDLE, RUNNING, HOLDING, FAULT, TORQUE_OFF, ESTOP                                                                  |
| `include/delta_edge/driver.hpp`                                 | Sürücü arayüzü; seri hattın tek sahibi (G10). `MockDriver` (sanal Pi), `Ax12Driver` (AX-12A)                                |
| `include/delta_edge/dynamixel_protocol.hpp`                     | Dynamixel Protokol 1.0: paket kurma, sağlama, akış ayrıştırıcısı (çöpte yeniden eşleme), AX-12A denetim tablosu             |
| `include/delta_edge/dynamixel_bus.hpp`                          | İşlem katmanı: PING / READ / WRITE / SYNC_WRITE, zaman aşımı, yanlış ID/boy, hata biti, yerel yankı                         |
| `include/delta_edge/serial.hpp`, `posix_serial.hpp`             | `SerialPort` arayüzü; POSIX gerçeklemesi aygıtı açan TEK dosyadır (termios ham, flock + TIOCEXCL)                           |
| `include/delta_edge/motor_config.hpp`                           | Motor YAML okuyucu, doğrulama, θ ↔ tick eşlemesi ve limit penceresi                                                        |
| `include/delta_edge/magnet_output.hpp`                          | Mıknatıs çıkışı arayüzü: boş çıkış ya da dosya (GPIO F5'te)                                                                 |
| `include/delta_edge/servo_tool.hpp`, `app/delta_servo_tool.cpp` | Kurulum aracı: tarama, ID/baud atama, okuma, tork                                                                           |
| `config/motor_ax12.yaml`                                        | AX-12A parametreleri (`motor:` bölümü, `model` arka ucu seçer)                                                              |
| `include/delta_edge/edge.hpp`                                   | `EdgeCore`: mesaj + tick → giden mesajlar (soket yok, test edilebilir)                                                      |
| `app/main.cpp`                                                  | Boost.Beast + OpenSSL istemcisi, yeniden bağlanma (üstel bekleme)                                                           |
| `config/edge.yaml`                                              | Kenara özgü sınırlar; eklem açı limitleri tek kaynak `config/robot.yaml`                                                    |
| `fuzz/`                                                         | Protokol ayrıştırıcı için libFuzzer hedefi ve tohum derlemi                                                                 |

## Protokol v1 (WebSocket metin çerçevesi, JSON, `v: 1`)

| Mesaj                     | Yön         | Alanlar                                                             | Sıklık |
| ------------------------- | ----------- | ------------------------------------------------------------------- | ------ |
| `trajectory`              | sunucu → Pi | `id`, `period_ms` (5–50), `points` [[θ1,θ2,θ3] deg], ops. `magnet`  | olay   |
| `heartbeat`               | sunucu → Pi | `seq` (kesin artan)                                                 | ~20 Hz |
| `stop` / `hold` / `reset` | sunucu → Pi | —                                                                   | olay   |
| `torque` / `magnet`       | sunucu → Pi | `on`                                                                | olay   |
| `telemetry`               | Pi → sunucu | `state`, `angles`, `temps`, `loads`, `voltages`, `traj_id`, `index` | 20 Hz  |
| `ack`                     | Pi → sunucu | `id` (kabul edilen yörünge)                                         | olay   |
| `fault`                   | Pi → sunucu | `code` (`faults.hpp`), `detail`                                     | olay   |

## Zamanlamalar ve sınırlar (`config/edge.yaml`, varsayım)

T_stop 200 ms, T_off 1000 ms, en çok 300 °/s ve 3000 °/s², sıcaklık 70 °C, gerilim 9–13 V, yük %90, döngü 100 Hz. Açılışta durum TORQUE_OFF'tur; hareket için taze kalp atışı + `torque on` gerekir. T_off'tan sonra mıknatıs **kapatılır**: bağlantı koptuğunda taşı tutmaya devam etmek yerine bilinen, enerjisiz bir duruma geçmek tercih edildi (taş en fazla tablaya düşer).

## AX-12A arka ucu (`DELTA_DRIVER=ax12`)

Protokol 1.0, 1 Mbps, yarım dupleks TTL. Sürücü seri hatta yalnız `SerialPort` arayüzüyle erişir; aygıtı `src/posix_serial.cpp` açar ve **özel kilitler** (G10): `flock` ikinci bir süreci root dahil reddeder, `TIOCEXCL` kilidi tanımayan araçları durdurur. `delta_edge` çalışırken `delta_servo_tool` portu açamaz.

| Ortam değişkeni       | Varsayılan                    | Anlam                                                                             |
| --------------------- | ----------------------------- | --------------------------------------------------------------------------------- |
| `DELTA_DRIVER`        | `mock`                        | `ax12` gerçek servolar                                                            |
| `DELTA_SERIAL_DEVICE` | `/dev/ttyAMA0`                | Pi PL011 UART (GPIO14/15); USB adaptörde ör. `/dev/ttyUSB0`                       |
| `DELTA_MOTOR_CONFIG`  | `edge/config/motor_ax12.yaml` | motor parametreleri (`--motor-config`)                                            |
| `DELTA_MAGNET_FILE`   | —                             | mıknatıs durumu dosyaya `1`/`0` yazılır (sysfs GPIO ya da gözlem); yoksa sürülmez |

**Neden `/dev/ttyAMA0`:** 1 Mbps için PL011 gerekir; mini UART (`ttyS0`) hızı çekirdek saatine bağlıdır. Pi 3/4'te `config.txt`: `enable_uart=1`, `dtoverlay=disable-bt`; `cmdline.txt`'den `console=serial0,...` silinir. Yön (TX/RX) denetimi donanımdadır (otomatik yönlü tampon ya da U2D2); tek telli, yankılı hatta `bus.local_echo: true`.

**Davranış.** `set_goal`: üç servoya tek Sync Write (Goal Position); hedef eklem limit penceresine kırpılır (G1), sonlu olmayan bir değer varsa hiçbir paket gitmez (G4); tork kapalıyken hedef gönderilmez (AX serisinde Goal yazımı torku açabilir). `read_state`: servo başına bir READ_DATA (0x24..0x2B); zaman aşımı, bozuk sağlama, yanlış ID/boy ya da herhangi bir servo hata biti `ok=false` verir ve EdgeCore torku açmaz / FAULT'a geçer (G9). `set_torque(true)`: gerekirse ilklendirme, Present Position okunur, **Goal = Present** yazılır, sonra her servoya doğrulamalı Torque Enable; bir adım başarısızsa hepsi kapatılır. İlklendirme (açılışta ve tork açılırken): ping, model numarası (12), status return level, return delay, CW/CCW açı limitleri = eklem penceresi (donanım tarafı G1; EEPROM yalnız farklıysa yazılır), Moving Speed.

**Motor yapılandırması** (`config/motor_ax12.yaml`, biçim motora genel): `model`, `bus` (baud, reply_timeout_ms, local_echo, status_return_level, return_delay_us), `position` (ticks, range_deg), `scale` (gerilim/sıcaklık/yük birimleri), `moving_speed`, `write_angle_limits`, `joints` (kol 1-3: `id`, `zero_tick`, `sign`). Eşleme: `tick = zero_tick + sign · θ / (range_deg / ticks)`. Eklem limitleri tek kaynak `config/robot.yaml`'dır; tick karşılıkları `0..ticks-1` dışına düşerse ya da `model`/`range_deg` robot.yaml `motor` bölümüyle tutmazsa yükleme reddedilir. Varsayılan `zero_tick: 376`, `sign: 1` **varsayımdır** (−70..150° → 138..888 tick).

**Kurulum aracı** (`delta_servo_tool`, servolar tek tek bağlanarak; fabrika ayarı ID 1, 1 Mbps):

```bash
delta_servo_tool scan                    # 1 Mbps'te ID 0..253'e ping
delta_servo_tool --baud 57142 scan 0 10  # başka hızda kısmi tarama
delta_servo_tool set-id 1 2              # yalnız bağlı servo; NEW boş olmalı, ping ile doğrulanır
delta_servo_tool set-baud 2 1            # kod 1 = 1 Mbps (baud = 2000000/(kod+1))
delta_servo_tool read 2                  # ID, baud, limitler, konum, yük, gerilim, sıcaklık
delta_servo_tool torque 2 off            # kalibrasyonda kolu elle oynatmak için
```

Seçenekler: `--device PATH` (ya da `DELTA_SERIAL_DEVICE`), `--baud N`, `--timeout-ms N`, `--echo`. Çıkış: 0 tamam, 1 haberleşme, 2 kullanım. Kalibrasyon: her kol yatayken (θ = 0) `read ID` → `present_position` değeri `zero_tick` olur; kol aşağı itilince değer artıyorsa `sign: 1`.

**Testler donanımsız:** `tests/fake_servo_bus.hpp` protokol düzeyinde N servoluk sahte hat (PING/READ/WRITE/SYNC_WRITE, yanıt düşürme, bozuk sağlama, hata bitleri, çöp bayt, yanlış ID, yankı); POSIX katmanı sözde terminal (pty) üzerinde sınanır.

**F5 donanım kabulünde doğrulanacak varsayımlar:** varsayılan aygıt ve UART ayarları; yön donanımı ve `return_delay_us: 100`, `reply_timeout_ms: 5`; her kolun `zero_tick` ve `sign` değeri; Goal yazımının torku kendiliğinden açıp açmadığı; limit dışında başlayan kolda davranış (servo açı limiti hatası verebilir → `ok=false`, güvenli taraf); yük ölçeği (%0,1/birim) ve işaret; mıknatıs GPIO'su ve kapalı tutan çekme direnci.

## Derleme ve test (konteynerde)

`DeltaRobotV2/` içinde:

```bash
docker compose run --rm dev bash -c 'cmake -S edge -B build/edge -G Ninja -DDELTA_EDGE_COVERAGE=ON && cmake --build build/edge && ctest --test-dir build/edge'
```

Testlerin adı kanıtladığı gereksinimle başlar (`G1_…`, `G6_…` vb.); izlenebilirlik: [güvenlik gereksinimleri](../docs/guvenlik-gereksinimleri.md).

## Fuzz ve mutasyon testi (konteynerde)

**Fuzz (G4).** libFuzzer + ASan + UBSan; hedef `fuzz/fuzz_protocol.cpp` (ayrıştırıcı + `EdgeCore`, değişmezler dosyanın başında). Büyüyen derlem depoya yazılmaz, `build/` altındaki kopyada çalışılır:

```bash
docker compose run --rm dev bash -c 'CC=clang CXX=clang++ cmake -S edge -B build/edge-fuzz -G Ninja -DDELTA_EDGE_FUZZ=ON && cmake --build build/edge-fuzz --target fuzz_protocol'
docker compose run --rm dev bash -c 'mkdir -p build/fuzz-run && cp -r edge/fuzz/corpus build/fuzz-run/ && cd build/fuzz-run && ../edge-fuzz/fuzz_protocol -max_total_time=300 -max_len=4096 -artifact_prefix=./ corpus'
```

Bulunan çökme girdisi küçültülür (`-minimize_crash=1`), `fuzz/regressions/` altına konur; `FuzzRegressions` testi her derlemde onu yeniden oynatır.

**Mutasyon.** `tools/mutate.py` (yalnız standart kütüphane) `src/gate.cpp`, `src/watchdog.cpp` ve `src/protocol.cpp` doğrulama bölümüne tek tek basit mutant uygular (ilişkisel işleç, `&&`/`||`, sabit ±1, `true`/`false`, deyim silme), `build/edge-mut` altında artımlı derler (`-D_GLIBCXX_ASSERTIONS`, kapsama yok), `ctest` çalıştırır ve dosyayı her durumda geri yükler (sonda SHA-256 denetimi). Rapor: `build/mutation/report.md` ve `summary.json`.

```bash
docker compose run --rm dev python3 edge/tools/mutate.py            # <=150 mutant, tohum 1, ~27 dk
docker compose run --rm dev python3 edge/tools/mutate.py --list     # yalnız listele
```

**Son sonuçlar (2026-11-12).**

- Fuzz: 2 × 300 s, toplam 174 743 çalıştırma (ilk koşu 105 986, `max_len` 128; ikinci koşu 68 757, `-max_len=4096 -len_control=0`), 2240 kenar kapsaması, 4450 özellik. Çökme, zaman aşımı, ASan/UBSan bulgusu yok.
- Mutasyon (243 adaydan tohum 1 ile 150 örnek): `gate.cpp` 59/60, `protocol.cpp` 56/56, `watchdog.cpp` 15/15 öldürüldü; skor %99,2 (130/131). 19 mutant derlenmedi (skora girmez), zaman aşımı yok. İlk koşuda skor %89,3 idi (14 hayatta kalan); eksikler yeni testlerle kapandı: ilk noktanın limit/NaN denetimi, her eklemde duruştan başlama ivmesi, her eklemde kırpma, servo numaralı hata metni, tam 2 MiB mesaj sınırı, hata metninde 32 karakter kesme.
- Kalan tek mutant eşdeğerdir: `beyond_tolerance` içinde `|d| <= tol` → `|d| < tol`; `|d| == tol` iken iki dal da 0 verir.
