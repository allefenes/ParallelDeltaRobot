// FakeServoBus: protokol düzeyinde sahte AX-12A hattı (SerialPort test ikizi).
// N servonun denetim tablosunu tutar; PING / READ / WRITE / SYNC_WRITE paketlerini gerçek servo
// gibi yanıtlar (status return level, yayın ID'si, baud kodu eşleşmesi). Hata enjeksiyonu:
// yanıt düşürme, bozuk sağlama, hata bitleri, çöp bayt, yanlış ID, yazma hatası, yerel yankı.
// Zaman yoktur: yanıt yazma anında hazırlanır, read() beklemez (veri yoksa hemen 0 = zaman aşımı).
#pragma once

#include <array>
#include <deque>
#include <stdexcept>
#include <vector>

#include "delta_edge/dynamixel_protocol.hpp"
#include "delta_edge/serial.hpp"

namespace delta_edge::test {

class FakeServoBus : public SerialPort {
 public:
  using Bytes = dxl::Bytes;
  using Table = std::array<std::uint8_t, dxl::ax12::kTableSize>;

  struct Servo {
    Table table{};
    int drop_replies{0};           // >0: sonraki n yanıt düşer; <0: hiç yanıt yok
    bool corrupt_checksum{false};  // yanıtın sağlama baytı bozulur
    std::uint8_t error_bits{0};    // her yanıta eklenen hata bitleri
    int reply_as_id{-1};           // >=0: yanıt bu ID ile gelir
    int extra_param_bytes{0};      // yanıta fazladan veri (uzunluk hatası)

    int id() const { return table[dxl::ax12::kId]; }
    int u16(std::uint8_t addr) const { return dxl::get_le16(&table[addr]); }
    void set_u16(std::uint8_t addr, int v) {
      table[addr] = static_cast<std::uint8_t>(v & 0xFF);
      table[addr + 1] = static_cast<std::uint8_t>((v >> 8) & 0xFF);
    }
  };

  struct Instr {
    std::uint8_t id;
    std::uint8_t instr;
    Bytes params;
  };

  explicit FakeServoBus(const std::vector<int>& ids) {
    for (int id : ids) add_servo(id);
  }

  Servo& add_servo(int id) {
    namespace r = dxl::ax12;
    Servo s;
    s.set_u16(r::kModelNumber, r::kModelAx12a);
    s.table[r::kFirmware] = 24;
    s.table[r::kId] = static_cast<std::uint8_t>(id);
    s.table[r::kBaudRate] = 1;
    s.table[r::kReturnDelay] = 250;
    s.set_u16(r::kCwAngleLimit, 0);
    s.set_u16(r::kCcwAngleLimit, 1023);
    s.table[r::kStatusReturnLevel] = 2;
    s.set_u16(r::kGoalPosition, 512);
    s.set_u16(r::kPresentPosition, 512);
    s.table[r::kPresentVoltage] = 120;
    s.table[r::kPresentTemperature] = 30;
    servos_.push_back(s);
    return servos_.back();
  }

  Servo& servo(int id) {
    for (auto& s : servos_) {
      if (s.id() == id) return s;
    }
    throw std::out_of_range("FakeServoBus: ID yok");
  }
  bool has(int id) const {
    for (const auto& s : servos_) {
      if (s.id() == id) return true;
    }
    return false;
  }

  // --- Hat düzeyi enjeksiyon ---
  void inject_garbage(const Bytes& b) { garbage_ = b; }  // sonraki yanıtın önüne
  void set_echo(bool on) { echo_ = on; }
  void set_write_fails(bool on) { write_fails_ = on; }
  void set_line_baud(int baud) { line_baud_ = baud; }
  bool goal_enables_torque{true};  // AX: tork kapalıyken Goal yazımı torku açabilir
  bool follow_goal{true};          // tork açıkken Present = Goal (anında)

  // --- Gözlem ---
  const std::vector<Instr>& log() const { return log_; }
  void clear_log() { log_.clear(); }
  int flushes() const { return flushes_; }
  int count(std::uint8_t instr, std::uint8_t address) const {
    int n = 0;
    for (const auto& i : log_)
      n += (i.instr == instr && !i.params.empty() && i.params[0] == address);
    return n;
  }

  // --- SerialPort ---
  bool write(const std::uint8_t* data, std::size_t n) override {
    if (write_fails_) return false;
    if (echo_) out_.insert(out_.end(), data, data + n);
    in_.insert(in_.end(), data, data + n);
    process();
    return true;
  }
  std::size_t read(std::uint8_t* buf, std::size_t max, int /*timeout_ms*/) override {
    std::size_t n = 0;
    while (n < max && !out_.empty()) {
      buf[n++] = out_.front();
      out_.pop_front();
    }
    return n;
  }
  void flush_input() override {
    out_.clear();
    ++flushes_;
  }

 private:
  void process() {
    while (true) {
      while (in_.size() >= 2 && !(in_[0] == 0xFF && in_[1] == 0xFF)) in_.pop_front();
      if (in_.size() < 4) return;
      const std::size_t total = in_[3] + 4u;
      if (in_.size() < total) return;
      Bytes p(in_.begin(), in_.begin() + static_cast<std::ptrdiff_t>(total));
      in_.erase(in_.begin(), in_.begin() + static_cast<std::ptrdiff_t>(total));
      if (p[3] < 2) continue;  // LEN < 2: gerçek servo da yok sayar
      const bool good = dxl::checksum(p.data() + 2, total - 3) == p[total - 1];
      handle(p[2], p[4], Bytes(p.begin() + 5, p.end() - 1), good);
    }
  }

  bool reachable(const Servo& s) const {
    return dxl::baud_from_code(s.table[dxl::ax12::kBaudRate]) == line_baud_;
  }

  void apply_write(Servo& s, std::uint8_t addr, const Bytes& data) {
    namespace r = dxl::ax12;
    for (std::size_t k = 0; k < data.size(); ++k) s.table[addr + k] = data[k];
    const bool goal = addr <= r::kGoalPosition + 1 && addr + data.size() > r::kGoalPosition;
    if (goal && goal_enables_torque) s.table[r::kTorqueEnable] = 1;
    if (goal && follow_goal && s.table[r::kTorqueEnable])
      s.set_u16(r::kPresentPosition, s.u16(r::kGoalPosition));
  }

  void handle(std::uint8_t id, std::uint8_t instr, const Bytes& params, bool good) {
    namespace r = dxl::ax12;
    log_.push_back({id, instr, params});
    if (instr == dxl::kSyncWrite && id == dxl::kBroadcastId && good && params.size() >= 2) {
      const std::size_t len = params[1];
      for (std::size_t k = 2; len > 0 && k + len < params.size(); k += len + 1) {
        if (!has(params[k])) continue;
        Servo& s = servo(params[k]);
        if (!reachable(s)) continue;
        apply_write(s, params[0],
                    Bytes(params.begin() + static_cast<std::ptrdiff_t>(k + 1),
                          params.begin() + static_cast<std::ptrdiff_t>(k + 1 + len)));
      }
      return;
    }
    for (auto& s : servos_) {
      const bool mine = s.id() == id || id == dxl::kBroadcastId;
      if (!mine || !reachable(s)) continue;
      const int reply_id = s.id();  // ID değişse de yanıt eski ID'den
      if (!good) {
        if (id != dxl::kBroadcastId) reply(s, reply_id, dxl::kErrChecksum, {});
        continue;
      }
      std::uint8_t err = 0;
      Bytes data;
      bool answer = true;
      if (instr == dxl::kPing) {
        answer = true;
      } else if (instr == dxl::kReadData && params.size() == 2) {
        if (params[0] + params[1] > r::kTableSize) {
          err = dxl::kErrRange;
        } else {
          data.assign(s.table.begin() + params[0], s.table.begin() + params[0] + params[1]);
        }
        answer = s.table[r::kStatusReturnLevel] >= 1;
      } else if (instr == dxl::kWriteData && !params.empty()) {
        const Bytes payload(params.begin() + 1, params.end());
        answer = s.table[r::kStatusReturnLevel] >= 2;
        if (params[0] + payload.size() > r::kTableSize) {
          err = dxl::kErrRange;
        } else {
          apply_write(s, params[0], payload);
        }
      } else {
        err = dxl::kErrInstruction;
      }
      if (answer && id != dxl::kBroadcastId) reply(s, reply_id, err, data);
    }
  }

  void reply(Servo& s, int id, std::uint8_t err, Bytes data) {
    if (s.drop_replies != 0) {
      if (s.drop_replies > 0) --s.drop_replies;
      return;
    }
    data.insert(data.end(), static_cast<std::size_t>(s.extra_param_bytes), 0x00);
    const int rid = s.reply_as_id >= 0 ? s.reply_as_id : id;
    Bytes p = dxl::make_packet(static_cast<std::uint8_t>(rid),
                               static_cast<std::uint8_t>(err | s.error_bits), data);
    if (s.corrupt_checksum) p.back() = static_cast<std::uint8_t>(p.back() ^ 0x5A);
    out_.insert(out_.end(), garbage_.begin(), garbage_.end());
    garbage_.clear();
    out_.insert(out_.end(), p.begin(), p.end());
  }

  std::vector<Servo> servos_;
  std::deque<std::uint8_t> in_;
  std::deque<std::uint8_t> out_;
  std::vector<Instr> log_;
  Bytes garbage_;
  bool echo_{false};
  bool write_fails_{false};
  int line_baud_{1000000};
  int flushes_{0};
};

}  // namespace delta_edge::test
