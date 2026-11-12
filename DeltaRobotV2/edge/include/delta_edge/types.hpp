// Ortak temel tipler.
#pragma once

#include <array>
#include <cstdint>

namespace delta_edge {

// Üç motor açısı, derece. Sıra kol 1, 2, 3 (robot.yaml arm_angles sırası). Pozitif θ kolu
// AŞAĞI indirir (robot.yaml çerçevesi). Kenar kapısı yalnız eklem uzayında çalışır, IK gerekmez.
using Angles = std::array<double, 3>;

// Monoton saat, mikrosaniye. Kaynak her zaman dışarıdan verilir: serviste steady_clock,
// testlerde sahte saat. Duvar saati hiçbir karar için kullanılmaz.
using Micros = std::int64_t;

constexpr Micros kMicrosPerMs = 1000;
constexpr Micros kMicrosPerSecond = 1000000;

}  // namespace delta_edge
