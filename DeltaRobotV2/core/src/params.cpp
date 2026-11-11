// config/robot.yaml okuyucu (yaml-cpp).
#include "delta_core/params.hpp"

#include <yaml-cpp/yaml.h>

#include <stdexcept>

namespace delta_core {

DeltaParams load_params(const std::string& yaml_path) {
  YAML::Node root;
  try {
    root = YAML::LoadFile(yaml_path);
  } catch (const YAML::Exception& e) {
    throw std::runtime_error("robot.yaml okunamadı: " + yaml_path + ": " + e.what());
  }
  const YAML::Node k = root["kinematics"];
  if (!k) throw std::runtime_error("robot.yaml: 'kinematics' bölümü yok");
  auto get = [&k](const char* key) {
    if (!k[key]) throw std::runtime_error(std::string("robot.yaml: kinematics.") + key + " yok");
    return k[key].as<double>();
  };
  DeltaParams p;
  p.base_radius = get("base_radius");
  p.bicep_length = get("bicep_length");
  p.forearm_length = get("forearm_length");
  p.platform_radius = get("platform_radius");
  p.ee_offset = get("ee_offset");
  p.base_to_floor = get("base_to_floor");
  p.motor_limit_min = get("motor_limit_min");
  p.motor_limit_max = get("motor_limit_max");
  p.spherical_joint_limit = get("spherical_joint_limit");
  p.motor_step = get("motor_step");
  const YAML::Node a = k["arm_angles"];
  if (!a || !a.IsSequence() || a.size() != 3)
    throw std::runtime_error("robot.yaml: arm_angles 3 elemanlı olmalı");
  for (std::size_t i = 0; i < 3; ++i) p.arm_angles[i] = a[i].as<double>();
  return p;
}

}  // namespace delta_core
