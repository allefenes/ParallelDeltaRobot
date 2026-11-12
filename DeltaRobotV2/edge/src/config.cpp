// robot.yaml (eklem limitleri, tek kaynak) + edge.yaml (kenar sınırları) okuyucu.
#include "delta_edge/config.hpp"

#include <yaml-cpp/yaml.h>

#include <cmath>
#include <stdexcept>

namespace delta_edge {
namespace {

YAML::Node section(const YAML::Node& parent, const char* key, const std::string& ctx) {
  const YAML::Node n = parent[key];
  if (!n || !n.IsMap()) throw std::runtime_error(ctx + "." + key + " bölümü eksik");
  return n;
}

template <typename T>
T value(const YAML::Node& parent, const char* key, const std::string& ctx) {
  const YAML::Node n = parent[key];
  if (!n || !n.IsScalar()) throw std::runtime_error(ctx + "." + key + " eksik");
  try {
    return n.as<T>();
  } catch (const YAML::Exception&) {
    throw std::runtime_error(ctx + "." + key + " geçersiz değer");
  }
}

YAML::Node load_file(const std::string& path) {
  try {
    return YAML::LoadFile(path);
  } catch (const YAML::Exception& e) {
    throw std::runtime_error(path + " okunamadı: " + e.what());
  }
}

}  // namespace

EdgeLimits load_limits(const std::string& robot_yaml_path, const std::string& edge_yaml_path) {
  EdgeLimits l;
  const YAML::Node robot = load_file(robot_yaml_path);
  const YAML::Node kin = section(robot, "kinematics", robot_yaml_path);
  const std::string kctx = robot_yaml_path + ":kinematics";
  l.joint_min_deg = value<double>(kin, "motor_limit_min", kctx);
  l.joint_max_deg = value<double>(kin, "motor_limit_max", kctx);

  const YAML::Node root = load_file(edge_yaml_path);
  const YAML::Node edge = section(root, "edge", edge_yaml_path);
  const std::string ectx = edge_yaml_path + ":edge";
  const YAML::Node joint = section(edge, "joint", ectx);
  l.max_velocity_dps = value<double>(joint, "max_velocity_dps", ectx + ".joint");
  l.max_accel_dps2 = value<double>(joint, "max_accel_dps2", ectx + ".joint");
  l.start_tolerance_deg = value<double>(joint, "start_tolerance_deg", ectx + ".joint");
  const YAML::Node hb = section(edge, "heartbeat", ectx);
  l.t_stop_ms = value<int>(hb, "t_stop_ms", ectx + ".heartbeat");
  l.t_off_ms = value<int>(hb, "t_off_ms", ectx + ".heartbeat");
  const YAML::Node health = section(edge, "health", ectx);
  l.max_temp_c = value<double>(health, "max_temp_c", ectx + ".health");
  l.min_voltage_v = value<double>(health, "min_voltage_v", ectx + ".health");
  l.max_voltage_v = value<double>(health, "max_voltage_v", ectx + ".health");
  l.max_load_pct = value<double>(health, "max_load_pct", ectx + ".health");
  const YAML::Node loop = section(edge, "loop", ectx);
  l.tick_hz = value<int>(loop, "tick_hz", ectx + ".loop");
  l.telemetry_period_ms = value<int>(loop, "telemetry_period_ms", ectx + ".loop");

  const std::string err = validate_limits(l);
  if (!err.empty()) throw std::runtime_error("geçersiz kenar sınırları: " + err);
  return l;
}

std::string validate_limits(const EdgeLimits& l) {
  for (double v :
       {l.joint_min_deg, l.joint_max_deg, l.max_velocity_dps, l.max_accel_dps2,
        l.start_tolerance_deg, l.max_temp_c, l.min_voltage_v, l.max_voltage_v, l.max_load_pct}) {
    if (!std::isfinite(v)) return "sonlu olmayan değer";
  }
  if (!(l.joint_min_deg < l.joint_max_deg)) return "motor_limit_min < motor_limit_max olmalı";
  if (!(l.max_velocity_dps > 0.0)) return "max_velocity_dps > 0 olmalı";
  if (!(l.max_accel_dps2 > 0.0)) return "max_accel_dps2 > 0 olmalı";
  if (l.start_tolerance_deg < 0.0) return "start_tolerance_deg >= 0 olmalı";
  if (l.tick_hz < 10 || l.tick_hz > 1000) return "tick_hz 10..1000 aralığında olmalı";
  // T_stop en az iki döngü: bekçi eşiği bir döngü erken tutulduğundan pozitif kalmalı.
  if (static_cast<Micros>(l.t_stop_ms) * kMicrosPerMs < 2 * l.tick_period_us())
    return "t_stop_ms en az iki döngü periyodu olmalı";
  if (l.t_off_ms <= l.t_stop_ms) return "t_off_ms > t_stop_ms olmalı";
  if (!(l.max_temp_c > 0.0)) return "max_temp_c > 0 olmalı";
  if (!(l.min_voltage_v > 0.0 && l.min_voltage_v < l.max_voltage_v))
    return "0 < min_voltage_v < max_voltage_v olmalı";
  if (!(l.max_load_pct > 0.0 && l.max_load_pct <= 100.0)) return "max_load_pct 0..100 olmalı";
  if (l.telemetry_period_ms < 1) return "telemetry_period_ms >= 1 olmalı";
  return {};
}

}  // namespace delta_edge
