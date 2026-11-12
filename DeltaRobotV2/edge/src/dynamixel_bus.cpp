// Protokol 1.0 işlemleri: her işlemden önce giriş tamponu boşaltılır, komut yazılır, yanıt
// süre sınırı içinde ayrıştırılır. Yanıt hiç gelmezse zaman aşımı; yalnız bozuk paket geldiyse
// sağlama hatası; yanlış ID, yanlış boy ya da hata biti gelirse ilgili hata döner.
#include "delta_edge/dynamixel_bus.hpp"

#include <chrono>
#include <utility>

namespace delta_edge::dxl {

const char* bus_error_name(BusError e) {
  switch (e) {
    case BusError::kNone:
      return "yok";
    case BusError::kWriteFailed:
      return "yazma başarısız";
    case BusError::kEcho:
      return "yankı tutmadı";
    case BusError::kTimeout:
      return "zaman aşımı";
    case BusError::kChecksum:
      return "sağlama toplamı";
    case BusError::kWrongId:
      return "yanlış ID";
    case BusError::kLength:
      return "yanlış uzunluk";
    case BusError::kServoError:
      return "servo hatası";
  }
  return "?";
}

std::string BusResult::describe() const {
  std::string s = bus_error_name(error);
  if (error == BusError::kServoError) s += " (" + describe_error(servo_error) + ")";
  return s;
}

bool Bus::send(const Bytes& packet, BusResult* r) {
  port_.flush_input();
  if (!port_.write(packet.data(), packet.size())) {
    r->error = BusError::kWriteFailed;
    return false;
  }
  if (!opt_.local_echo) return true;
  // Tek telli hatta yazılan paket aynen geri okunur; okunmazsa hat ya da yön sorunu var.
  Bytes echo(packet.size());
  std::size_t got = 0;
  while (got < echo.size()) {
    const std::size_t n = port_.read(echo.data() + got, echo.size() - got, opt_.timeout_ms);
    if (n == 0) break;
    got += n;
  }
  if (got != packet.size() || echo != packet) {
    r->error = BusError::kEcho;
    return false;
  }
  return true;
}

BusResult Bus::transact(const Bytes& packet, std::uint8_t id, bool expect_reply, int expect_len) {
  BusResult r;
  if (!send(packet, &r)) return r;
  if (!expect_reply) return r;

  using Clock = std::chrono::steady_clock;
  const auto deadline = Clock::now() + std::chrono::milliseconds(opt_.timeout_ms);
  StatusParser parser;
  std::uint8_t buf[64];
  while (true) {
    const auto left =
        std::chrono::duration_cast<std::chrono::milliseconds>(deadline - Clock::now()).count();
    // Süre dolmuş olsa da bir kez beklemeden okunur: iş parçacığı geç uyanırsa hazır yanıt
    // zaman aşımı sayılmaz. Süre dolduktan sonra gelen sürekli çöp döngüyü uzatamaz.
    const std::size_t n = port_.read(buf, sizeof buf, left > 0 ? static_cast<int>(left) : 0);
    if (n > 0) parser.feed(buf, n);
    auto s = n > 0 ? parser.next() : std::nullopt;
    if (!s) {
      if (n > 0 && left > 0) continue;
      r.error = parser.bad_checksums() > 0 ? BusError::kChecksum : BusError::kTimeout;
      break;
    }
    if (s->id != id) {
      r.error = BusError::kWrongId;
    } else if (s->error != 0) {
      r.error = BusError::kServoError;
      r.servo_error = s->error;
    } else if (static_cast<int>(s->params.size()) != expect_len) {
      r.error = BusError::kLength;
    } else {
      r.data = std::move(s->params);
    }
    break;
  }
  discarded_ += parser.discarded_bytes();
  return r;
}

BusResult Bus::ping(std::uint8_t id) { return transact(make_ping(id), id, id != kBroadcastId, 0); }

BusResult Bus::read(std::uint8_t id, std::uint8_t address, std::uint8_t length) {
  return transact(make_read(id, address, length), id, true, length);
}

BusResult Bus::write(std::uint8_t id, std::uint8_t address, const Bytes& data) {
  return transact(make_write(id, address, data), id, opt_.write_replies && id != kBroadcastId, 0);
}

BusResult Bus::sync_write(std::uint8_t address, std::uint8_t length,
                          const std::vector<SyncEntry>& entries) {
  return transact(make_sync_write(address, length, entries), kBroadcastId, false, 0);
}

}  // namespace delta_edge::dxl
