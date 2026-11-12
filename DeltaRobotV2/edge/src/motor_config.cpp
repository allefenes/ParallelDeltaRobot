// Motor YAML okuyucu, doğrulama ve açı <-> tick eşlemesi.
#include "delta_edge/motor_config.hpp"

#include <yaml-cpp/yaml.h>

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace delta_edge {
namespace {

constexpr double kEps = 1e-9;

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

bool known_model(const std::string& m) { return m == "AX-12A"; }

}  // namespace

double tick_from_deg(const MotorConfig& c, int j, double deg) {
  const MotorJoint& m = c.joints[static_cast<std::size_t>(j)];
  return m.zero_tick + m.sign * deg / c.deg_per_tick();
}

double deg_from_tick(const MotorConfig& c, int j, double tick) {
  const MotorJoint& m = c.joints[static_cast<std::size_t>(j)];
  return m.sign * (tick - m.zero_tick) * c.deg_per_tick();
}

TickWindow tick_window(const MotorConfig& c, int j) {
  const double a = tick_from_deg(c, j, c.joint_min_deg);
  const double b = tick_from_deg(c, j, c.joint_max_deg);
  // İçe yuvarla: pencere içindeki her tick limit açılarının arasında kalır.
  return {static_cast<int>(std::ceil(std::min(a, b) - kEps)),
          static_cast<int>(std::floor(std::max(a, b) + kEps))};
}

int goal_tick(const MotorConfig& c, int j, double deg) {
  const TickWindow w = tick_window(c, j);
  const double t = std::round(tick_from_deg(c, j, deg));
  return static_cast<int>(std::clamp(t, static_cast<double>(w.lo), static_cast<double>(w.hi)));
}

std::string validate_motor_config(const MotorConfig& c) {
  if (!known_model(c.model)) return "bilinmeyen model '" + c.model + "' (desteklenen: AX-12A)";
  if (c.ticks < 2 || c.ticks > 65536) return "ticks 2..65536 olmalı";
  if (!std::isfinite(c.range_deg) || !(c.range_deg > 0.0) || c.range_deg > 360.0)
    return "range_deg 0..360 olmalı";
  // AX serisi: baud = 2 000 000 / (kod + 1), kod 0..254.
  const int code = c.baud > 0 ? 2000000 / c.baud - 1 : -1;
  if (code < 0 || code > 254 || 2000000 / (code + 1) != c.baud)
    return "baud bir AX baud koduna karşılık gelmeli (2000000/(kod+1))";
  for (double v : {c.voltage_v_per_unit, c.temp_c_per_unit, c.load_pct_per_unit}) {
    if (!std::isfinite(v) || !(v > 0.0)) return "ölçek katsayıları sonlu ve pozitif olmalı";
  }
  if (c.return_delay_us < 0 || c.return_delay_us > 508 || c.return_delay_us % 2 != 0)
    return "return_delay_us 0..508 ve çift olmalı (2 us adım)";
  if (c.status_return_level != 1 && c.status_return_level != 2)
    return "status_return_level 1 ya da 2 olmalı (0'da okuma yapılamaz)";
  if (c.reply_timeout_ms < 1 || c.reply_timeout_ms > 100) return "reply_timeout_ms 1..100 olmalı";
  if (c.moving_speed < 0 || c.moving_speed > 1023) return "moving_speed 0..1023 olmalı";
  if (!std::isfinite(c.joint_min_deg) || !std::isfinite(c.joint_max_deg) ||
      !(c.joint_min_deg < c.joint_max_deg))
    return "eklem limitleri sonlu ve min < max olmalı";
  for (int j = 0; j < 3; ++j) {
    const MotorJoint& m = c.joints[static_cast<std::size_t>(j)];
    const std::string tag = "eklem " + std::to_string(j + 1) + ": ";
    if (m.id < 0 || m.id > 253) return tag + "id 0..253 olmalı";
    for (int k = 0; k < j; ++k) {
      if (c.joints[static_cast<std::size_t>(k)].id == m.id) return tag + "id tekrar ediyor";
    }
    if (m.sign != 1 && m.sign != -1) return tag + "sign +1 ya da -1 olmalı";
    if (!std::isfinite(m.zero_tick)) return tag + "zero_tick sonlu olmalı";
    const double a = tick_from_deg(c, j, c.joint_min_deg);
    const double b = tick_from_deg(c, j, c.joint_max_deg);
    const double top = static_cast<double>(c.ticks - 1);
    if (std::min(a, b) < -kEps || std::max(a, b) > top + kEps) {
      return tag + "motor_limit_min/max tick karşılığı (" + std::to_string(a) + ", " +
             std::to_string(b) + ") 0.." + std::to_string(c.ticks - 1) + " dışında";
    }
  }
  return {};
}

MotorConfig load_motor_config(const std::string& motor_yaml_path,
                              const std::string& robot_yaml_path) {
  MotorConfig c;
  const YAML::Node robot = load_file(robot_yaml_path);
  const YAML::Node kin = section(robot, "kinematics", robot_yaml_path);
  c.joint_min_deg = value<double>(kin, "motor_limit_min", robot_yaml_path + ":kinematics");
  c.joint_max_deg = value<double>(kin, "motor_limit_max", robot_yaml_path + ":kinematics");
  const YAML::Node rmotor = section(robot, "motor", robot_yaml_path);
  const std::string rctx = robot_yaml_path + ":motor";
  const std::string robot_model = value<std::string>(rmotor, "model", rctx);
  const double robot_range = value<double>(rmotor, "position_range_deg", rctx);

  const YAML::Node root = load_file(motor_yaml_path);
  const YAML::Node m = section(root, "motor", motor_yaml_path);
  const std::string ctx = motor_yaml_path + ":motor";
  c.model = value<std::string>(m, "model", ctx);
  const YAML::Node bus = section(m, "bus", ctx);
  c.baud = value<int>(bus, "baud", ctx + ".bus");
  c.reply_timeout_ms = value<int>(bus, "reply_timeout_ms", ctx + ".bus");
  c.local_echo = value<bool>(bus, "local_echo", ctx + ".bus");
  c.status_return_level = value<int>(bus, "status_return_level", ctx + ".bus");
  c.return_delay_us = value<int>(bus, "return_delay_us", ctx + ".bus");
  const YAML::Node pos = section(m, "position", ctx);
  c.ticks = value<int>(pos, "ticks", ctx + ".position");
  c.range_deg = value<double>(pos, "range_deg", ctx + ".position");
  const YAML::Node scale = section(m, "scale", ctx);
  c.voltage_v_per_unit = value<double>(scale, "voltage_v_per_unit", ctx + ".scale");
  c.temp_c_per_unit = value<double>(scale, "temp_c_per_unit", ctx + ".scale");
  c.load_pct_per_unit = value<double>(scale, "load_pct_per_unit", ctx + ".scale");
  c.moving_speed = value<int>(m, "moving_speed", ctx);
  c.write_angle_limits = value<bool>(m, "write_angle_limits", ctx);
  const YAML::Node joints = m["joints"];
  if (!joints || !joints.IsSequence() || joints.size() != 3)
    throw std::runtime_error(ctx + ".joints üç elemanlı liste olmalı (kol 1, 2, 3)");
  for (std::size_t j = 0; j < 3; ++j) {
    const std::string jctx = ctx + ".joints[" + std::to_string(j) + "]";
    if (!joints[j].IsMap()) throw std::runtime_error(jctx + " eşleme olmalı");
    c.joints[j].id = value<int>(joints[j], "id", jctx);
    c.joints[j].zero_tick = value<double>(joints[j], "zero_tick", jctx);
    c.joints[j].sign = value<int>(joints[j], "sign", jctx);
  }

  if (c.model != robot_model)
    throw std::runtime_error("motor modeli '" + c.model + "' robot.yaml motor.model '" +
                             robot_model + "' ile aynı değil");
  if (std::abs(c.range_deg - robot_range) > kEps)
    throw std::runtime_error("range_deg robot.yaml motor.position_range_deg ile aynı değil");
  const std::string err = validate_motor_config(c);
  if (!err.empty()) throw std::runtime_error("geçersiz motor yapılandırması: " + err);
  return c;
}

}  // namespace delta_edge
