// Sahte sürücü dinamiği. Birimler: deg, deg/s, s, °C, V, %.
#include "delta_edge/mock_driver.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace delta_edge {
namespace {
constexpr double kStepS = 0.001;   // tümleme adımı, s
constexpr double kMaxGapS = 10.0;  // tek seferde en fazla tümlenen süre, s
}  // namespace

MockDriver::MockDriver(Clock clock) : MockDriver(std::move(clock), Params{}) {}

MockDriver::MockDriver(Clock clock, Params params)
    : clock_(std::move(clock)), p_(params), last_(clock_()) {
  pos_ = p_.initial;
  goal_ = p_.initial;
  temps_.fill(p_.ambient_c);
  loads_.fill(0.0);
  min_goal_.fill(std::numeric_limits<double>::infinity());
  max_goal_.fill(-std::numeric_limits<double>::infinity());
}

void MockDriver::advance() {
  const Micros now = clock_();
  double dt = static_cast<double>(now - last_) / static_cast<double>(kMicrosPerSecond);
  last_ = now;
  if (!(dt > 0.0)) return;
  dt = std::min(dt, kMaxGapS);
  while (dt > 0.0) {
    const double h = std::min(dt, kStepS);
    step(h);
    dt -= h;
  }
}

void MockDriver::step(double h) {
  for (int j = 0; j < 3; ++j) {
    double vel = 0.0;
    if (torque_) {
      // Birinci dereceden konum döngüsü, hız doyumu (AX-12A yüksüz hızı).
      vel = std::clamp((goal_[j] - pos_[j]) / p_.tau_s, -p_.max_speed_dps, p_.max_speed_dps);
    }
    pos_[j] += vel * h;
    // Yük: tutma için %10 + hızla doğrusal artış (kaba model); tork kapalıyken 0.
    loads_[j] = torque_ ? std::copysign(10.0 + 80.0 * std::abs(vel) / p_.max_speed_dps, vel) : 0.0;
    const double t_ss = p_.ambient_c + p_.temp_per_load * std::abs(loads_[j]);
    temps_[j] += (t_ss - temps_[j]) * h / p_.temp_tau_s;
  }
}

void MockDriver::set_goal(const Angles& angles_deg) {
  advance();
  goal_ = angles_deg;
  ++goal_count_;
  for (int j = 0; j < 3; ++j) {
    min_goal_[j] = std::min(min_goal_[j], angles_deg[j]);
    max_goal_[j] = std::max(max_goal_[j], angles_deg[j]);
  }
}

DriverState MockDriver::read_state() {
  advance();
  DriverState s;
  s.ok = read_ok_;
  s.angles = pos_;
  s.temps_c = temps_;
  s.loads_pct = loads_;
  s.voltages_v.fill(inj_voltage_.value_or(p_.supply_v));
  for (int j = 0; j < 3; ++j) {
    if (inj_temp_[j]) s.temps_c[j] = *inj_temp_[j];
    if (inj_load_[j]) s.loads_pct[j] = *inj_load_[j];
  }
  return s;
}

void MockDriver::set_torque(bool on) {
  advance();
  torque_ = on;
}

void MockDriver::set_magnet(bool on) { magnet_ = on; }

void MockDriver::inject_temperature(int servo, double celsius) { inj_temp_[servo] = celsius; }
void MockDriver::inject_load(int servo, double pct) { inj_load_[servo] = pct; }
void MockDriver::inject_voltage(double volts) { inj_voltage_ = volts; }
void MockDriver::set_read_ok(bool ok) { read_ok_ = ok; }

void MockDriver::clear_injections() {
  for (int j = 0; j < 3; ++j) {
    inj_temp_[j].reset();
    inj_load_[j].reset();
  }
  inj_voltage_.reset();
  read_ok_ = true;
}

}  // namespace delta_edge
