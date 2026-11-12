// EdgeCore: kenarın tüm kararı. Ağ yok; mesaj metni ve saat dışarıdan gelir, giden mesajlar metin
// olarak döner. tick() tick_hz ile, on_message() gelen her çerçevede çağrılır (tek iş parçacığı).
#pragma once

#include <string>
#include <string_view>
#include <vector>

#include "delta_edge/config.hpp"
#include "delta_edge/driver.hpp"
#include "delta_edge/gate.hpp"
#include "delta_edge/player.hpp"
#include "delta_edge/protocol.hpp"
#include "delta_edge/state.hpp"
#include "delta_edge/watchdog.hpp"

namespace delta_edge {

class EdgeCore {
 public:
  // Açılışta tork ve mıknatıs kapatılır; durum TORQUE_OFF.
  EdgeCore(const EdgeLimits& limits, Driver& driver, EstopInput& estop, Micros now);

  std::vector<std::string> on_message(std::string_view text, Micros now);
  std::vector<std::string> tick(Micros now);

  void on_connection_open();  // yeni oturum: heartbeat seq sıfırlanır
  void shutdown();            // servis kapanırken: mıknatıs ve tork kapalı

  State state() const { return state_; }
  const Gate& gate() const { return gate_; }
  const Watchdog& watchdog() const { return watchdog_; }
  const Angles& last_command() const { return last_cmd_; }
  const Angles& hold_target() const { return hold_target_; }

 private:
  using Out = std::vector<std::string>;

  void handle(const TrajectoryMsg& m, Micros now, Out& out);
  void handle(const TorqueMsg& m, Micros now, Out& out);
  void handle(const MagnetMsg& m, Out& out);
  void handle_reset(Micros now, Out& out);
  // Komut kabulü için ortak ön koşul: taze kalp atışı, acil stop yok, sağlık iyi.
  bool ready_for_motion(Micros now, Out& out);

  void enter_hold(State next);  // yörüngeyi kes, ölçülen konumu tutma hedefi yap
  void enter_torque_off();
  void enter_estop(Out& out);
  std::string telemetry() const;

  EdgeLimits limits_;
  Gate gate_;
  Watchdog watchdog_;
  Player player_;
  Driver& driver_;
  EstopInput& estop_;
  State state_{State::kTorqueOff};
  DriverState measured_{};
  Angles last_cmd_{};     // servolara giden son hedef, deg
  Angles hold_target_{};  // tutma hedefi, deg
  std::string traj_id_;   // son yörünge kimliği (telemetri)
  long long index_{-1};
  Micros last_tick_;
  Micros next_telemetry_;
};

}  // namespace delta_edge
