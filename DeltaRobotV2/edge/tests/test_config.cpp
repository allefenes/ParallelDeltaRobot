// Yapılandırma: robot.yaml (eklem limitleri tek kaynak) + edge.yaml okuma ve doğrulama.
#include <gtest/gtest.h>

#include <cmath>
#include <filesystem>
#include <fstream>
#include <stdexcept>

#include "delta_edge/config.hpp"

namespace delta_edge {
namespace {

std::string write_tmp(const std::string& name, const std::string& text) {
  const auto path = std::filesystem::temp_directory_path() / ("delta_edge_" + name);
  std::ofstream(path) << text;
  return path.string();
}

const char* kEdgeYaml = R"(edge:
  joint: {max_velocity_dps: 300.0, max_accel_dps2: 3000.0, start_tolerance_deg: 1.0}
  heartbeat: {t_stop_ms: 200, t_off_ms: 1000}
  health: {max_temp_c: 70, min_voltage_v: 9, max_voltage_v: 13, max_load_pct: 90}
  loop: {tick_hz: 100, telemetry_period_ms: 50}
)";

TEST(Config, LoadsRealFilesJointLimitsFromRobotYaml) {
  // G1: eklem limitleri tek kaynaktan (robot.yaml) gelir.
  const EdgeLimits l = load_limits(DELTA_ROBOT_YAML, DELTA_EDGE_YAML);
  EXPECT_DOUBLE_EQ(l.joint_min_deg, -70.0);
  EXPECT_DOUBLE_EQ(l.joint_max_deg, 150.0);
  EXPECT_DOUBLE_EQ(l.max_velocity_dps, 300.0);
  EXPECT_DOUBLE_EQ(l.max_accel_dps2, 3000.0);
  EXPECT_EQ(l.t_stop_ms, 200);
  EXPECT_EQ(l.t_off_ms, 1000);
  EXPECT_EQ(l.tick_hz, 100);
  EXPECT_EQ(l.tick_period_us(), 10000);
  EXPECT_EQ(validate_limits(l), "");
}

TEST(Config, DefaultsMatchFiles) {
  const EdgeLimits f = load_limits(DELTA_ROBOT_YAML, DELTA_EDGE_YAML);
  const EdgeLimits d;
  EXPECT_DOUBLE_EQ(d.joint_min_deg, f.joint_min_deg);
  EXPECT_DOUBLE_EQ(d.joint_max_deg, f.joint_max_deg);
  EXPECT_DOUBLE_EQ(d.max_velocity_dps, f.max_velocity_dps);
  EXPECT_DOUBLE_EQ(d.max_accel_dps2, f.max_accel_dps2);
  EXPECT_DOUBLE_EQ(d.start_tolerance_deg, f.start_tolerance_deg);
  EXPECT_EQ(d.t_stop_ms, f.t_stop_ms);
  EXPECT_EQ(d.t_off_ms, f.t_off_ms);
  EXPECT_DOUBLE_EQ(d.max_temp_c, f.max_temp_c);
  EXPECT_DOUBLE_EQ(d.min_voltage_v, f.min_voltage_v);
  EXPECT_DOUBLE_EQ(d.max_voltage_v, f.max_voltage_v);
  EXPECT_DOUBLE_EQ(d.max_load_pct, f.max_load_pct);
  EXPECT_EQ(d.tick_hz, f.tick_hz);
  EXPECT_EQ(d.telemetry_period_ms, f.telemetry_period_ms);
}

TEST(Config, MissingFileThrows) {
  EXPECT_THROW(load_limits("/yok/robot.yaml", DELTA_EDGE_YAML), std::runtime_error);
  EXPECT_THROW(load_limits(DELTA_ROBOT_YAML, "/yok/edge.yaml"), std::runtime_error);
}

TEST(Config, MissingSectionOrFieldThrows) {
  const std::string robot_ok =
      write_tmp("r_ok.yaml", "kinematics: {motor_limit_min: -70, motor_limit_max: 150}\n");
  const std::string edge_ok = write_tmp("e_ok.yaml", kEdgeYaml);
  EXPECT_NO_THROW(load_limits(robot_ok, edge_ok));
  EXPECT_THROW(load_limits(write_tmp("r1.yaml", "foo: 1\n"), edge_ok), std::runtime_error);
  EXPECT_THROW(load_limits(write_tmp("r2.yaml", "kinematics: {motor_limit_min: -70}\n"), edge_ok),
               std::runtime_error);
  EXPECT_THROW(
      load_limits(write_tmp("r3.yaml", "kinematics: {motor_limit_min: x, motor_limit_max: 1}\n"),
                  edge_ok),
      std::runtime_error);
  EXPECT_THROW(load_limits(robot_ok, write_tmp("e1.yaml", "edge: {}\n")), std::runtime_error);
  EXPECT_THROW(load_limits(robot_ok, write_tmp("e2.yaml", "[1, 2\n")), std::runtime_error);
  // Doğrulamadan geçmeyen değer: t_off <= t_stop.
  std::string bad = kEdgeYaml;
  bad.replace(bad.find("t_off_ms: 1000"), 14, "t_off_ms: 100");
  EXPECT_THROW(load_limits(robot_ok, write_tmp("e3.yaml", bad)), std::runtime_error);
}

TEST(Config, ValidateRejectsInconsistentLimits) {
  const auto bad = [](auto mutate) {
    EdgeLimits l;
    mutate(l);
    return !validate_limits(l).empty();
  };
  EXPECT_FALSE(bad([](EdgeLimits&) {}));
  EXPECT_TRUE(bad([](EdgeLimits& l) { l.max_velocity_dps = std::nan(""); }));
  EXPECT_TRUE(bad([](EdgeLimits& l) { l.joint_min_deg = 150.0; }));
  EXPECT_TRUE(bad([](EdgeLimits& l) { l.max_velocity_dps = 0.0; }));
  EXPECT_TRUE(bad([](EdgeLimits& l) { l.max_accel_dps2 = 0.0; }));
  EXPECT_TRUE(bad([](EdgeLimits& l) { l.start_tolerance_deg = -0.1; }));
  EXPECT_TRUE(bad([](EdgeLimits& l) { l.tick_hz = 9; }));
  EXPECT_TRUE(bad([](EdgeLimits& l) { l.tick_hz = 1001; }));
  EXPECT_FALSE(bad([](EdgeLimits& l) { l.t_stop_ms = 20; }));  // tam iki döngü
  EXPECT_TRUE(bad([](EdgeLimits& l) { l.t_stop_ms = 19; }));
  EXPECT_TRUE(bad([](EdgeLimits& l) { l.t_off_ms = l.t_stop_ms; }));
  EXPECT_TRUE(bad([](EdgeLimits& l) { l.max_temp_c = 0.0; }));
  EXPECT_TRUE(bad([](EdgeLimits& l) { l.min_voltage_v = 0.0; }));
  EXPECT_TRUE(bad([](EdgeLimits& l) { l.min_voltage_v = 13.0; }));
  EXPECT_TRUE(bad([](EdgeLimits& l) { l.max_load_pct = 0.0; }));
  EXPECT_TRUE(bad([](EdgeLimits& l) { l.max_load_pct = 100.5; }));
  EXPECT_FALSE(bad([](EdgeLimits& l) { l.max_load_pct = 100.0; }));
  EXPECT_TRUE(bad([](EdgeLimits& l) { l.telemetry_period_ms = 0; }));
}

}  // namespace
}  // namespace delta_edge
