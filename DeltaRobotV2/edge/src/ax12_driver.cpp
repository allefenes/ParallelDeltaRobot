// AX-12A arka ucu: TODO(F5). Seri kod yok; okuma her zaman başarısız döner (bkz. başlık).
#include "delta_edge/ax12_driver.hpp"

namespace delta_edge {

Ax12Driver::Ax12Driver(std::string device, int baud) : device_(std::move(device)), baud_(baud) {}

void Ax12Driver::set_goal(const Angles& /*angles_deg*/) {}  // TODO(F5): Sync Write Goal Position

DriverState Ax12Driver::read_state() { return DriverState{}; }  // ok=false: kenar torku açmaz

void Ax12Driver::set_torque(bool /*on*/) {}  // TODO(F5): Torque Enable

void Ax12Driver::set_magnet(bool /*on*/) {}  // TODO(F5): mıknatıs GPIO

}  // namespace delta_edge
