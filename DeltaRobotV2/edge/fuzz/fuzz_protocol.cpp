// libFuzzer hedefi: protokol ayrıştırıcı + EdgeCore. Değişmezler (ihlal = abort = bulgu):
//   - parse_server_message istisna fırlatmaz (noexcept; fırlatırsa std::terminate).
//   - Kabul edilen yörüngede her nokta sonlu, nokta sayısı ve period_ms sınır içinde (G4).
//   - Girdi ne olursa olsun servolara hiçbir sonlu olmayan ya da eklem limiti dışı hedef gitmez
//   (G1).
// Derleme: cmake -DDELTA_EDGE_FUZZ=ON -DCMAKE_CXX_COMPILER=clang++ (bkz. README.md).
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <string_view>

#include "delta_edge/edge.hpp"
#include "delta_edge/mock_driver.hpp"

namespace {

using namespace delta_edge;

void check(bool cond) {
  if (!cond) std::abort();
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size) {
  const std::string_view text(reinterpret_cast<const char*>(data), size);

  const ParseResult r = parse_server_message(text);
  if (r.ok()) {
    if (const auto* t = std::get_if<TrajectoryMsg>(&*r.message)) {
      check(!t->points.empty() && t->points.size() <= kMaxPoints);
      check(t->period_ms >= kMinPeriodMs && t->period_ms <= kMaxPeriodMs);
      check(!t->id.empty() && t->id.size() <= kMaxIdLength);
      for (const Angles& p : t->points) {
        for (double v : p) check(std::isfinite(v));
      }
    }
  } else {
    check(!r.error.empty());
  }

  // Hazır robota girdiyi ver, birkaç döngü oynat: hedefler limit içinde ve sonlu kalmalı.
  Micros now = 0;
  MockDriver drv([&now] { return now; });
  MockEstop estop;
  const EdgeLimits lim;
  EdgeCore core(lim, drv, estop, now);
  core.on_message(R"({"v":1,"type":"heartbeat","seq":1})", now);
  core.on_message(R"({"v":1,"type":"torque","on":true})", now);
  core.on_message(text, now);
  for (int i = 0; i < 20; ++i) {
    now += 10 * kMicrosPerMs;
    core.tick(now);
  }
  if (drv.goal_count() > 0) {
    for (int j = 0; j < 3; ++j) {
      check(std::isfinite(drv.min_goal()[j]) && std::isfinite(drv.max_goal()[j]));
      check(drv.min_goal()[j] >= lim.joint_min_deg && drv.max_goal()[j] <= lim.joint_max_deg);
    }
  }
  return 0;
}
