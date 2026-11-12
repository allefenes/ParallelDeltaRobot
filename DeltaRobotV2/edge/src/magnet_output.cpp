// Dosya tabanlı mıknatıs çıkışı (sysfs GPIO ya da sanal Pi gözlemi).
#include "delta_edge/magnet_output.hpp"

#include <fstream>

namespace delta_edge {

void FileMagnetOutput::set(bool on) {
  std::ofstream f(path_, std::ios::trunc);
  f << (on ? "1" : "0") << '\n';
  f.flush();
  ok_ = static_cast<bool>(f);
}

}  // namespace delta_edge
