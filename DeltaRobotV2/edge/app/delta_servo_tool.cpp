// delta_servo_tool: kurulum aracı için ince giriş noktası. Mantık src/servo_tool.cpp'de;
// burada yalnız argümanlar ayrıştırılır ve port posix_serial ile özel kilitle açılır (G10).
#include <cstdlib>
#include <exception>
#include <iostream>
#include <string>
#include <vector>

#include "delta_edge/posix_serial.hpp"
#include "delta_edge/servo_tool.hpp"

int main(int argc, char** argv) {
  namespace tool = delta_edge::servo_tool;
  const std::vector<std::string> args(argv + 1, argv + argc);
  const tool::ParseResult p = tool::parse_args(args);
  if (!p.ok) {
    std::cerr << "hata: " << p.error << '\n';
    return tool::kExitUsage;
  }
  tool::Args a = p.args;
  if (a.command == tool::Command::kHelp) {
    std::cout << tool::usage() << "Varsayılan aygıt: " << delta_edge::default_serial_device()
              << '\n';
    return tool::kExitOk;
  }
  if (a.device.empty()) {
    const char* env = std::getenv("DELTA_SERIAL_DEVICE");
    a.device = (env && *env) ? env : delta_edge::default_serial_device();
  }
  try {
    auto port = delta_edge::open_posix_serial({a.device, a.baud});
    return tool::run(a, *port, std::cout, std::cerr);
  } catch (const std::exception& e) {
    std::cerr << "hata: " << e.what() << '\n';
    return tool::kExitComm;
  }
}
