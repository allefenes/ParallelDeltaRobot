// Donanım bekçisi için yaşam darbesi (G13).
//
// Kenar döngüsü her tick'ini tamamladıkça çıkış ters çevrilir (100 Hz döngüde 50 Hz kare dalga).
// Döngü takılırsa, süreç ölürse ya da çekirdek donarsa darbe kendiliğinden durur; servo güç
// yolundaki yeniden tetiklenebilir monostable (74HC123, ≈0.5 s, varsayım) o zaman 12 V servo
// gücünü keser. Darbe yalnız sağlıklı döngünün yan ürünüdür; yazılım "çökmüş" hâlde üretemez.
#pragma once

#include <cstdint>

#include "delta_edge/types.hpp"

namespace delta_edge {

// Fiziksel çıkış: gerçek Pi'de GPIO (F5), sanal Pi'de dosya/sayaç, testte sahte.
class PulseOutput {
 public:
  virtual ~PulseOutput() = default;
  virtual void write(bool level) = 0;
};

class LifePulse {
 public:
  explicit LifePulse(PulseOutput& out) : out_(out) {}

  // Döngü tick'i başarıyla bittiğinde çağrılır.
  void on_tick_completed() {
    level_ = !level_;
    out_.write(level_);
    ++edges_;
  }
  std::uint64_t edges() const { return edges_; }

 private:
  PulseOutput& out_;
  bool level_{false};
  std::uint64_t edges_{0};
};

}  // namespace delta_edge
