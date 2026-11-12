// delta_servo_tool: kurulum komutları (tarama, ID/baud atama, okuma, tork).
#include "delta_edge/servo_tool.hpp"

#include <stdexcept>

#include "delta_edge/dynamixel_bus.hpp"
#include "delta_edge/posix_serial.hpp"

namespace delta_edge::servo_tool {
namespace {

namespace reg = dxl::ax12;

int to_int(const std::string& s, const char* what, int lo, int hi) {
  std::size_t used = 0;
  int v = 0;
  try {
    v = std::stoi(s, &used);
  } catch (const std::exception&) {
    used = 0;
  }
  if (used == 0 || used != s.size() || v < lo || v > hi) {
    throw std::invalid_argument(std::string(what) + " " + std::to_string(lo) + ".." +
                                std::to_string(hi) + " arası tam sayı olmalı: '" + s + "'");
  }
  return v;
}

dxl::Bus make_bus(const Args& a, SerialPort& port) {
  dxl::BusOptions o;
  o.timeout_ms = a.timeout_ms;
  o.local_echo = a.local_echo;
  return dxl::Bus(port, o);
}

int comm_error(std::ostream& err, const std::string& what, const dxl::BusResult& r) {
  err << "hata: " << what << ": " << r.describe() << '\n';
  return kExitComm;
}

int cmd_scan(const Args& a, dxl::Bus& bus, std::ostream& out) {
  int found = 0;
  for (int id = a.scan_from; id <= a.scan_to; ++id) {
    const auto sid = static_cast<std::uint8_t>(id);
    if (!bus.ping(sid).ok()) continue;
    ++found;
    out << "ID " << id;
    const dxl::BusResult m = bus.read(sid, reg::kModelNumber, 2);
    if (m.ok()) out << ": model " << dxl::get_le16(m.data.data());
    out << '\n';
  }
  out << found << " servo bulundu (" << a.baud << " baud, ID " << a.scan_from << ".." << a.scan_to
      << ")\n";
  return found > 0 ? kExitOk : kExitComm;
}

int cmd_set_id(const Args& a, dxl::Bus& bus, std::ostream& out, std::ostream& err) {
  const auto old_id = static_cast<std::uint8_t>(a.id);
  const auto new_id = static_cast<std::uint8_t>(a.new_id);
  dxl::BusResult r = bus.ping(old_id);
  if (!r.ok()) return comm_error(err, "ID " + std::to_string(a.id) + " yanıt vermiyor", r);
  if (bus.ping(new_id).ok()) {
    err << "hata: ID " << a.new_id << " zaten kullanımda; çakışma olur\n";
    return kExitComm;
  }
  // Yanıt eski ya da yeni ID'den gelebilir: sonuç yeni ID'ye ping ile doğrulanır.
  bus.write(old_id, reg::kId, {new_id});
  r = bus.ping(new_id);
  if (!r.ok()) return comm_error(err, "yeni ID " + std::to_string(a.new_id) + " doğrulanamadı", r);
  out << "ID " << a.id << " -> " << a.new_id << " tamam\n";
  return kExitOk;
}

int cmd_set_baud(const Args& a, dxl::Bus& bus, std::ostream& out, std::ostream& err) {
  const int new_baud = dxl::baud_from_code(static_cast<std::uint8_t>(a.baud_code));
  if (!posix_baud_supported(new_baud)) {
    err << "hata: kod " << a.baud_code << " = " << new_baud
        << " baud bu sistemde açılamaz; servo erişilemez olurdu\n";
    return kExitUsage;
  }
  const auto sid = static_cast<std::uint8_t>(a.id);
  const dxl::BusResult r = bus.ping(sid);
  if (!r.ok()) return comm_error(err, "ID " + std::to_string(a.id) + " yanıt vermiyor", r);
  // Servo hızı yanıttan hemen sonra değiştirir; yanıt bozulabilir, sonucu yok sayılır.
  bus.write(sid, reg::kBaudRate, {static_cast<std::uint8_t>(a.baud_code)});
  out << "ID " << a.id << ": baud kodu " << a.baud_code << " (" << new_baud
      << " baud) yazıldı; doğrulama: --baud " << new_baud << " read " << a.id << '\n';
  return kExitOk;
}

int cmd_read(const Args& a, dxl::Bus& bus, std::ostream& out, std::ostream& err) {
  const auto sid = static_cast<std::uint8_t>(a.id);
  const dxl::BusResult r = bus.read(sid, 0, reg::kTableSize);
  if (!r.ok()) return comm_error(err, "ID " + std::to_string(a.id) + " okunamadı", r);
  const std::uint8_t* t = r.data.data();
  const int load = dxl::get_le16(t + reg::kPresentLoad);
  out << "id " << int{t[reg::kId]} << '\n'
      << "model " << dxl::get_le16(t + reg::kModelNumber) << '\n'
      << "firmware " << int{t[reg::kFirmware]} << '\n'
      << "baud_code " << int{t[reg::kBaudRate]} << " (" << dxl::baud_from_code(t[reg::kBaudRate])
      << " baud)\n"
      << "return_delay_us " << 2 * t[reg::kReturnDelay] << '\n'
      << "cw_angle_limit " << dxl::get_le16(t + reg::kCwAngleLimit) << '\n'
      << "ccw_angle_limit " << dxl::get_le16(t + reg::kCcwAngleLimit) << '\n'
      << "status_return_level " << int{t[reg::kStatusReturnLevel]} << '\n'
      << "torque_enable " << int{t[reg::kTorqueEnable]} << '\n'
      << "goal_position " << dxl::get_le16(t + reg::kGoalPosition) << '\n'
      << "moving_speed " << dxl::get_le16(t + reg::kMovingSpeed) << '\n'
      << "present_position " << dxl::get_le16(t + reg::kPresentPosition) << '\n'
      << "present_load " << ((load & 0x400) ? "-" : "") << (load & 0x3FF) << '\n'
      << "present_voltage_v " << t[reg::kPresentVoltage] / 10.0 << '\n'
      << "present_temperature_c " << int{t[reg::kPresentTemperature]} << '\n';
  return kExitOk;
}

int cmd_torque(const Args& a, dxl::Bus& bus, std::ostream& out, std::ostream& err) {
  const auto sid = static_cast<std::uint8_t>(a.id);
  const dxl::BusResult r =
      bus.write(sid, reg::kTorqueEnable, {a.on ? std::uint8_t{1} : std::uint8_t{0}});
  if (!r.ok()) return comm_error(err, "ID " + std::to_string(a.id) + " tork yazılamadı", r);
  out << "ID " << a.id << ": tork " << (a.on ? "açık" : "kapalı") << '\n';
  return kExitOk;
}

}  // namespace

const char* usage() {
  return R"(delta_servo_tool: Dynamixel AX-12A kurulum aracı (Protokol 1.0)

Kullanım: delta_servo_tool [seçenekler] KOMUT [argümanlar]

Komutlar:
  scan [FROM TO]       ID FROM..TO aralığına ping (varsayılan 0..253)
  set-id OLD NEW       servonun ID'sini değiştir (NEW boş olmalı; ping ile doğrulanır)
  set-baud ID CODE     baud kodu yaz: baud = 2000000 / (CODE + 1); 1 = 1 Mbps
  read ID              denetim tablosunu oku (ID, baud, limitler, konum, gerilim, sıcaklık)
  torque ID on|off     tork aç / kapat

Seçenekler:
  --device PATH        seri aygıt (varsayılan: DELTA_SERIAL_DEVICE, yoksa aşağıdaki aygıt)
  --baud N             hat hızı (varsayılan 1000000)
  --timeout-ms N       yanıt bekleme, ms (varsayılan 20)
  --echo               tek telli hat: yazılan baytlar geri okunur
  -h, --help           bu yardım

Port özel kilitle açılır: delta_edge çalışırken araç portu açamaz (G10).
Çıkış kodları: 0 tamam, 1 servo yanıtı/haberleşme hatası, 2 kullanım hatası.
)";
}

ParseResult parse_args(const std::vector<std::string>& argv) {
  ParseResult res;
  Args& a = res.args;
  std::vector<std::string> pos;
  try {
    for (std::size_t i = 0; i < argv.size(); ++i) {
      const std::string& s = argv[i];
      const auto next = [&]() -> const std::string& {
        if (i + 1 >= argv.size()) throw std::invalid_argument(s + " bir değer bekliyor");
        return argv[++i];
      };
      if (s == "-h" || s == "--help") {
        a.command = Command::kHelp;
        res.ok = true;
        return res;
      } else if (s == "--device") {
        a.device = next();
      } else if (s == "--baud") {
        a.baud = to_int(next(), "--baud", 1, 4000000);
      } else if (s == "--timeout-ms") {
        a.timeout_ms = to_int(next(), "--timeout-ms", 1, 1000);
      } else if (s == "--echo") {
        a.local_echo = true;
      } else if (s.size() > 1 && s[0] == '-') {
        throw std::invalid_argument("bilinmeyen seçenek: " + s);
      } else {
        pos.push_back(s);
      }
    }
    if (pos.empty()) throw std::invalid_argument("komut yok (--help)");
    const std::string& cmd = pos[0];
    const std::size_t n = pos.size() - 1;
    const auto want = [&](std::size_t k) {
      if (n != k)
        throw std::invalid_argument(cmd + " " + std::to_string(k) + " argüman bekliyor (--help)");
    };
    if (cmd == "scan") {
      a.command = Command::kScan;
      if (n != 0) {
        want(2);
        a.scan_from = to_int(pos[1], "FROM", 0, 253);
        a.scan_to = to_int(pos[2], "TO", a.scan_from, 253);
      }
    } else if (cmd == "set-id") {
      want(2);
      a.command = Command::kSetId;
      a.id = to_int(pos[1], "OLD", 0, 253);
      a.new_id = to_int(pos[2], "NEW", 0, 253);
      if (a.id == a.new_id) throw std::invalid_argument("OLD ve NEW aynı");
    } else if (cmd == "set-baud") {
      want(2);
      a.command = Command::kSetBaud;
      a.id = to_int(pos[1], "ID", 0, 253);
      a.baud_code = to_int(pos[2], "CODE", 0, 254);
    } else if (cmd == "read") {
      want(1);
      a.command = Command::kRead;
      a.id = to_int(pos[1], "ID", 0, 253);
    } else if (cmd == "torque") {
      want(2);
      a.command = Command::kTorque;
      a.id = to_int(pos[1], "ID", 0, 253);
      if (pos[2] != "on" && pos[2] != "off") throw std::invalid_argument("torque on|off bekliyor");
      a.on = pos[2] == "on";
    } else {
      throw std::invalid_argument("bilinmeyen komut: " + cmd + " (--help)");
    }
  } catch (const std::invalid_argument& e) {
    res.error = e.what();
    return res;
  }
  res.ok = true;
  return res;
}

int run(const Args& a, SerialPort& port, std::ostream& out, std::ostream& err) {
  dxl::Bus bus = make_bus(a, port);
  switch (a.command) {
    case Command::kScan:
      return cmd_scan(a, bus, out);
    case Command::kSetId:
      return cmd_set_id(a, bus, out, err);
    case Command::kSetBaud:
      return cmd_set_baud(a, bus, out, err);
    case Command::kRead:
      return cmd_read(a, bus, out, err);
    case Command::kTorque:
      return cmd_torque(a, bus, out, err);
    case Command::kHelp:
      break;
  }
  out << usage() << "Varsayılan aygıt: " << default_serial_device() << '\n';
  return kExitOk;
}

}  // namespace delta_edge::servo_tool
