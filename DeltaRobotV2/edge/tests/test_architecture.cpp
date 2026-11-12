// G10 (mimari test): seri hattı yalnız sürücü arka ucu kullanır. Kenar kaynaklarında seri port
// API'lerine yalnız posix_serial.* (aygıtı açan tek gerçekleme) ve ax12_driver.* içinde izin
// verilir; sürücü, protokol ve kurulum aracı aygıtı yalnız SerialPort arayüzüyle görür, EdgeCore
// donanıma yalnız Driver arayüzüyle erişir. Özel kilit testi: test_posix_serial.cpp.
#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <type_traits>

#include "delta_edge/edge.hpp"

namespace delta_edge {
namespace {

namespace fs = std::filesystem;

TEST(Architecture, G10_OnlyDriverBackendTouchesSerialPort) {
  const char* kForbidden[] = {"termios", "/dev/tty",   "serial_port", "ttyAMA",      "ttyUSB",
                              "ttyS0",   "cfsetspeed", "tcsetattr",   "open(\"/dev", "TIOCEXCL"};
  int scanned = 0;
  for (const char* dir : {"src", "include", "app"}) {
    for (const auto& e : fs::recursive_directory_iterator(fs::path(DELTA_EDGE_SRC) / dir)) {
      if (!e.is_regular_file()) continue;
      const std::string name = e.path().filename().string();
      if (name.rfind("ax12_driver", 0) == 0) continue;   // sürücü arka ucu
      if (name.rfind("posix_serial", 0) == 0) continue;  // aygıtı açan tek gerçekleme
      std::ifstream in(e.path());
      std::stringstream ss;
      ss << in.rdbuf();
      const std::string text = ss.str();
      ++scanned;
      for (const char* token : kForbidden) {
        EXPECT_EQ(text.find(token), std::string::npos)
            << e.path() << " seri port erişimi içeriyor: " << token;
      }
    }
  }
  EXPECT_GE(scanned, 20);  // tarama gerçekten kaynakları gördü
}

TEST(Architecture, G10_EdgeCoreDependsOnlyOnDriverInterface) {
  // EdgeCore somut sürücü değil soyut Driver alır: kurucunun imzası bunu zorlar.
  static_assert(std::is_constructible_v<EdgeCore, const EdgeLimits&, Driver&, EstopInput&, Micros>);
  static_assert(std::is_abstract_v<Driver>);
  static_assert(std::is_abstract_v<EstopInput>);
  SUCCEED();
}

}  // namespace
}  // namespace delta_edge
