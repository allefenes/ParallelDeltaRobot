// delta_servo_tool komut mantığı: argüman ayrıştırma ve komutların SerialPort üzerinde
// yürütülmesi. Aygıtı açan ince katman app/delta_servo_tool.cpp'dedir (G10).
#pragma once

#include <ostream>
#include <string>
#include <vector>

#include "delta_edge/serial.hpp"

namespace delta_edge::servo_tool {

enum class Command { kHelp, kScan, kSetId, kSetBaud, kRead, kTorque };

struct Args {
  Command command{Command::kHelp};
  std::string device;  // boş: varsayılan aygıt
  int baud{1000000};
  int timeout_ms{20};
  bool local_echo{false};
  int id{0};         // set-id OLD, set-baud ID, read ID, torque ID
  int new_id{0};     // set-id NEW
  int baud_code{1};  // set-baud
  bool on{false};    // torque
  int scan_from{0};
  int scan_to{253};
};

struct ParseResult {
  bool ok{false};
  Args args;
  std::string error;
};

// argv[1..] (program adı hariç).
ParseResult parse_args(const std::vector<std::string>& argv);

const char* usage();

// Çıkış kodları.
constexpr int kExitOk = 0;
constexpr int kExitComm = 1;   // servo yanıt vermedi / hata
constexpr int kExitUsage = 2;  // argüman hatası

// Komutu yürütür; sonuç `out`a, hatalar `err`e yazılır.
int run(const Args& a, SerialPort& port, std::ostream& out, std::ostream& err);

}  // namespace delta_edge::servo_tool
