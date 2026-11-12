# Delta Robotics V2

[![Claude Code ile geliştirildi](https://img.shields.io/badge/Claude%20Code%20ile-geli%C5%9Ftirildi-D97757?logo=claude&logoColor=white)](https://claude.com/claude-code)

V2, [Claude Code](https://claude.com/claude-code) ile geliştirilmektedir: tasarım kararları ve gözden geçirme proje sahibinde, kodlama ve belgeleme Claude Code ile birlikte yapılır.

Uzaktan erişilebilir paralel delta robot deney kiti, ikinci sürüm. Kullanıcılar web sayfasından ya da VS Code'dan Python yazarak gerçek robotu (ya da onun dijital ikizini) güvenli bir çerçevede kontrol eder. Hedef senaryo: havalandırmalı bir kutudaki robotun altındaki 3B baskı tic-tac-toe tablasında taşları hücreler arasında taşımak. Erişim saatlik kiralanır.

V2 sıfırdan yazılır. Repodaki eski klasörler (`LikeSoup/`, `KilavuzDeltaRobotics/`, `ImageProcessing/`, `WsAnalysis/`) 2024 bitirme projesinin değiştirilmeyen referansıdır; V2 bu klasörlerin hiçbirine dokunmaz ve onlardan kod almaz. Robotun mekaniği V1 ile birebir aynıdır.

## Durum

| Faz  | Kapsam                                                    | Durum      |
| ---- | --------------------------------------------------------- | ---------- |
| F0   | İskele, Docker geliştirme ortamı, Compose, i18n, CI       | Tamamlandı |
| F0.5 | FreeCAD ile parametrik 3B model, montaj, renkli görseller | Tamamlandı |
| F1   | C++ kinematik çekirdeği + testler + Python bağlaması      | Tamamlandı |
| F2   | Datasheet (etkileşimli HTML)                              | Tamamlandı |
| F3   | ROS2 + güvenlik süpervizörü + dijital ikiz                | Tamamlandı |
| F4   | Uzaktan erişim: API, Python istemcisi, web, sandbox       | Kod tamam  |
| F4.5 | Tic-tac-toe senaryosu (simülasyon)                        | Kod tamam  |
| F5   | Yeniden kurulum (yazılım yarısı, sonra askıda)            | —          |
| F6   | Tek sayfalık deneyim arayüzü (simülasyon)                 | Sürüyor    |

Ayrıntı: [docs/yol-haritasi.md](docs/yol-haritasi.md)

## Klasör haritası

```
DeltaRobotV2/
  README.md           Bu dosya
  compose.yaml        Konteyner servisleri: dev; sim profili (certs, server, edge)
  docker/dev/         Geliştirme imajı: Ubuntu 24.04 + ROS2 Jazzy + C++/Python araçları
  docker/ros/         Sunucu imajı (ROS2 yığını)
  docker/edge/        Sanal Pi imajı (gerçek Pi ile aynı delta_edge ikilisi)
  config/robot.yaml   Robot tanımı: tek ölçü kaynağı (mm, derece)
  cad/                FreeCAD betikleri, montaj, mesh ve kütle çıktıları
  core/               delta_core: ROS'tan bağımsız C++ kinematik çekirdeği + Python bağlaması
  edge/               delta_edge: Pi kenar servisi (C++17, ROS'suz): son kapı, bekçi, oynatıcı
  ros2_ws/            ROS2 paketleri: arayüzler, URDF, sunucu düğümleri, edge_bridge, tabla ikizi
  api/                Komut API'si (FastAPI): REST + WebSocket, iş kuyruğu; sözleşme docs/api.md
  client/             Python istemcisi (pip: delta-robot-client), VS Code'dan kullanım
  web/                Türkçe web arayüzü: editör, 3B ikiz, telemetri
  sandbox/            Kullanıcı kodu koşucusu ve G11 güvenlik testleri
  i18n/locales/       Arayüz metinleri; tr.json kaynak, en.json çeviri
  hardware/           Malzeme listesi: bom.yaml (kaynak) -> bom.csv, bom.md (CAD ile senkron)
  tools/              ci.sh, format.sh, cad.sh, bom.py, i18n denetimi, git kancaları
  tests/              Python testleri (pytest) ve uçtan uca senaryolar (tests/e2e)
  docs/               Mimari, yol haritası, robot girdileri, geliştirme ortamı
```

Alt klasörler yalnız gerektiği fazda açılır.

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
- [docs/gelistirme-ortami.md](docs/gelistirme-ortami.md): Docker, Compose, CI, kod standardı
- [docs/datasheet/datasheet.html](docs/datasheet/datasheet.html): etkileşimli datasheet
- [docs/ilerleme.md](docs/ilerleme.md): faz ilerlemesi, sayılarla
- [docs/guvenlik-gereksinimleri.md](docs/guvenlik-gereksinimleri.md): güvenlik gereksinimleri ve testleri
- [docs/kabul-testleri.md](docs/kabul-testleri.md): donanım kabul testleri (F5)
- [hardware/bom.md](hardware/bom.md): malzeme listesi (BOM)
- [docs/kurulum-plani.md](docs/kurulum-plani.md): robot üretilecekse üretim ve kurulum sırası

Belgeler Türkçedir. Arayüz önce Türkçe, sonra İngilizce desteklenir.
