# Geliştirme ortamı

Bütün derleme ve testler Docker konteynerinde çalışır. Böylece Windows (Docker Desktop + WSL 2), Linux ve CI aynı ortamı kullanır.

## Gereksinimler

- Docker Desktop, WSL 2 arka ucuyla (ya da Linux'ta Docker Engine)
- Docker Compose v2

## İmaj

`docker/dev/Dockerfile`, `ros:jazzy-ros-base` (Ubuntu 24.04 + ROS2 Jazzy) üzerine şunları ekler: CMake, Ninja, GoogleTest, pytest, clang-format. Konteynerde varsayılan kullanıcı `ubuntu` (UID 1000), çalışma dizini `/workspace`, yani `DeltaRobotV2/` klasörü.

## Komutlar

`DeltaRobotV2/` içinde:

| İş | Komut |
|---|---|
| İmajı derle | `docker compose build dev` |
| Tüm denetimler (CI ile aynı) | `docker compose run --rm dev ./tools/ci.sh` |
| Etkileşimli kabuk | `docker compose run --rm dev bash` |

`tools/ci.sh` sırasıyla şunları yapar:

1. i18n kataloglarını denetler (`tools/check_i18n.py`)
2. Python testlerini çalıştırır (`tests/`)
3. `core/` C++ kütüphanesini derler ve testlerini çalıştırır (`build/core/`)

## Notlar

- Kaynak Windows diskinden bağlandığında derleme yavaş olabilir. Ağır derlemeler için çıktılar `build/` altına yazılır ve git tarafından yok sayılır.
- `.gitattributes` bu klasördeki metin dosyalarını LF satır sonuyla tutar; konteynerdeki betikler bu yüzden Windows'ta da çalışır.

## CI

GitHub Actions yalnız repo kökündeki `.github/workflows/` klasörünü okur. V2 kuralı gereği repo köküne (README dışında) dosya eklenmediği için iş akışı taslağı `ci/github-workflow.yml` olarak durur. Etkinleştirmek için kökte `.github/workflows/deltarobotv2.yml` olarak kopyalanması gerekir; bu adım proje sahibinin onayını bekler. İş akışı yalnız `DeltaRobotV2/**` değiştiğinde tetiklenir ve aynı imajda `tools/ci.sh` çalıştırır.
