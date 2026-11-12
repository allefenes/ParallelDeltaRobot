# delta_edge — Raspberry Pi kenar servisi

İnce ama güvenli kenar ([mimari](../docs/mimari.md)): sunucudan gelen zaman damgalı yörüngeyi yerel saatle 100 Hz'de oynatır, **son güvenlik kapısını** uygular, kalp atışı bekçisini çalıştırır, telemetri yayınlar ve sunucuya **kendisi bağlanır** (TLS WebSocket). ROS kullanmaz; C++17.

## Yapı

| Dosya                             | Görev                                                                                                                       |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `include/delta_edge/protocol.hpp` | Kenar protokolü v1 (JSON); katı ayrıştırıcı, istisna fırlatmaz                                                              |
| `include/delta_edge/gate.hpp`     | Son kapı: eklem limitleri (G1), sonlu değer (G4), hız/ivme ve ilk nokta sıçraması (G5), sağlık sınırları (G9), komut kırpma |
| `include/delta_edge/player.hpp`   | Yörünge tamponu; enjekte edilen monoton saatle oynatma                                                                      |
| `include/delta_edge/watchdog.hpp` | Kalp atışı: T_stop → dur-tut (G6), T_off → tork ve mıknatıs kapalı (G7)                                                     |
| `include/delta_edge/state.hpp`    | Durumlar: IDLE, RUNNING, HOLDING, FAULT, TORQUE_OFF, ESTOP                                                                  |
| `include/delta_edge/driver.hpp`   | Sürücü arayüzü; seri hattın tek sahibi (G10). `MockDriver` (sanal Pi), `Ax12Driver` (F5)                                    |
| `include/delta_edge/edge.hpp`     | `EdgeCore`: mesaj + tick → giden mesajlar (soket yok, test edilebilir)                                                      |
| `app/main.cpp`                    | Boost.Beast + OpenSSL istemcisi, yeniden bağlanma (üstel bekleme)                                                           |
| `config/edge.yaml`                | Kenara özgü sınırlar; eklem açı limitleri tek kaynak `config/robot.yaml`                                                    |
| `fuzz/`                           | Protokol ayrıştırıcı için libFuzzer hedefi ve tohum derlemi                                                                 |

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
