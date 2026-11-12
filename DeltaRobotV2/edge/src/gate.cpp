// Son güvenlik kapısı. Tanımlar ve model: include/delta_edge/gate.hpp
#include "delta_edge/gate.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>

#include "delta_edge/faults.hpp"
#include "delta_edge/protocol.hpp"

namespace delta_edge {
namespace {

GateResult fail(const char* code, std::string detail) {
  GateResult r;
  r.ok = false;
  r.code = code;
  r.detail = std::move(detail);
  return r;
}

std::string num(double v) {
  char buf[32];
  std::snprintf(buf, sizeof(buf), "%.3f", v);
  return buf;
}

std::string joint(int j) { return "eklem " + std::to_string(j + 1); }

// İlk adımda ölçüm gürültüsü payı: |d| <= tol ise sıçrama yok sayılır, değilse tol kadar azalır.
double beyond_tolerance(double d, double tol) {
  if (std::abs(d) <= tol) return 0.0;
  return d - std::copysign(tol, d);
}

std::string step_name(std::size_t k, std::size_t n) {
  if (k == 0) return "ilk nokta (mevcut konumdan)";
  if (k == n) return "son noktada duruş";
  return "nokta " + std::to_string(k);
}

}  // namespace

GateResult Gate::check_point(const Angles& p) const {
  for (int j = 0; j < 3; ++j) {
    if (!std::isfinite(p[j])) return fail(fault::kNonFinite, joint(j) + ": sonlu olmayan değer");
  }
  for (int j = 0; j < 3; ++j) {
    if (p[j] < l_.joint_min_deg || p[j] > l_.joint_max_deg)
      return fail(fault::kJointLimit, joint(j) + ": " + num(p[j]) + " deg sınır [" +
                                          num(l_.joint_min_deg) + ", " + num(l_.joint_max_deg) +
                                          "] dışında");
  }
  return {};
}

GateResult Gate::validate_trajectory(const Angles& current, const std::vector<Angles>& points,
                                     int period_ms) const {
  if (period_ms < kMinPeriodMs || period_ms > kMaxPeriodMs)
    return fail(fault::kPeriod, "period_ms=" + std::to_string(period_ms) + " aralık dışında");
  if (points.empty()) return fail(fault::kEmpty, "nokta yok");
  if (points.size() > kMaxPoints)
    return fail(fault::kTooManyPoints, std::to_string(points.size()) + " nokta");
  for (int j = 0; j < 3; ++j) {
    if (!std::isfinite(current[j]))
      return fail(fault::kNonFinite, "ölçülen konum, " + joint(j) + ": sonlu değil");
  }
  for (std::size_t k = 0; k < points.size(); ++k) {
    GateResult r = check_point(points[k]);
    if (!r.ok) {
      r.detail = "nokta " + std::to_string(k) + ", " + r.detail;
      return r;
    }
  }

  // Hız ve ivme (G5). rate = 1/T, 1/s. k == n: son noktadan sonra duruş (v = 0).
  const double rate = 1000.0 / period_ms;
  const std::size_t n = points.size();
  Angles v_prev{0.0, 0.0, 0.0};
  for (std::size_t k = 0; k <= n; ++k) {
    for (int j = 0; j < 3; ++j) {
      double v = 0.0;
      if (k < n) {
        const double from = (k == 0) ? current[j] : points[k - 1][j];
        double d = points[k][j] - from;
        if (k == 0) d = beyond_tolerance(d, l_.start_tolerance_deg);
        v = d * rate;
      }
      if (std::abs(v) > l_.max_velocity_dps)
        return fail(fault::kVelocity, step_name(k, n) + ", " + joint(j) +
                                          ": |v|=" + num(std::abs(v)) + " deg/s > " +
                                          num(l_.max_velocity_dps));
      const double a = (v - v_prev[j]) * rate;
      if (std::abs(a) > l_.max_accel_dps2)
        return fail(fault::kAccel, step_name(k, n) + ", " + joint(j) + ": |a|=" + num(std::abs(a)) +
                                       " deg/s2 > " + num(l_.max_accel_dps2));
      v_prev[j] = v;
    }
  }
  return {};
}

Angles Gate::clamp_to_limits(const Angles& a) const {
  Angles out = a;
  for (int j = 0; j < 3; ++j) {
    if (std::isfinite(a[j])) out[j] = std::clamp(a[j], l_.joint_min_deg, l_.joint_max_deg);
  }
  return out;
}

std::optional<Angles> Gate::clamp_command(const Angles& previous, const Angles& target,
                                          double dt_s) const {
  const double dt = std::isfinite(dt_s) ? std::clamp(dt_s, 0.0, kMaxCommandDtS) : 0.0;
  const double max_step = l_.max_velocity_dps * dt;
  Angles out{};
  for (int j = 0; j < 3; ++j) {
    if (!std::isfinite(previous[j])) return std::nullopt;
    const double base = std::clamp(previous[j], l_.joint_min_deg, l_.joint_max_deg);
    const double goal =
        std::isfinite(target[j]) ? std::clamp(target[j], l_.joint_min_deg, l_.joint_max_deg) : base;
    out[j] = std::clamp(goal, base - max_step, base + max_step);
  }
  return out;
}

GateResult Gate::check_health(const DriverState& s) const {
  if (!s.ok) return fail(fault::kDriver, "sürücü durumu okunamadı");
  for (int j = 0; j < 3; ++j) {
    if (!std::isfinite(s.angles[j]) || !std::isfinite(s.temps_c[j]) ||
        !std::isfinite(s.loads_pct[j]) || !std::isfinite(s.voltages_v[j]))
      return fail(fault::kNonFinite, "servo " + std::to_string(j + 1) + ": sonlu olmayan ölçüm");
  }
  for (int j = 0; j < 3; ++j) {
    const std::string servo = "servo " + std::to_string(j + 1) + ": ";
    if (s.temps_c[j] > l_.max_temp_c)
      return fail(fault::kOverTemp,
                  servo + num(s.temps_c[j]) + " C > " + num(l_.max_temp_c) + " C");
    if (std::abs(s.loads_pct[j]) > l_.max_load_pct)
      return fail(fault::kOverLoad, servo + "|yük| " + num(std::abs(s.loads_pct[j])) + " % > " +
                                        num(l_.max_load_pct) + " %");
    if (s.voltages_v[j] < l_.min_voltage_v || s.voltages_v[j] > l_.max_voltage_v)
      return fail(fault::kVoltage, servo + num(s.voltages_v[j]) + " V aralık [" +
                                       num(l_.min_voltage_v) + ", " + num(l_.max_voltage_v) +
                                       "] dışında");
  }
  return {};
}

}  // namespace delta_edge
