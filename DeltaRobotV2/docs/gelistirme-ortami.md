# Geliştirme ortamı

Bütün derleme ve testler Docker konteynerinde çalışır. Böylece Windows (Docker Desktop + WSL 2), Linux ve CI aynı ortamı kullanır.

## Gereksinimler

- Docker Desktop, WSL 2 arka ucuyla (ya da Linux'ta Docker Engine)
- Docker Compose v2

## İmaj

`docker/dev/Dockerfile`, `ros:jazzy-ros-base` (Ubuntu 24.04 + ROS2 Jazzy) üzerine şunları ekler: CMake, Ninja, GoogleTest, pytest, clang-format, Node.js + Prettier, ruff. Konteynerde varsayılan kullanıcı `ubuntu` (UID 1000), çalışma dizini `/workspace`, yani `DeltaRobotV2/` klasörü.

## Komutlar

`DeltaRobotV2/` içinde:

| İş                           | Komut                                           |
| ---------------------------- | ----------------------------------------------- |
| İmajı derle                  | `docker compose build dev`                      |
| Tüm denetimler (CI ile aynı) | `docker compose run --rm dev ./tools/ci.sh`     |
| Etkileşimli kabuk            | `docker compose run --rm dev bash`              |
| Biçimlendir                  | `docker compose run --rm dev ./tools/format.sh` |

`tools/ci.sh` sırasıyla şunları yapar:

1. Biçim denetimi (`tools/format.sh --check`)
2. Malzeme listesinin CAD ile senkronunu denetler (`tools/bom.py --check`)
3. i18n kataloglarını denetler (`tools/check_i18n.py`)
4. Python testlerini çalıştırır (`tests/`)
5. `core/` C++ kütüphanesini derler ve testlerini çalıştırır (`build/core/`)

## Kod standardı

Kod, incelemesi kolay olsun diye her zaman otomatik biçimlendirilir:

| Dil                                  | Araç                                   | Ayar dosyası       |
| ------------------------------------ | -------------------------------------- | ------------------ |
| JSON, YAML, Markdown (ileride JS/TS) | Prettier 3.3.3                         | `.prettierrc.yaml` |
| C++                                  | clang-format (Google stili, 100 sütun) | `.clang-format`    |
| Python                               | ruff 0.6.9 (format: black stili; lint) | `pyproject.toml`   |

Belgeleme kodun içinde, kısa ve açık yorumlarla yapılır: her modülün, sınıfın ve fonksiyonun ne yaptığı, birimler (mm, derece, radyan), koordinat sistemleri ve varsayımlar. Kodun zaten söylediğini tekrarlayan yorum yazılmaz. Yorum dili Türkçedir.

### Pre-commit kancası

Repo kökünde bir kez çalıştırın:

```bash
git config core.hooksPath DeltaRobotV2/tools/git-hooks
```

Bundan sonra `DeltaRobotV2/` altında değişiklik içeren her commit'te biçim denetimi konteynerde çalışır; biçimsiz dosya varsa commit durur. Docker Desktop açık olmalıdır.

## Notlar

- Kaynak Windows diskinden bağlandığında derleme yavaş olabilir. Ağır derlemeler için çıktılar `build/` altına yazılır ve git tarafından yok sayılır.
- `.gitattributes` bu klasördeki metin dosyalarını LF satır sonuyla tutar; konteynerdeki betikler bu yüzden Windows'ta da çalışır.

## CI

İş akışı repo kökünde `.github/workflows/deltarobotv2.yml` dosyasındadır (V2 klasörü dışındaki tek dosya; proje sahibi onayladı). Yalnız `DeltaRobotV2/**` ya da iş akışı dosyası değiştiğinde tetiklenir, geliştirme imajını derler ve içinde `tools/ci.sh` çalıştırır; yani yerel denetimle birebir aynıdır.
