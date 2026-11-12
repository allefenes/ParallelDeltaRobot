// Kenar sınırları: eklem limitleri config/robot.yaml'dan (tek kaynak), geri kalanı
// edge/config/edge.yaml'dan okunur. Buradaki varsayılanlar yalnız testlerin ve fuzz hedefinin
// dosyasız kurulumu içindir ve iki dosyadaki değerlerle aynıdır.
#pragma once

#include <string>

#include "delta_edge/types.hpp"

namespace delta_edge {

struct EdgeLimits {
  double joint_min_deg{-70.0};      // robot.yaml kinematics.motor_limit_min (yukarı)
  double joint_max_deg{150.0};      // robot.yaml kinematics.motor_limit_max (aşağı)
  double max_velocity_dps{300.0};   // deg/s, eklem başına
  double max_accel_dps2{3000.0};    // deg/s², eklem başına
  double start_tolerance_deg{1.0};  // ilk nokta - ölçülen konum farkından düşülen pay, deg
  int t_stop_ms{200};               // kalp atışı yoksa dur-tut (G6)
  int t_off_ms{1000};               // kalp atışı yoksa tork + mıknatıs kapalı (G7)
  double max_temp_c{70.0};          // °C
  double min_voltage_v{9.0};        // V
  double max_voltage_v{13.0};       // V
  double max_load_pct{90.0};        // mutlak yük, %
  int tick_hz{100};                 // döngü frekansı, Hz
  int telemetry_period_ms{50};      // telemetri aralığı, ms

  Micros tick_period_us() const { return kMicrosPerSecond / tick_hz; }
};

// İki dosyayı okur ve doğrular. Dosya, alan ya da değer hatasında std::runtime_error.
EdgeLimits load_limits(const std::string& robot_yaml_path, const std::string& edge_yaml_path);

// Tutarlılık denetimi; geçerliyse boş metin, değilse ilk hatanın açıklaması.
std::string validate_limits(const EdgeLimits& limits);

}  // namespace delta_edge
