// Test yardımcıları: mesaj üreticileri, düzgün yörünge, giden mesaj ayrıştırma.
#pragma once

#include <cmath>
#include <nlohmann/json.hpp>
#include <optional>
#include <string>
#include <vector>

#include "delta_edge/types.hpp"

namespace delta_edge::test {

using nlohmann::json;

inline std::string traj_msg(const std::string& id, int period_ms, const std::vector<Angles>& pts,
                            std::optional<bool> magnet = std::nullopt) {
  json j = {{"v", 1}, {"type", "trajectory"}, {"id", id}, {"period_ms", period_ms}};
  j["points"] = json::array();
  for (const auto& p : pts) j["points"].push_back({p[0], p[1], p[2]});
  if (magnet) j["magnet"] = *magnet;
  return j.dump();
}

inline std::string hb_msg(std::uint64_t seq) {
  return json({{"v", 1}, {"type", "heartbeat"}, {"seq", seq}}).dump();
}

inline std::string simple_msg(const std::string& type) {
  return json({{"v", 1}, {"type", type}}).dump();
}

inline std::string on_msg(const std::string& type, bool on) {
  return json({{"v", 1}, {"type", type}, {"on", on}}).dump();
}

// Kosinüs profili: from -> to, süre duration_ms, period_ms aralıklı. Uçlarda hız sıfır.
// Tepe hız = Δ·π/(2T), tepe ivme = Δ·π²/(2T²).
inline std::vector<Angles> smooth(const Angles& from, const Angles& to, int duration_ms,
                                  int period_ms) {
  const double kPi = 3.14159265358979323846;
  std::vector<Angles> pts;
  const int n = duration_ms / period_ms;
  for (int k = 0; k <= n; ++k) {
    const double s = 0.5 * (1.0 - std::cos(kPi * k / n));
    Angles p{};
    for (int j = 0; j < 3; ++j) p[j] = from[j] + (to[j] - from[j]) * s;
    pts.push_back(p);
  }
  return pts;
}

// Giden mesajlar içinde ilk `type` (ve varsa `code`) eşleşmesi.
inline std::optional<json> find_msg(const std::vector<std::string>& out, const std::string& type,
                                    const std::string& code = "") {
  for (const auto& s : out) {
    const json j = json::parse(s);
    if (j.at("type") == type && (code.empty() || j.at("code") == code)) return j;
  }
  return std::nullopt;
}

inline int count_type(const std::vector<std::string>& out, const std::string& type) {
  int n = 0;
  for (const auto& s : out) n += json::parse(s).at("type") == type ? 1 : 0;
  return n;
}

}  // namespace delta_edge::test
