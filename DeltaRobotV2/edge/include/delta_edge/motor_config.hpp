// Motor parametreleri (edge/config/motor_<model>.yaml, `motor:` bölümü). Biçim motora genel:
// `model` arka ucu seçer, konum ölçeği ve eklem eşlemesi sayısal parametredir. Başka bir motor
// takılırken yeni bir YAML ve (denetim tablosu farklıysa) yeni bir Driver arka ucu yeterlidir.
//
// Eşleme (eklem j, V2 açısı θ deg, pozitif = kol aşağı):
//   tick = zero_tick[j] + sign[j] * θ / deg_per_tick        deg_per_tick = range_deg / ticks
//   θ    = sign[j] * (tick - zero_tick[j]) * deg_per_tick
// Eklem limitleri (robot.yaml kinematics.motor_limit_min/max) 0..ticks-1 içine düşmelidir;
// düşmüyorsa yükleme reddedilir. Hedefler bu limit penceresine kırpılır (G1).
#pragma once

#include <array>
#include <string>

#include "delta_edge/types.hpp"

namespace delta_edge {

struct MotorJoint {
  int id{0};              // servo ID
  double zero_tick{0.0};  // θ = 0 (kısa kol yatay) iken servo konumu, tick
  int sign{1};            // +1: tick artınca θ artar; -1: ters
};

struct MotorConfig {
  std::string model{"AX-12A"};
  int baud{1000000};
  int ticks{1024};          // konum aralığındaki adım sayısı (0..ticks-1)
  double range_deg{300.0};  // ticks adımın kapsadığı açı
  std::array<MotorJoint, 3> joints{{{1, 376.0, 1}, {2, 376.0, 1}, {3, 376.0, 1}}};
  double voltage_v_per_unit{0.1};  // Present Voltage birimi
  double temp_c_per_unit{1.0};     // Present Temperature birimi
  double load_pct_per_unit{0.1};   // Present Load büyüklük birimi (0..1023)
  int return_delay_us{100};        // servo yanıt gecikmesi (AX: 2 us adım, 0..508)
  int status_return_level{2};      // 1: yalnız READ/PING yanıtlanır, 2: WRITE de
  int reply_timeout_ms{5};         // işlem başına yanıt bekleme
  bool local_echo{false};          // tek telli hatta yazılan baytlar geri okunur
  int moving_speed{0};             // Moving Speed kaydı (AX: 0 = en yüksek, 1..1023)
  bool write_angle_limits{true};   // CW/CCW açı limitlerini eklem penceresine yaz (EEPROM)
  double joint_min_deg{-70.0};     // robot.yaml'dan; pencere hesabı için
  double joint_max_deg{150.0};

  double deg_per_tick() const { return range_deg / ticks; }
};

// Eklem j için tick <-> açı (gerçel; yuvarlama/kırpma yok).
double tick_from_deg(const MotorConfig& c, int j, double deg);
double deg_from_tick(const MotorConfig& c, int j, double tick);

// Eklem j'nin izinli tick penceresi: limit açılarının tick karşılıkları, içe yuvarlanmış.
struct TickWindow {
  int lo;
  int hi;
};
TickWindow tick_window(const MotorConfig& c, int j);

// Hedef tick: yuvarlanır ve pencereye kırpılır. `deg` sonlu olmalı (çağıran denetler).
int goal_tick(const MotorConfig& c, int j, double deg);

// Tutarlılık denetimi; geçerliyse boş metin.
std::string validate_motor_config(const MotorConfig& c);

// motor YAML + robot.yaml (eklem limitleri, motor.model ve position_range_deg tutarlılığı).
// Hata olursa std::runtime_error.
MotorConfig load_motor_config(const std::string& motor_yaml_path,
                              const std::string& robot_yaml_path);

}  // namespace delta_edge
