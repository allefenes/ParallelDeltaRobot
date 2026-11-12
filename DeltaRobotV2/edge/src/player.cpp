// Yörünge oynatıcı: yerel monoton saat, doğrusal ara değerleme.
#include "delta_edge/player.hpp"

namespace delta_edge {

void Player::start(std::string id, std::vector<Angles> points, int period_ms, Micros now) {
  id_ = std::move(id);
  points_ = std::move(points);
  period_us_ = static_cast<Micros>(period_ms) * kMicrosPerMs;
  start_ = now;
}

void Player::clear() {
  points_.clear();
  id_.clear();
}

Player::Sample Player::sample(Micros now) const {
  const Micros elapsed = now > start_ ? now - start_ : 0;
  const std::size_t last = points_.size() - 1;
  const auto k = static_cast<std::size_t>(elapsed / period_us_);
  if (k >= last) return {points_[last], last, true};
  // Aralık içi oran [0, 1): k. noktadan k+1'e doğrusal.
  const double f = static_cast<double>(elapsed - static_cast<Micros>(k) * period_us_) /
                   static_cast<double>(period_us_);
  Sample s;
  s.index = k;
  for (int j = 0; j < 3; ++j) {
    s.command[j] = points_[k][j] + (points_[k + 1][j] - points_[k][j]) * f;
  }
  return s;
}

}  // namespace delta_edge
