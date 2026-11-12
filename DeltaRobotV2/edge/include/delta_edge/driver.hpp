// Motor sürücüsü ve acil stop girişi soyutlamaları.
// Seri hattın TEK sahibi Driver gerçeklemesidir (G10): EdgeCore donanıma yalnız bu arayüzle
// erişir; başka hiçbir bileşen seri porta dokunmaz (bkz. tests/test_architecture.cpp).
#pragma once

#include "delta_edge/types.hpp"

namespace delta_edge {

struct DriverState {
  bool ok{false};       // okuma başarılı mı
  Angles angles{};      // ölçülen motor açısı, deg
  Angles temps_c{};     // °C
  Angles loads_pct{};   // present load, % (işaretli: yön bilgisi)
  Angles voltages_v{};  // V
};

class Driver {
 public:
  virtual ~Driver() = default;
  virtual void set_goal(const Angles& angles_deg) = 0;
  virtual DriverState read_state() = 0;
  virtual void set_torque(bool on) = 0;
  virtual void set_magnet(bool on) = 0;
};

// Fiziksel acil stop butonunun Pi girişi (GPIO). Buton güç yolunu donanımda keser (G12);
// bu giriş yazılımın da durumu bilip mandallamasını sağlar.
class EstopInput {
 public:
  virtual ~EstopInput() = default;
  virtual bool active() = 0;
};

}  // namespace delta_edge
