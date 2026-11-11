# Delta Robotics V2

Uzaktan erişilebilir paralel delta robot deney kiti, ikinci sürüm. Kullanıcılar web sayfasından ya da VS Code'dan Python yazarak gerçek robotu (ya da onun dijital ikizini) güvenli bir çerçevede kontrol eder. Hedef senaryo: havalandırmalı bir kutudaki robotun altındaki 3B baskı tic-tac-toe tablasında taşları hücreler arasında taşımak. Erişim saatlik kiralanır.

V2 sıfırdan yazılır. Repodaki eski klasörler (`LikeSoup/`, `KilavuzDeltaRobotics/`, `ImageProcessing/`, `WsAnalysis/`) 2024 bitirme projesinin değiştirilmeyen referansıdır; V2 bu klasörlerin hiçbirine dokunmaz ve onlardan kod almaz. Robotun mekaniği V1 ile birebir aynıdır.

## Durum

| Faz | Kapsam | Durum |
|---|---|---|
| F0 | İskele, Docker geliştirme ortamı, Compose, i18n, CI | Tamamlandı |
| F0.5 | FreeCAD ile parametrik 3B model, montaj, renkli görseller | Sırada (onay bekliyor) |
| F1 | C++ kinematik çekirdeği + testler + Python bağlaması | — |
| F2 | Datasheet | — |
| F3 | ROS2 + güvenlik süpervizörü + dijital ikiz | — |
| F4 | Uzaktan erişim: API, Python istemcisi, web, sandbox | — |
| F4.5 | Tic-tac-toe senaryosu | — |
| F5 | Robotun yeniden kurulumu | — |
| F6 | Saatlik kiralama | — |

Ayrıntı: [docs/yol-haritasi.md](docs/yol-haritasi.md)

## Klasör haritası

```
DeltaRobotV2/
  README.md           Bu dosya
  compose.yaml        Konteyner servisleri (şimdilik: dev)
  docker/dev/         Geliştirme imajı: Ubuntu 24.04 + ROS2 Jazzy + C++/Python araçları
  core/               delta_core: ROS'tan bağımsız C++ çekirdek kütüphane (F1'de dolacak)
  i18n/locales/       Arayüz metinleri; tr.json kaynak, en.json çeviri
  tools/              ci.sh ve yardımcı betikler
  tests/              Python testleri (pytest)
  ci/                 GitHub Actions iş akışı taslağı
  docs/               Mimari, yol haritası, robot girdileri, geliştirme ortamı
```

Alt klasörler yalnız gerektiği fazda açılır (`cad/` F0.5'te, `ros2_ws/` F3'te, `api/` ve `web/` F4'te).

## Hızlı başlangıç

Docker Desktop (WSL 2 arka ucu) gerekir. `DeltaRobotV2/` içinde:

```bash
docker compose build dev
```

```bash
docker compose run --rm dev ./tools/ci.sh
```

```bash
docker compose run --rm dev bash
```

Ayrıntı: [docs/gelistirme-ortami.md](docs/gelistirme-ortami.md)

## Belgeler

- [docs/mimari.md](docs/mimari.md): sistem mimarisi ve güvenlik ilkeleri
- [docs/yol-haritasi.md](docs/yol-haritasi.md): fazlar ve teslimler
- [docs/robot-girdileri.md](docs/robot-girdileri.md): robotun ölçüleri ve mekanik bilgileri, kaynaklarıyla
- [docs/gelistirme-ortami.md](docs/gelistirme-ortami.md): Docker, Compose, CI

Belgeler Türkçedir. Arayüz önce Türkçe, sonra İngilizce desteklenir.
