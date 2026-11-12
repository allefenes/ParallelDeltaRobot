// Dynamixel AX-12A arka ucu. TODO(F5): gerçek seri protokol henüz yok; bu sınıf yalnız arayüzün
// derlendiğini gösterir. read_state() her zaman ok=false döner; yanlışlıkla seçilirse EdgeCore
// sağlık denetiminde "driver" hatası verir ve torku açmayı reddeder.
//
// F5'te yapılacaklar:
//   - Protokol 1.0, yarım dupleks, 1 Mbps; yön pini (TX/RX) yönetimi.
//   - Portu özel kilitle aç (flock + TIOCEXCL): seri hattın tek sahibi bu sınıf (G10).
//   - Goal Position (0x1E), Torque Enable (0x18); Present Position/Load/Voltage/Temperature okuma;
//     3 servoya Sync Write ile tek paket.
//   - Açı <-> birim dönüşümü: 0..1023 = 0..300°, motor sıfırı kalibrasyonla eşlenir.
//   - Torku açmadan önce Goal Position = Present Position (eski hedefe sıçramasın).
//   - Mıknatıs çıkışı (GPIO + MOSFET).
#pragma once

#include <string>

#include "delta_edge/driver.hpp"

namespace delta_edge {

class Ax12Driver : public Driver {
 public:
  Ax12Driver(std::string device, int baud);

  void set_goal(const Angles& angles_deg) override;
  DriverState read_state() override;
  void set_torque(bool on) override;
  void set_magnet(bool on) override;

  const std::string& device() const { return device_; }
  int baud() const { return baud_; }

 private:
  std::string device_;
  int baud_;
};

}  // namespace delta_edge
