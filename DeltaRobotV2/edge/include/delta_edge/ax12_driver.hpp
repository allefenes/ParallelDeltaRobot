// Dynamixel AX-12A arka ucu (Protokol 1.0). Seri hatta yalnız SerialPort arayüzüyle erişir;
// aygıtı posix_serial.cpp açar ve kilitler (G10). Parametreler MotorConfig'ten
// (edge/config/motor_ax12.yaml).
//
// Davranış:
//   set_goal    Üç servoya TEK Sync Write (Goal Position). Sonlu olmayan değer varsa hiçbir şey
//               gönderilmez (G4). Hedef eklem limit penceresine kırpılır (G1). Tork kapalıyken
//               gönderilmez: AX serisinde Goal yazımı torku kendiliğinden açabilir.
//   read_state  Servo başına bir READ_DATA (0x24..0x2B: konum, hız, yük, gerilim, sıcaklık).
//               Zaman aşımı, sağlama, yanlış ID/boy ya da servo hata biti -> ok=false (EdgeCore
//               torku açmayı reddeder, tork açıksa FAULT'a geçer). Okunamayan eklemde son geçerli
//               değer kalır (sonlu olmayan değer telemetriye girmez).
//   set_torque  Açmadan önce: gerekirse initialize(), Present Position oku, Goal = Present
//               (Sync Write; sıçrama yok), sonra her servoya doğrulamalı Torque Enable = 1.
//               Herhangi bir adım başarısızsa tork açılmaz, hepsi kapatılır ve read_state
//               başarılı bir tork komutuna kadar ok=false döner. Kapatma: yayın + servo başına.
//   set_magnet  MagnetOutput'a iletilir (GPIO F5'te; şimdilik dosya ya da boş çıkış).
//
// F5 donanım kabulünde doğrulanacaklar: yön (TX/RX) donanımı ve return_delay_us, zero_tick ve
// sign kalibrasyonu, Goal yazımının torku açıp açmadığı, limit dışında başlayan kolda davranış.
#pragma once

#include <string>

#include "delta_edge/driver.hpp"
#include "delta_edge/dynamixel_bus.hpp"
#include "delta_edge/magnet_output.hpp"
#include "delta_edge/motor_config.hpp"
#include "delta_edge/serial.hpp"

namespace delta_edge {

class Ax12Driver : public Driver {
 public:
  // `port` ve `magnet` sürücüden uzun yaşamalı. `cfg` doğrulanmış olmalı.
  Ax12Driver(SerialPort& port, const MotorConfig& cfg, MagnetOutput& magnet);

  // Servoları denetler ve yapılandırır: ping, model numarası, return delay, status return
  // level, (isteğe bağlı) CW/CCW açı limitleri = eklem penceresi, Moving Speed. EEPROM yalnız
  // değer farklıysa yazılır. Başarılıysa boş metin, değilse ilk hatanın açıklaması.
  std::string initialize();

  void set_goal(const Angles& angles_deg) override;
  DriverState read_state() override;
  void set_torque(bool on) override;
  void set_magnet(bool on) override;

  // --- Gözlem (testler, tanı) ---
  bool initialized() const { return initialized_; }
  bool torque_on() const { return torque_on_; }
  long long goals_sent() const { return goals_sent_; }
  long long goals_rejected() const { return goals_rejected_; }  // sonlu olmayan (G4)
  const std::string& last_error() const { return last_error_; }

 private:
  std::uint8_t id(int j) const { return static_cast<std::uint8_t>(cfg_.joints[j].id); }
  bool fail(const std::string& what, int j, const dxl::BusResult& r);
  bool init_servo(int j);
  bool enable_torque();
  void disable_torque();

  dxl::Bus bus_;
  MotorConfig cfg_;
  MagnetOutput& magnet_;
  DriverState last_{};
  bool initialized_{false};
  bool torque_on_{false};
  bool torque_fault_{false};  // son tork komutu başarısız: read_state ok=false
  bool goal_fault_{false};    // son hedef gönderilemedi: bir sonraki okuma ok=false
  long long goals_sent_{0};
  long long goals_rejected_{0};
  std::string last_error_;
};

}  // namespace delta_edge
