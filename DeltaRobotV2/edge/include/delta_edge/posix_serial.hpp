// POSIX seri hat gerçeklemesi (Linux, Raspberry Pi). Kenar kaynaklarında aygıt dosyasını açan
// TEK yer bu dosya ve posix_serial.cpp'dir (G10, tests/test_architecture.cpp izin listesi).
//
// Aygıt ham kipte (termios raw, 8N1, akış denetimi yok) ve ÖZEL kilitle açılır:
// flock(LOCK_EX | LOCK_NB) ikinci bir süreci (root dahil) reddeder, TIOCEXCL ise kilidi
// tanımayan araçların (ör. minicom) open() çağrısını reddeder.
#pragma once

#include <memory>
#include <string>

#include "delta_edge/serial.hpp"

namespace delta_edge {

struct PosixSerialOptions {
  std::string device;  // boşsa default_serial_device()
  int baud{1000000};   // desteklenen termios hızlarından biri olmalı
};

// Raspberry Pi varsayılan aygıtı (PL011 UART, GPIO14/15). Açıklama posix_serial.cpp'de.
const char* default_serial_device();

// Desteklenen hızlar: 9600 .. 4000000 arası standart Linux termios hızları.
bool posix_baud_supported(int baud);

// Açar ve yapılandırır; hata (aygıt yok, meşgul, tty değil, hız desteklenmiyor) olursa
// std::runtime_error.
std::unique_ptr<SerialPort> open_posix_serial(const PosixSerialOptions& opt);

}  // namespace delta_edge
