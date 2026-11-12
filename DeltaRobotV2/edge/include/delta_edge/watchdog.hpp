// Kalp atışı bekçisi (G6, G7). Son geçerli kalp atışından beri geçen süreye göre seviye verir.
// Algılama döngü adımında yapıldığından eşikler bir döngü periyodu (guard) erken tutulur: döngü
// zamanında çalıştıkça dur-tut en geç T_stop, tork kapatma en geç T_off anında verilir.
#pragma once

#include <cstdint>

#include "delta_edge/types.hpp"

namespace delta_edge {

enum class WatchdogLevel { kOk, kHold, kOff };

class Watchdog {
 public:
  Watchdog(int t_stop_ms, int t_off_ms, Micros guard_us);

  // Kalp atışı. Oturum içinde seq kesin artmalı; tekrar ya da eski seq yok sayılır (false).
  bool feed(std::uint64_t seq, Micros now);
  // Yeni bağlantı: seq sayacı sıfırlanır, zaman sıfırlanmaz (bağlanmak kalp atışı değildir).
  void new_session();
  // Hiç kalp atışı gelmediyse kOff.
  WatchdogLevel level(Micros now) const;

  Micros hold_after_us() const { return hold_after_; }
  Micros off_after_us() const { return off_after_; }

 private:
  Micros hold_after_;
  Micros off_after_;
  Micros last_{0};
  bool fed_{false};
  bool seq_valid_{false};
  std::uint64_t last_seq_{0};
};

}  // namespace delta_edge
