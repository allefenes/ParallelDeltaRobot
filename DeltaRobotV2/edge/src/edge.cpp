// EdgeCore: durum makinesi, kapı, bekçi ve oynatıcıyı bağlar. Geçiş tablosu README.md'de.
//
// Mıknatısın güvenli durumu KAPALI (G7). Gerekçe: elektromıknatıs enerjisi kesilince bırakır;
// fiziksel acil stop ya da güç kaybında da zaten bırakacaktır. Yazılımın güvenli durumu bunu
// izlerse her arıza yolunda davranış aynı ve öngörülebilir olur. Denetimsiz açık kalan bobin
// ısınır ve parçayı kimsenin kontrol etmediği bir konumda tutar. Bedel: tutulan parça düşer;
// çalışma alanı alçak ve parçalar hafif olduğundan kabul edilir (F5'te risk analizinde gözden
// geçirilir).
#include "delta_edge/edge.hpp"

#include <cmath>

#include "delta_edge/faults.hpp"

namespace delta_edge {

EdgeCore::EdgeCore(const EdgeLimits& limits, Driver& driver, EstopInput& estop, Micros now)
    : limits_(limits),
      gate_(limits),
      watchdog_(limits.t_stop_ms, limits.t_off_ms, limits.tick_period_us()),
      driver_(driver),
      estop_(estop),
      last_tick_(now),
      next_telemetry_(now) {
  set_magnet(false);
  driver_.set_torque(false);
  measured_ = driver_.read_state();
  last_cmd_ = hold_target_ = gate_.clamp_to_limits(measured_.angles);
}

void EdgeCore::on_connection_open() { watchdog_.new_session(); }

void EdgeCore::shutdown() {
  player_.clear();
  set_magnet(false);
  driver_.set_torque(false);
  if (state_ != State::kEstop) state_ = State::kTorqueOff;
}

void EdgeCore::enter_hold(State next) {
  player_.clear();
  // Hareketin ortasında bile ölçülen konumda dondur (G6). Sonlu olmayan eklem son komutta kalır.
  Angles target = gate_.clamp_to_limits(measured_.angles);
  for (int j = 0; j < 3; ++j) {
    if (!std::isfinite(target[j])) target[j] = last_cmd_[j];
  }
  hold_target_ = target;
  state_ = next;
}

void EdgeCore::enter_torque_off() {
  player_.clear();
  set_magnet(false);
  driver_.set_torque(false);
  state_ = State::kTorqueOff;
}

void EdgeCore::enter_estop(Out& out) {
  player_.clear();
  set_magnet(false);
  driver_.set_torque(false);
  state_ = State::kEstop;
  out.push_back(serialize_fault(fault::kEstop, "acil stop girişi etkin; mandallandı"));
}

std::vector<std::string> EdgeCore::tick(Micros now) {
  Out out;
  const double dt_s = static_cast<double>(now - last_tick_) / static_cast<double>(kMicrosPerSecond);
  last_tick_ = now;
  measured_ = driver_.read_state();

  // 1) Acil stop: en yüksek öncelik, mandallı.
  if (state_ != State::kEstop && estop_.active()) enter_estop(out);

  if (state_ != State::kEstop) {
    // 2) Sağlık (G9): tork açıkken sınır aşılırsa dur, tut, bildir.
    if (torque_enabled(state_) && state_ != State::kFault) {
      const GateResult h = gate_.check_health(measured_);
      if (!h.ok) {
        enter_hold(State::kFault);
        out.push_back(serialize_fault(h.code, h.detail));
      }
    }
    // 3) Bekçi (G6, G7).
    const WatchdogLevel w = watchdog_.level(now);
    if (w == WatchdogLevel::kOff && torque_enabled(state_)) {
      enter_torque_off();
      out.push_back(serialize_fault(fault::kHeartbeatOff,
                                    "kalp atışı T_off=" + std::to_string(limits_.t_off_ms) +
                                        " ms gelmedi; tork ve mıknatıs kapatıldı"));
    } else if (w == WatchdogLevel::kHold && (state_ == State::kIdle || state_ == State::kRunning)) {
      enter_hold(State::kHolding);
      out.push_back(serialize_fault(fault::kHeartbeatHold,
                                    "kalp atışı T_stop=" + std::to_string(limits_.t_stop_ms) +
                                        " ms gelmedi; konum tutuluyor"));
    }
    // 4) Komut: yörünge örneği ya da tutma hedefi, son kapıdan geçerek (kırpma).
    if (torque_enabled(state_)) {
      Angles target = hold_target_;
      if (state_ == State::kRunning) {
        const Player::Sample s = player_.sample(now);
        target = s.command;
        index_ = static_cast<long long>(s.index);
        if (s.finished) {
          hold_target_ = s.command;
          player_.clear();
          state_ = State::kIdle;
        }
      }
      if (const auto cmd = gate_.clamp_command(last_cmd_, target, dt_s)) {
        last_cmd_ = *cmd;
        driver_.set_goal(*cmd);
      }
    }
  }

  // 5) Telemetri.
  if (now >= next_telemetry_) {
    out.push_back(telemetry());
    next_telemetry_ = now + static_cast<Micros>(limits_.telemetry_period_ms) * kMicrosPerMs;
  }
  return out;
}

std::vector<std::string> EdgeCore::on_message(std::string_view text, Micros now) {
  Out out;
  const ParseResult r = parse_server_message(text);
  if (!r.ok()) {
    out.push_back(serialize_fault(fault::kParseError, r.error));
    return out;
  }
  const ServerMessage& m = *r.message;
  if (const auto* hb = std::get_if<HeartbeatMsg>(&m)) {
    watchdog_.feed(hb->seq, now);
  } else if (const auto* t = std::get_if<TrajectoryMsg>(&m)) {
    handle(*t, now, out);
  } else if (std::holds_alternative<StopMsg>(m)) {
    if (state_ == State::kRunning) enter_hold(State::kIdle);
  } else if (std::holds_alternative<HoldMsg>(m)) {
    if (state_ == State::kIdle || state_ == State::kRunning) enter_hold(State::kHolding);
  } else if (const auto* tq = std::get_if<TorqueMsg>(&m)) {
    handle(*tq, now, out);
  } else if (const auto* mg = std::get_if<MagnetMsg>(&m)) {
    handle(*mg, out);
  } else {
    handle_reset(now, out);
  }
  return out;
}

bool EdgeCore::ready_for_motion(Micros now, Out& out) {
  if (watchdog_.level(now) != WatchdogLevel::kOk) {
    out.push_back(serialize_fault(fault::kHeartbeatRequired, "taze kalp atışı yok"));
    return false;
  }
  if (estop_.active()) {
    out.push_back(serialize_fault(fault::kEstop, "acil stop girişi etkin"));
    return false;
  }
  measured_ = driver_.read_state();
  const GateResult h = gate_.check_health(measured_);
  if (!h.ok) {
    out.push_back(serialize_fault(h.code, h.detail));
    return false;
  }
  return true;
}

void EdgeCore::handle(const TrajectoryMsg& m, Micros now, Out& out) {
  if (state_ != State::kIdle) {
    out.push_back(serialize_fault(fault::kNotReady, "yörünge " + m.id +
                                                        " reddedildi: yalnız IDLE durumunda "
                                                        "kabul edilir, durum " +
                                                        state_name(state_)));
    return;
  }
  if (!ready_for_motion(now, out)) return;
  // Son kapı: yörünge bütünüyle doğrulanmadan hiçbir noktası oynatılmaz (G8).
  const GateResult g = gate_.validate_trajectory(measured_.angles, m.points, m.period_ms);
  if (!g.ok) {
    out.push_back(serialize_fault(g.code, "yörünge " + m.id + " reddedildi: " + g.detail));
    return;
  }
  if (m.magnet) set_magnet(*m.magnet);
  player_.start(m.id, m.points, m.period_ms, now);
  traj_id_ = m.id;
  index_ = 0;
  state_ = State::kRunning;
  out.push_back(serialize_ack(m.id));
}

void EdgeCore::handle(const TorqueMsg& m, Micros now, Out& out) {
  if (!m.on) {
    if (state_ != State::kEstop) enter_torque_off();
    return;
  }
  if (state_ == State::kEstop || state_ == State::kFault) {
    out.push_back(serialize_fault(
        fault::kNotReady,
        std::string("torque on reddedildi: önce reset, durum ") + state_name(state_)));
    return;
  }
  if (state_ != State::kTorqueOff && state_ != State::kHolding) return;  // zaten çalışıyor
  // Kurtarma kuralı: taze kalp atışı VE açık torque on komutu.
  if (!ready_for_motion(now, out)) return;
  if (state_ == State::kTorqueOff) {
    // Tork açılmadan önce hedef = ölçülen konum: servo eski hedefe sıçramaz.
    hold_target_ = last_cmd_ = gate_.clamp_to_limits(measured_.angles);
    driver_.set_goal(last_cmd_);
    driver_.set_torque(true);
  }
  state_ = State::kIdle;
}

void EdgeCore::handle(const MagnetMsg& m, Out& out) {
  if (!m.on) {
    set_magnet(false);
    return;
  }
  if (state_ == State::kIdle || state_ == State::kRunning || state_ == State::kHolding) {
    set_magnet(true);
    return;
  }
  out.push_back(serialize_fault(fault::kNotReady,
                                std::string("magnet on reddedildi: durum ") + state_name(state_)));
}

void EdgeCore::handle_reset(Micros now, Out& out) {
  if (state_ == State::kEstop) {
    if (estop_.active()) {
      out.push_back(serialize_fault(fault::kEstop, "reset reddedildi: acil stop hâlâ etkin"));
      return;
    }
    state_ = State::kTorqueOff;  // tork kapalı kalır; devam için torque on gerekir
    return;
  }
  if (state_ == State::kFault) {
    if (!ready_for_motion(now, out)) return;
    state_ = State::kIdle;  // tutma hedefi korunur
  }
}

// Mıknatıs yalnız buradan sürülür; telemetri sürücüye yazılan son değeri bildirir.
void EdgeCore::set_magnet(bool on) {
  magnet_ = on;
  driver_.set_magnet(on);
}

std::string EdgeCore::telemetry() const {
  Telemetry t;
  t.state = state_name(state_);
  t.angles = measured_.angles;
  t.temps_c = measured_.temps_c;
  t.loads_pct = measured_.loads_pct;
  t.voltages_v = measured_.voltages_v;
  t.traj_id = traj_id_;
  t.index = index_;
  t.magnet = magnet_;
  return serialize_telemetry(t);
}

}  // namespace delta_edge
