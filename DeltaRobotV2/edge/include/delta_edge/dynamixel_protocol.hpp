// Dynamixel Protokol 1.0: saf paket katmanı (G/Ç yok, saat yok).
//
// Komut paketi:  FF FF ID LEN INSTR P1..Pn CHK   LEN = n + 2
// Durum paketi:  FF FF ID LEN ERR   P1..Pn CHK   LEN = n + 2
// CHK = ~(ID + LEN + INSTR/ERR + P1 + .. + Pn) & 0xFF
//
// Kaynak: ROBOTIS e-manual, "Protocol 1.0" ve "AX-12A" denetim tablosu.
#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace delta_edge::dxl {

using Bytes = std::vector<std::uint8_t>;

constexpr std::uint8_t kHeader = 0xFF;
constexpr std::uint8_t kBroadcastId = 0xFE;  // yanıt dönmez
constexpr std::uint8_t kMaxId = 0xFD;        // 253
constexpr std::size_t kMaxParams = 253;      // LEN tek bayt: n + 2 <= 255

// Komutlar.
constexpr std::uint8_t kPing = 0x01;
constexpr std::uint8_t kReadData = 0x02;
constexpr std::uint8_t kWriteData = 0x03;
constexpr std::uint8_t kSyncWrite = 0x83;

// Durum paketindeki hata baytının bitleri.
constexpr std::uint8_t kErrInputVoltage = 0x01;
constexpr std::uint8_t kErrAngleLimit = 0x02;
constexpr std::uint8_t kErrOverheating = 0x04;
constexpr std::uint8_t kErrRange = 0x08;
constexpr std::uint8_t kErrChecksum = 0x10;
constexpr std::uint8_t kErrOverload = 0x20;
constexpr std::uint8_t kErrInstruction = 0x40;

// AX-12A denetim tablosu (kullanılan adresler). EEPROM: 0x00..0x17, RAM: 0x18..
namespace ax12 {
constexpr std::uint8_t kModelNumber = 0x00;  // 2 bayt, AX-12A = 12
constexpr std::uint8_t kFirmware = 0x02;
constexpr std::uint8_t kId = 0x03;
constexpr std::uint8_t kBaudRate = 0x04;       // baud = 2 000 000 / (kod + 1)
constexpr std::uint8_t kReturnDelay = 0x05;    // birim 2 us
constexpr std::uint8_t kCwAngleLimit = 0x06;   // 2 bayt
constexpr std::uint8_t kCcwAngleLimit = 0x08;  // 2 bayt
constexpr std::uint8_t kStatusReturnLevel = 0x10;
constexpr std::uint8_t kTorqueEnable = 0x18;
constexpr std::uint8_t kGoalPosition = 0x1E;  // 2 bayt
constexpr std::uint8_t kMovingSpeed = 0x20;   // 2 bayt
constexpr std::uint8_t kPresentPosition = 0x24;
constexpr std::uint8_t kPresentSpeed = 0x26;
constexpr std::uint8_t kPresentLoad = 0x28;  // bit 10 yön (1 = CW), 0..1023 büyüklük
constexpr std::uint8_t kPresentVoltage = 0x2A;
constexpr std::uint8_t kPresentTemperature = 0x2B;
constexpr std::uint8_t kTableSize = 0x32;  // 0x00..0x31
constexpr std::uint16_t kModelAx12a = 12;
}  // namespace ax12

// Baud kodu -> baud (Protokol 1.0, AX serisi).
constexpr int baud_from_code(std::uint8_t code) { return 2000000 / (code + 1); }

// ID..son parametre üzerinden sağlama toplamı. `data` başlığı (FF FF) içermez.
std::uint8_t checksum(const std::uint8_t* data, std::size_t n);

// Komut paketi. Parametre sayısı kMaxParams'ı aşarsa std::invalid_argument.
Bytes make_packet(std::uint8_t id, std::uint8_t instruction, const Bytes& params);
Bytes make_ping(std::uint8_t id);
Bytes make_read(std::uint8_t id, std::uint8_t address, std::uint8_t length);
Bytes make_write(std::uint8_t id, std::uint8_t address, const Bytes& data);

struct SyncEntry {
  std::uint8_t id;
  Bytes data;  // her girişte tam `length` bayt
};
// Uzunluğu tutmayan giriş varsa std::invalid_argument.
Bytes make_sync_write(std::uint8_t address, std::uint8_t length,
                      const std::vector<SyncEntry>& entries);

// Küçük endian 16 bit yardımcıları.
inline Bytes le16(std::uint16_t v) {
  return {static_cast<std::uint8_t>(v & 0xFF), static_cast<std::uint8_t>(v >> 8)};
}
inline std::uint16_t get_le16(const std::uint8_t* p) {
  return static_cast<std::uint16_t>(p[0] | (p[1] << 8));
}

struct StatusPacket {
  std::uint8_t id{0};
  std::uint8_t error{0};  // hata bitleri
  Bytes params;
};

// Akış ayrıştırıcısı: bayt parçaları beslenir, tam ve sağlaması tutan paketler sırayla çıkar.
// Çöp baytlar atlanır (başlık aranır); sağlaması tutmayan ya da LEN < 2 olan aday paket
// reddedilir ve bir bayt kaydırılarak yeniden eşlenir. Asla istisna fırlatmaz.
class StatusParser {
 public:
  void feed(const std::uint8_t* data, std::size_t n);
  void feed(const Bytes& b) { feed(b.data(), b.size()); }
  std::optional<StatusPacket> next();
  void reset();

  std::size_t pending() const { return buf_.size(); }
  std::size_t discarded_bytes() const { return discarded_; }
  std::size_t bad_checksums() const { return bad_checksum_; }
  std::size_t bad_lengths() const { return bad_length_; }

 private:
  void drop(std::size_t n);
  Bytes buf_;
  std::size_t discarded_{0};
  std::size_t bad_checksum_{0};
  std::size_t bad_length_{0};
};

// Durum hatası baytının okunur açıklaması (ör. "aşırı ısınma, aşırı yük"); 0 ise boş.
std::string describe_error(std::uint8_t error);

}  // namespace delta_edge::dxl
