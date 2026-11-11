// Robot geometrisi ve limitleri. Tek kaynak config/robot.yaml (`kinematics` bölümü).
#pragma once

#include <array>
#include <string>

namespace delta_core {

// Birimler: uzunluk mm, açı derece.
struct DeltaParams {
  double base_radius{65.0};      // R: merkezden motor eksenine
  double bicep_length{64.0};     // L1: motor ekseni -> üst küresel eklem merkezi
  double forearm_length{201.0};  // L2: üst -> alt küresel eklem merkezi
  double platform_radius{35.0};  // r: platform merkezi (P) -> alt eklem merkezi
  double ee_offset{15.0};        // P -> mıknatıs ucu (aşağı)
  double base_to_floor{240.0};   // motor ekseni düzlemi -> zemin
  std::array<double, 3> arm_angles{0.0, 120.0, 240.0};
  double motor_limit_min{-70.0};       // yukarı (negatif θ kolu kaldırır)
  double motor_limit_max{150.0};       // aşağı
  double spherical_joint_limit{13.0};  // rot başı yanal açı sınırı
  double motor_step{0.29};             // servo çözünürlüğü
};

// config/robot.yaml'ın `kinematics` bölümünü okur; dosya ya da alan yoksa std::runtime_error.
DeltaParams load_params(const std::string& yaml_path);

}  // namespace delta_core
