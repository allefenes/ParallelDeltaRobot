// Dynamixel Protokol 1.0 paket kurma ve durum paketi ayrıştırma.
#include "delta_edge/dynamixel_protocol.hpp"

#include <stdexcept>
#include <utility>

namespace delta_edge::dxl {

std::uint8_t checksum(const std::uint8_t* data, std::size_t n) {
  unsigned sum = 0;
  for (std::size_t i = 0; i < n; ++i) sum += data[i];
  return static_cast<std::uint8_t>(~sum & 0xFF);
}

Bytes make_packet(std::uint8_t id, std::uint8_t instruction, const Bytes& params) {
  if (params.size() > kMaxParams) throw std::invalid_argument("dxl: parametre sayısı > 253");
  Bytes p;
  p.reserve(params.size() + 6);
  p.push_back(kHeader);
  p.push_back(kHeader);
  p.push_back(id);
  p.push_back(static_cast<std::uint8_t>(params.size() + 2));
  p.push_back(instruction);
  p.insert(p.end(), params.begin(), params.end());
  p.push_back(checksum(p.data() + 2, p.size() - 2));
  return p;
}

Bytes make_ping(std::uint8_t id) { return make_packet(id, kPing, {}); }

Bytes make_read(std::uint8_t id, std::uint8_t address, std::uint8_t length) {
  return make_packet(id, kReadData, {address, length});
}

Bytes make_write(std::uint8_t id, std::uint8_t address, const Bytes& data) {
  Bytes params{address};
  params.insert(params.end(), data.begin(), data.end());
  return make_packet(id, kWriteData, params);
}

Bytes make_sync_write(std::uint8_t address, std::uint8_t length,
                      const std::vector<SyncEntry>& entries) {
  Bytes params{address, length};
  for (const auto& e : entries) {
    if (e.data.size() != length) throw std::invalid_argument("dxl: sync write veri boyu tutmuyor");
    params.push_back(e.id);
    params.insert(params.end(), e.data.begin(), e.data.end());
  }
  return make_packet(kBroadcastId, kSyncWrite, params);
}

void StatusParser::feed(const std::uint8_t* data, std::size_t n) {
  buf_.insert(buf_.end(), data, data + n);
}

void StatusParser::drop(std::size_t n) {
  buf_.erase(buf_.begin(), buf_.begin() + static_cast<std::ptrdiff_t>(n));
}

void StatusParser::reset() { buf_.clear(); }

std::optional<StatusPacket> StatusParser::next() {
  while (true) {
    // Başlığa kadar olan çöpü at. Tek kalan FF bir sonraki parçanın başı olabilir: tutulur.
    std::size_t i = 0;
    while (i + 1 < buf_.size() && !(buf_[i] == kHeader && buf_[i + 1] == kHeader)) ++i;
    if (i + 1 >= buf_.size() && !buf_.empty() && buf_.back() != kHeader) i = buf_.size();
    if (i > 0) {
      discarded_ += i;
      drop(i);
    }
    if (buf_.size() < 4) return std::nullopt;
    // FF FF FF ...: ID 0xFF geçersiz; ilk FF çöptür, kaydır.
    if (buf_[2] == kHeader) {
      ++discarded_;
      drop(1);
      continue;
    }
    const std::size_t len = buf_[3];
    if (len < 2) {
      ++bad_length_;
      ++discarded_;
      drop(1);
      continue;
    }
    const std::size_t total = len + 4;
    if (buf_.size() < total) return std::nullopt;
    if (checksum(buf_.data() + 2, total - 3) != buf_[total - 1]) {
      ++bad_checksum_;
      ++discarded_;
      drop(1);  // paket içinde gerçek başlık olabilir: bir bayt kaydırıp yeniden ara
      continue;
    }
    StatusPacket s;
    s.id = buf_[2];
    s.error = buf_[4];
    s.params.assign(buf_.begin() + 5, buf_.begin() + static_cast<std::ptrdiff_t>(total - 1));
    drop(total);
    return s;
  }
}

std::string describe_error(std::uint8_t error) {
  static const std::pair<std::uint8_t, const char*> kNames[] = {
      {kErrInputVoltage, "giriş gerilimi"}, {kErrAngleLimit, "açı limiti"},
      {kErrOverheating, "aşırı ısınma"},    {kErrRange, "aralık dışı"},
      {kErrChecksum, "sağlama toplamı"},    {kErrOverload, "aşırı yük"},
      {kErrInstruction, "geçersiz komut"}};
  std::string out;
  for (const auto& [bit, name] : kNames) {
    if (!(error & bit)) continue;
    if (!out.empty()) out += ", ";
    out += name;
  }
  if (error & 0x80) out += out.empty() ? "bilinmeyen bit 7" : ", bilinmeyen bit 7";
  return out;
}

}  // namespace delta_edge::dxl
