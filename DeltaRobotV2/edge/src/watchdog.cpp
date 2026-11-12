// Kalp atışı bekçisi. Eşik modeli: include/delta_edge/watchdog.hpp
#include "delta_edge/watchdog.hpp"

namespace delta_edge {

Watchdog::Watchdog(int t_stop_ms, int t_off_ms, Micros guard_us)
    : hold_after_(static_cast<Micros>(t_stop_ms) * kMicrosPerMs - guard_us),
      off_after_(static_cast<Micros>(t_off_ms) * kMicrosPerMs - guard_us) {}

bool Watchdog::feed(std::uint64_t seq, Micros now) {
  if (seq_valid_ && seq <= last_seq_) return false;
  seq_valid_ = true;
  last_seq_ = seq;
  last_ = now;
  fed_ = true;
  return true;
}

void Watchdog::new_session() { seq_valid_ = false; }

WatchdogLevel Watchdog::level(Micros now) const {
  if (!fed_) return WatchdogLevel::kOff;
  const Micros silent = now - last_;
  if (silent >= off_after_) return WatchdogLevel::kOff;
  if (silent >= hold_after_) return WatchdogLevel::kHold;
  return WatchdogLevel::kOk;
}

}  // namespace delta_edge
