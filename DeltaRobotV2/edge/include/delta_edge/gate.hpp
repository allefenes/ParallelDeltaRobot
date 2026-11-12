// SON güvenlik kapısı (2. kapı). Sunucu ne gönderirse göndersin servolara giden her değer buradan
// geçer. Eklem uzayında çalışır (deg); çalışma alanı ve çarpışma 1. kapının (sunucu) işidir.
#pragma once

#include <optional>
#include <string>
#include <vector>

#include "delta_edge/config.hpp"
#include "delta_edge/driver.hpp"
#include "delta_edge/types.hpp"

namespace delta_edge {

struct GateResult {
  bool ok{true};
  std::string code;    // faults.hpp
  std::string detail;  // insan okuyabilir neden: hangi nokta, eklem, değer, sınır
};

// Kırpmada dt bu değerle sınırlanır: döngü gecikse bile tek adım max_velocity * 50 ms'yi aşmaz.
constexpr double kMaxCommandDtS = 0.05;

class Gate {
 public:
  explicit Gate(const EdgeLimits& limits) : l_(limits) {}

  // Yörüngeyi BAŞLAMADAN önce bütünüyle doğrular (G1, G4, G5, G8). `current`: ölçülen konum.
  // Model: robot başta durgun (v=0), nokta k'ya period_ms'de varılır, son noktadan sonra durur.
  //   v_k = (p_k - p_{k-1}) / T, p_{-1} = current;  a_k = (v_k - v_{k-1}) / T;  v_n = 0.
  // İlk adımda |p_0 - current| farkından start_tolerance_deg düşülür (ölçüm gürültüsü).
  // Sınır değerleri dahildir: tam sınırdaki değer kabul edilir.
  GateResult validate_trajectory(const Angles& current, const std::vector<Angles>& points,
                                 int period_ms) const;

  // Tek nokta: sonlu mu (G4), eklem limitleri içinde mi (G1).
  GateResult check_point(const Angles& p) const;

  // Döngü başına derinlemesine savunma: hedefi eklem limitlerine ve önceki komuttan
  // max_velocity * dt adımına kırpar. Sonlu olmayan hedef, eklemi önceki komutta tutar.
  // Önceki komut sonlu değilse güvenli komut üretilemez: nullopt (hedef gönderilmez).
  std::optional<Angles> clamp_command(const Angles& previous, const Angles& target,
                                      double dt_s) const;

  // Açıları eklem limitlerine kırpar (sonlu olmayan değer olduğu gibi kalır).
  Angles clamp_to_limits(const Angles& a) const;

  // Çalışma anı izleme (G9): sürücü okuması, sıcaklık, yük, gerilim. Sınır değeri dahil kabul.
  GateResult check_health(const DriverState& s) const;

  const EdgeLimits& limits() const { return l_; }

 private:
  EdgeLimits l_;
};

}  // namespace delta_edge
