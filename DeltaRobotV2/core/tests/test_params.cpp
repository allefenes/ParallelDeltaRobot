// robot.yaml okuyucu testleri.
#include <gtest/gtest.h>

#include <cstdio>
#include <fstream>
#include <stdexcept>
#include <string>

#include "delta_core/params.hpp"

TEST(Params, LoadsRepoYaml) {
  const auto p = delta_core::load_params(DELTA_ROBOT_YAML);
  EXPECT_DOUBLE_EQ(p.base_radius, 65.0);
  EXPECT_DOUBLE_EQ(p.bicep_length, 64.0);
  EXPECT_DOUBLE_EQ(p.forearm_length, 201.0);
  EXPECT_DOUBLE_EQ(p.platform_radius, 35.0);
  EXPECT_DOUBLE_EQ(p.ee_offset, 15.0);
  EXPECT_DOUBLE_EQ(p.spherical_joint_limit, 13.0);
  EXPECT_DOUBLE_EQ(p.arm_angles[2], 240.0);
}

TEST(Params, MissingFileThrows) {
  EXPECT_THROW(delta_core::load_params("/yok/robot.yaml"), std::runtime_error);
}

namespace {
std::string write_tmp(const std::string& name, const std::string& text) {
  const std::string path = std::string("/tmp/") + name;
  std::ofstream(path) << text;
  return path;
}
}  // namespace

TEST(Params, MissingSectionThrows) {
  EXPECT_THROW(delta_core::load_params(write_tmp("p1.yaml", "baska: 1\n")), std::runtime_error);
}

TEST(Params, MissingKeyThrows) {
  EXPECT_THROW(delta_core::load_params(write_tmp("p2.yaml", "kinematics: {base_radius: 1}\n")),
               std::runtime_error);
}

TEST(Params, BadArmAnglesThrows) {
  const std::string y =
      "kinematics: {base_radius: 1, bicep_length: 1, forearm_length: 1, platform_radius: 1,"
      " ee_offset: 1, base_to_floor: 1, motor_limit_min: 1, motor_limit_max: 1,"
      " spherical_joint_limit: 1, motor_step: 1, arm_angles: [0, 120]}\n";
  EXPECT_THROW(delta_core::load_params(write_tmp("p3.yaml", y)), std::runtime_error);
}
