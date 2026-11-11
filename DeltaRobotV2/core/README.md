# delta_core

ROS'tan bağımsız C++17 kinematik çekirdeği. Sunucu (1. güvenlik kapısı, yörünge planlama), Pi kenarı (son kapı), Python istemcisi ve web ikizi aynı kodu kullanır.

| Dosya                               | Görev                                                                        |
| ----------------------------------- | ---------------------------------------------------------------------------- |
| `include/delta_core/kinematics.hpp` | İleri/ters kinematik, Jacobian, koşul sayısı, rot başı açısı, limit kontrolü |
| `include/delta_core/params.hpp`     | Geometri ve limitler; `config/robot.yaml` okuyucu                            |
| `include/delta_core/vec3.hpp`       | Bağımlılıksız 3B vektör / 3x3 matris                                         |
| `python/bindings.cpp`               | `delta_core_py` Python modülü (pybind11)                                     |
| `tests/*.cpp`                       | GoogleTest birim testleri                                                    |
| `tests/python/`                     | Hypothesis özellik tabanlı testleri ve V1 çapraz doğrulaması                 |
| `tests/data/v1_vectors.json`        | V1 kodundan üretilmiş referans vakalar (`tools/v1_vectors.py`)               |

Çerçeve: orijin motor eksenleri düzleminin merkezi, +Z yukarı; pozitif θ kolu indirir. V1'e göre: V2 (x, y, z) = V1 (x, −y, −z), kol sırası V2 [1, 2, 3] = V1 [1, 3, 2].

Python'dan kullanım (konteynerde, derlemeden sonra):

```python
import delta_core_py as dc
robot = dc.DeltaKinematics(dc.load_params("config/robot.yaml"))
robot.inverse((0, 0, -200))      # (θ1, θ2, θ3) derece ya da None
robot.check_point((60, 0, -140)) # (False, 0, "motor açı limiti")
```

Derleme, testler ve kapsama: `docker compose run --rm dev ./tools/ci.sh` (rapor: `build/coverage/`).
