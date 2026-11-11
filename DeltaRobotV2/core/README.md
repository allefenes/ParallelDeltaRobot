# delta_core

ROS'tan bağımsız C++17 çekirdek kütüphane. F1'de ileri/ters kinematik, Jacobian, çalışma alanı ve limit kontrolü buraya eklenir; ROS2 düğümleri, Python bağlaması (pybind11) ve web ikizi aynı hesabı kullanır.

Şu an yalnız sürüm başlığı ve derleme/test hattı var.

Derleme ve test (konteynerde, `DeltaRobotV2/` içinden):

```bash
cmake -S core -B build/core -G Ninja && cmake --build build/core && ctest --test-dir build/core --output-on-failure
```
