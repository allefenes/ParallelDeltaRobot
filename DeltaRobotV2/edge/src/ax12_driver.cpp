// AX-12A arka ucu: Protokol 1.0 üzerinden hedef, durum, tork ve mıknatıs (bkz. başlık).
#include "delta_edge/ax12_driver.hpp"

#include <cmath>

namespace delta_edge {

using dxl::Bus;
using dxl::BusOptions;
using dxl::BusResult;
using dxl::Bytes;
namespace reg = dxl::ax12;

namespace {

BusOptions bus_options(const MotorConfig& c) {
  BusOptions o;
  o.timeout_ms = c.reply_timeout_ms;
  o.local_echo = c.local_echo;
  o.write_replies = c.status_return_level >= 2;
  return o;
}

std::uint8_t lo8(int v) { return static_cast<std::uint8_t>(v & 0xFF); }

}  // namespace

Ax12Driver::Ax12Driver(SerialPort& port, const MotorConfig& cfg, MagnetOutput& magnet)
    : bus_(port, bus_options(cfg)), cfg_(cfg), magnet_(magnet) {}

bool Ax12Driver::fail(const std::string& what, int j, const BusResult& r) {
  last_error_ = "servo " + std::to_string(j + 1) + " (ID " + std::to_string(cfg_.joints[j].id) +
                "): " + what + ": " + r.describe();
  return false;
}

bool Ax12Driver::init_servo(int j) {
  const std::uint8_t sid = id(j);
  BusResult r = bus_.ping(sid);
  if (!r.ok()) return fail("ping", j, r);
  r = bus_.read(sid, reg::kModelNumber, 2);
  if (!r.ok()) return fail("model okuma", j, r);
  const int model = dxl::get_le16(r.data.data());
  if (model != reg::kModelAx12a) {
    last_error_ = "servo " + std::to_string(j + 1) + ": model numarası " + std::to_string(model) +
                  " (AX-12A = 12 bekleniyor)";
    return false;
  }
  // Status return level: servo yapılandırmadan farklıysa yaz; yanıt eski seviyeye göre
  // gelebileceğinden yazma sonucu değil yeniden okuma esas alınır.
  r = bus_.read(sid, reg::kStatusReturnLevel, 1);
  if (!r.ok()) return fail("status return level okuma", j, r);
  if (r.data[0] != cfg_.status_return_level) {
    bus_.write(sid, reg::kStatusReturnLevel, {lo8(cfg_.status_return_level)});
    r = bus_.read(sid, reg::kStatusReturnLevel, 1);
    if (!r.ok() || r.data[0] != cfg_.status_return_level)
      return fail("status return level yazılamadı", j, r);
  }
  const std::uint8_t delay = lo8(cfg_.return_delay_us / 2);
  r = bus_.read(sid, reg::kReturnDelay, 1);
  if (!r.ok()) return fail("return delay okuma", j, r);
  if (r.data[0] != delay) {
    r = bus_.write(sid, reg::kReturnDelay, {delay});
    if (!r.ok()) return fail("return delay yazma", j, r);
  }
  if (cfg_.write_angle_limits) {
    // Donanım tarafı G1: servo, eklem penceresi dışına hedef kabul etmez.
    const TickWindow w = tick_window(cfg_, j);
    r = bus_.read(sid, reg::kCwAngleLimit, 4);
    if (!r.ok()) return fail("açı limiti okuma", j, r);
    if (dxl::get_le16(r.data.data()) != w.lo || dxl::get_le16(r.data.data() + 2) != w.hi) {
      Bytes lim = dxl::le16(static_cast<std::uint16_t>(w.lo));
      const Bytes hi = dxl::le16(static_cast<std::uint16_t>(w.hi));
      lim.insert(lim.end(), hi.begin(), hi.end());
      r = bus_.write(sid, reg::kCwAngleLimit, lim);
      if (!r.ok()) return fail("açı limiti yazma", j, r);
    }
  }
  r = bus_.write(sid, reg::kMovingSpeed, dxl::le16(static_cast<std::uint16_t>(cfg_.moving_speed)));
  if (!r.ok()) return fail("moving speed yazma", j, r);
  return true;
}

std::string Ax12Driver::initialize() {
  initialized_ = false;
  for (int j = 0; j < 3; ++j) {
    if (!init_servo(j)) return last_error_;
  }
  initialized_ = true;
  return {};
}

void Ax12Driver::set_goal(const Angles& angles_deg) {
  for (double a : angles_deg) {
    if (!std::isfinite(a)) {
      ++goals_rejected_;  // G4: bozuk hedef servoya hiç gitmez
      return;
    }
  }
  if (!torque_on_) return;
  std::vector<dxl::SyncEntry> entries;
  for (int j = 0; j < 3; ++j) {
    entries.push_back(
        {id(j), dxl::le16(static_cast<std::uint16_t>(goal_tick(cfg_, j, angles_deg[j])))});
  }
  const BusResult r = bus_.sync_write(reg::kGoalPosition, 2, entries);
  if (!r.ok()) {
    goal_fault_ = true;
    last_error_ = std::string("hedef gönderilemedi: ") + r.describe();
    return;
  }
  ++goals_sent_;
}

DriverState Ax12Driver::read_state() {
  DriverState s = last_;
  s.ok = !torque_fault_ && !goal_fault_;
  goal_fault_ = false;
  for (int j = 0; j < 3; ++j) {
    // 0x24 konum(2) 0x26 hız(2) 0x28 yük(2) 0x2A gerilim(1) 0x2B sıcaklık(1)
    const BusResult r = bus_.read(id(j), reg::kPresentPosition, 8);
    if (!r.ok()) {
      fail("durum okuma", j, r);
      s.ok = false;
      continue;
    }
    const std::uint8_t* d = r.data.data();
    s.angles[j] = deg_from_tick(cfg_, j, dxl::get_le16(d));
    const int load = dxl::get_le16(d + 4);
    const double mag = (load & 0x3FF) * cfg_.load_pct_per_unit;
    // Bit 10 = CW (tick azalan yön); eklem çerçevesine sign ile çevrilir.
    s.loads_pct[j] = ((load & 0x400) ? -mag : mag) * cfg_.joints[j].sign;
    s.voltages_v[j] = d[6] * cfg_.voltage_v_per_unit;
    s.temps_c[j] = d[7] * cfg_.temp_c_per_unit;
  }
  last_ = s;
  return s;
}

bool Ax12Driver::enable_torque() {
  if (!initialized_ && !initialize().empty()) return false;
  std::vector<dxl::SyncEntry> entries;
  for (int j = 0; j < 3; ++j) {
    const BusResult r = bus_.read(id(j), reg::kPresentPosition, 2);
    if (!r.ok()) return fail("konum okuma (tork öncesi)", j, r);
    entries.push_back({id(j), r.data});  // Goal = Present: tork açılınca sıçrama yok
  }
  BusResult r = bus_.sync_write(reg::kGoalPosition, 2, entries);
  if (!r.ok()) {
    last_error_ = std::string("goal = present gönderilemedi: ") + r.describe();
    return false;
  }
  for (int j = 0; j < 3; ++j) {
    r = bus_.write(id(j), reg::kTorqueEnable, {1});
    if (!r.ok()) return fail("tork açma", j, r);
  }
  return true;
}

void Ax12Driver::disable_torque() {
  // Önce yayın (yanıt beklemez, bozuk yanıt hattında da ulaşır), sonra servo başına doğrulama.
  bus_.write(dxl::kBroadcastId, reg::kTorqueEnable, {0});
  for (int j = 0; j < 3; ++j) {
    const BusResult r = bus_.write(id(j), reg::kTorqueEnable, {0});
    if (!r.ok()) {
      fail("tork kapatma", j, r);
      torque_fault_ = true;
    }
  }
}

void Ax12Driver::set_torque(bool on) {
  torque_fault_ = false;
  if (!on) {
    torque_on_ = false;
    disable_torque();
    return;
  }
  if (enable_torque()) {
    torque_on_ = true;
    return;
  }
  // Yarım açık bırakma: hepsini kapat, okuma başarılı bir tork komutuna dek ok=false.
  const std::string why = last_error_;
  torque_on_ = false;
  disable_torque();
  torque_fault_ = true;
  last_error_ = why;
}

void Ax12Driver::set_magnet(bool on) { magnet_.set(on); }

}  // namespace delta_edge
