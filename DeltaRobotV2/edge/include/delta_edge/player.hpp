// Yörünge tamponu ve oynatıcı. Noktalar yerel monoton saatle period_ms aralığında oynatılır;
// iki nokta arası doğrusal ara değerlenir. Ağ gecikmesi hareketi etkilemez.
#pragma once

#include <cstddef>
#include <string>
#include <vector>

#include "delta_edge/types.hpp"

namespace delta_edge {

class Player {
 public:
  struct Sample {
    Angles command{};      // deg
    std::size_t index{0};  // içinde bulunulan aralığın başlangıç noktası
    bool finished{false};  // son noktaya varıldı
  };

  void start(std::string id, std::vector<Angles> points, int period_ms, Micros now);
  void clear();
  bool active() const { return !points_.empty(); }
  // Ön koşul: active(). now başlangıçtan önceyse ilk nokta.
  Sample sample(Micros now) const;
  const std::string& id() const { return id_; }
  std::size_t size() const { return points_.size(); }

 private:
  std::string id_;
  std::vector<Angles> points_;
  Micros period_us_{0};
  Micros start_{0};
};

}  // namespace delta_edge
