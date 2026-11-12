// Dynamixel Protokol 1.0 işlem katmanı: komut yaz, durum paketini bekle ve doğrula.
// SerialPort üzerinde çalışır; aygıtı kendisi açmaz (G10).
#pragma once

#include <string>
#include <vector>

#include "delta_edge/dynamixel_protocol.hpp"
#include "delta_edge/serial.hpp"

namespace delta_edge::dxl {

enum class BusError {
  kNone,
  kWriteFailed,  // port yazamadı
  kEcho,         // yerel yankı yazılanla tutmadı
  kTimeout,      // süre içinde geçerli yanıt yok
  kChecksum,     // yalnız sağlaması bozuk yanıt geldi
  kWrongId,      // başka ID'den yanıt
  kLength,       // veri boyu istenenle tutmuyor
  kServoError,   // durum paketinde hata biti
};

const char* bus_error_name(BusError e);

struct BusResult {
  BusError error{BusError::kNone};
  std::uint8_t servo_error{0};  // durum paketindeki hata bitleri
  Bytes data;                   // READ yanıtının verisi
  bool ok() const { return error == BusError::kNone; }
  std::string describe() const;
};

struct BusOptions {
  int timeout_ms{5};         // yanıt bekleme süresi, işlem başına
  bool local_echo{false};    // tek telli yarım dupleks: yazılan baytlar geri okunur
  bool write_replies{true};  // status_return_level 2: WRITE de yanıtlanır (1: yalnız READ/PING)
};

class Bus {
 public:
  Bus(SerialPort& port, BusOptions opt) : port_(port), opt_(opt) {}

  BusResult ping(std::uint8_t id);
  BusResult read(std::uint8_t id, std::uint8_t address, std::uint8_t length);
  BusResult write(std::uint8_t id, std::uint8_t address, const Bytes& data);
  // Yanıt dönmez; yalnız gönderim (ve varsa yankı) denetlenir.
  BusResult sync_write(std::uint8_t address, std::uint8_t length,
                       const std::vector<SyncEntry>& entries);

  const BusOptions& options() const { return opt_; }
  // Gözlem (tanı): toplam reddedilen çöp bayt ve bozuk paket sayısı.
  std::size_t discarded_bytes() const { return discarded_; }

 private:
  BusResult transact(const Bytes& packet, std::uint8_t id, bool expect_reply, int expect_len);
  bool send(const Bytes& packet, BusResult* r);
  SerialPort& port_;
  BusOptions opt_;
  std::size_t discarded_{0};
};

}  // namespace delta_edge::dxl
