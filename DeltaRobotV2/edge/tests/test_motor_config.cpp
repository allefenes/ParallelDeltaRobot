// Motor yapılandırması: YAML okuma, doğrulama, açı <-> tick eşlemesi ve limit penceresi.
#include <gtest/gtest.h>

#include <cmath>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>

#include "delta_edge/motor_config.hpp"

namespace delta_edge {
namespace {

std::string write_tmp(const std::string& name, const std::string& text) {
  const auto path = std::filesystem::temp_directory_path() / ("delta_motor_" + name);
  std::ofstream(path) << text;
  return path.string();
}

const char* kMotorYaml = R"(motor:
  model: AX-12A
  bus: {baud: 1000000, reply_timeout_ms: 5, local_echo: false, status_return_level: 2, return_delay_us: 100}
  position: {ticks: 1024, range_deg: 300.0}
  scale: {voltage_v_per_unit: 0.1, temp_c_per_unit: 1.0, load_pct_per_unit: 0.1}
  moving_speed: 0
  write_angle_limits: true
  joints:
    - {id: 1, zero_tick: 376, sign: 1}
    - {id: 2, zero_tick: 376, sign: 1}
    - {id: 3, zero_tick: 376, sign: 1}
)";

const char* kRobotYaml = R"(kinematics: {motor_limit_min: -70.0, motor_limit_max: 150.0}
motor: {model: AX-12A, position_range_deg: 300.0}
)";

std::string replace(std::string s, const std::string& from, const std::string& to) {
  const auto pos = s.find(from);
  EXPECT_NE(pos, std::string::npos) << from;
  if (pos != std::string::npos) s.replace(pos, from.size(), to);
  return s;
}

std::string load_error(const std::string& motor, const std::string& robot = kRobotYaml) {
  try {
    load_motor_config(write_tmp("m.yaml", motor), write_tmp("r.yaml", robot));
  } catch (const std::runtime_error& e) {
    return e.what();
  }
  return {};
}

TEST(MotorConfig, LoadsRealFileWithLimitsFromRobotYaml) {
  const MotorConfig c = load_motor_config(DELTA_MOTOR_YAML, DELTA_ROBOT_YAML);
  EXPECT_EQ(c.model, "AX-12A");
  EXPECT_EQ(c.baud, 1000000);
  EXPECT_EQ(c.ticks, 1024);
  EXPECT_DOUBLE_EQ(c.range_deg, 300.0);
  EXPECT_DOUBLE_EQ(c.joint_min_deg, -70.0);
  EXPECT_DOUBLE_EQ(c.joint_max_deg, 150.0);
  for (int j = 0; j < 3; ++j) EXPECT_EQ(c.joints[j].id, j + 1);
  EXPECT_EQ(validate_motor_config(c), "");
  // Varsayılan yapı gerçek dosyayla aynı (dosyasız test kurulumu için).
  const MotorConfig d;
  EXPECT_DOUBLE_EQ(d.joints[0].zero_tick, c.joints[0].zero_tick);
  EXPECT_EQ(d.return_delay_us, c.return_delay_us);
  EXPECT_EQ(validate_motor_config(d), "");
}

TEST(MotorConfig, G1_LimitWindowInsideServoRange) {
  const MotorConfig c;
  for (int j = 0; j < 3; ++j) {
    const TickWindow w = tick_window(c, j);
    EXPECT_EQ(w.lo, 138);  // 376 - 70 / 0.29296875 = 137.07 -> içe (yukarı) yuvarlanır
    EXPECT_EQ(w.hi, 888);  // 376 + 150 / 0.29296875 = 888
    EXPECT_GE(deg_from_tick(c, j, w.lo), c.joint_min_deg);
    EXPECT_LE(deg_from_tick(c, j, w.hi), c.joint_max_deg);
  }
}

TEST(MotorConfig, AngleTickRoundTrip) {
  MotorConfig c;
  c.joints[1] = {2, 700.0, -1};
  for (int j = 0; j < 3; ++j) {
    for (double deg = -70.0; deg <= 150.0; deg += 0.37) {
      EXPECT_NEAR(deg_from_tick(c, j, tick_from_deg(c, j, deg)), deg, 1e-9);
      // Yuvarlanmış hedef pencere içinde yarım adım, limit kenarında (içe kırpma) en çok bir adım.
      const double err = std::abs(deg_from_tick(c, j, goal_tick(c, j, deg)) - deg);
      const bool edge =
          deg - c.joint_min_deg < c.deg_per_tick() || c.joint_max_deg - deg < c.deg_per_tick();
      EXPECT_LE(err, (edge ? 1.0 : 0.5) * c.deg_per_tick() + 1e-9) << j << " " << deg;
    }
  }
  EXPECT_DOUBLE_EQ(tick_from_deg(c, 0, 0.0), 376.0);
  EXPECT_DOUBLE_EQ(tick_from_deg(c, 1, 0.0), 700.0);
  EXPECT_LT(tick_from_deg(c, 1, 10.0), 700.0);  // sign -1: θ artınca tick azalır
}

TEST(MotorConfig, G1_GoalTickClampedToJointWindow) {
  MotorConfig c;
  c.joints[2] = {3, 700.0, -1};
  for (int j = 0; j < 3; ++j) {
    const TickWindow w = tick_window(c, j);
    for (double deg : {-1e6, -70.5, 150.5, 1e6}) {
      const int t = goal_tick(c, j, deg);
      EXPECT_GE(t, w.lo);
      EXPECT_LE(t, w.hi);
      const double back = deg_from_tick(c, j, t);
      EXPECT_GE(back, c.joint_min_deg - 1e-9);
      EXPECT_LE(back, c.joint_max_deg + 1e-9);
    }
  }
  EXPECT_EQ(goal_tick(c, 0, 1e6), 888);
  EXPECT_EQ(goal_tick(c, 0, -1e6), 138);
}

TEST(MotorConfig, G1_RejectsLimitsOutsideTickRange) {
  MotorConfig c;
  c.joints[0].zero_tick = 200.0;  // -70 deg -> -38.9 tick
  EXPECT_NE(validate_motor_config(c).find("eklem 1: motor_limit_min/max"), std::string::npos);
  c = MotorConfig{};
  c.joints[2].zero_tick = 600.0;  // 150 deg -> 1112 tick
  EXPECT_NE(validate_motor_config(c).find("eklem 3"), std::string::npos);
  c = MotorConfig{};
  c.joints[1] = {2, 376.0, -1};  // ters yönde 150 deg -> -136 tick
  EXPECT_NE(validate_motor_config(c).find("eklem 2"), std::string::npos);
  EXPECT_NE(load_error(replace(kMotorYaml, "{id: 1, zero_tick: 376", "{id: 1, zero_tick: 100"))
                .find("dışında"),
            std::string::npos);
}

TEST(MotorConfig, ValidationRejectsBadValues) {
  const auto bad = [](auto mutate) {
    MotorConfig c;
    mutate(c);
    return validate_motor_config(c);
  };
  EXPECT_NE(bad([](MotorConfig& c) { c.model = "XM430"; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.ticks = 1; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.range_deg = 400.0; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.range_deg = NAN; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.baud = 115200; }), "");  // AX kodu yok
  EXPECT_NE(bad([](MotorConfig& c) { c.baud = 0; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.baud = 7000; }), "");  // kod > 254
  EXPECT_NE(bad([](MotorConfig& c) { c.voltage_v_per_unit = -0.1; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.load_pct_per_unit = INFINITY; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.return_delay_us = 101; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.return_delay_us = 510; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.return_delay_us = -2; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.status_return_level = 0; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.reply_timeout_ms = 0; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.reply_timeout_ms = 101; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.moving_speed = 1024; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.moving_speed = -1; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.joint_min_deg = 150.0; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.joint_max_deg = NAN; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.joints[1].id = 254; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.joints[1].id = -1; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.joints[2].id = 1; }).find("tekrar"), std::string::npos);
  EXPECT_NE(bad([](MotorConfig& c) { c.joints[0].sign = 0; }), "");
  EXPECT_NE(bad([](MotorConfig& c) { c.joints[0].zero_tick = NAN; }), "");
  EXPECT_EQ(bad([](MotorConfig& c) { c.baud = 57142; }), "");  // kod 34
}

TEST(MotorConfig, LoaderChecksConsistencyWithRobotYaml) {
  EXPECT_EQ(load_error(kMotorYaml), "");
  EXPECT_NE(load_error(kMotorYaml, replace(kRobotYaml, "model: AX-12A", "model: MX-28"))
                .find("robot.yaml motor.model"),
            std::string::npos);
  EXPECT_NE(load_error(kMotorYaml, replace(kRobotYaml, "position_range_deg: 300.0",
                                           "position_range_deg: 360.0"))
                .find("position_range_deg"),
            std::string::npos);
  EXPECT_NE(load_error(kMotorYaml, "motor: {model: AX-12A}\n").find("kinematics"),
            std::string::npos);
}

TEST(MotorConfig, LoaderRejectsMalformedFiles) {
  EXPECT_NE(load_error("foo: 1\n").find("motor bölümü eksik"), std::string::npos);
  EXPECT_NE(load_error(replace(kMotorYaml, "  moving_speed: 0\n", "")).find("moving_speed eksik"),
            std::string::npos);
  EXPECT_NE(load_error(replace(kMotorYaml, "baud: 1000000", "baud: hızlı")).find("geçersiz değer"),
            std::string::npos);
  EXPECT_NE(load_error(replace(kMotorYaml, "    - {id: 3, zero_tick: 376, sign: 1}\n", ""))
                .find("üç elemanlı"),
            std::string::npos);
  EXPECT_NE(load_error(replace(kMotorYaml, "    - {id: 3, zero_tick: 376, sign: 1}", "    - 3"))
                .find("eşleme olmalı"),
            std::string::npos);
  EXPECT_NE(load_error(replace(kMotorYaml, "sign: 1}\n    - {id: 2", "sign: 2}\n    - {id: 2"))
                .find("sign"),
            std::string::npos);
  EXPECT_NE(load_error("motor: [unclosed\n").find("okunamadı"), std::string::npos);
  EXPECT_THROW(load_motor_config("/yok/motor.yaml", DELTA_ROBOT_YAML), std::runtime_error);
}

}  // namespace
}  // namespace delta_edge
