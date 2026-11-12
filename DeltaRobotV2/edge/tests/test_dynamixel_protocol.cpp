// Dynamixel Protokol 1.0: paket kurma (e-manual bayt vektörleri), durum ayrıştırıcısı
// (çöp, bölünmüş akış, bozuk sağlama/uzunluk, rastgele akış) ve işlem katmanı (Bus).
#include <gtest/gtest.h>

#include <algorithm>
#include <cstdint>
#include <deque>
#include <iterator>
#include <stdexcept>

#include "delta_edge/dynamixel_bus.hpp"
#include "delta_edge/dynamixel_protocol.hpp"
#include "fake_servo_bus.hpp"

namespace delta_edge::dxl {
namespace {

using test::FakeServoBus;

// --- Paket kurma: ROBOTIS e-manual (Protocol 1.0) örnekleri ---

TEST(DxlProtocol, PingVectorFromEManual) {
  EXPECT_EQ(make_ping(1), (Bytes{0xFF, 0xFF, 0x01, 0x02, 0x01, 0xFB}));
}

TEST(DxlProtocol, ReadTemperatureVectorFromEManual) {
  EXPECT_EQ(make_read(1, ax12::kPresentTemperature, 1),
            (Bytes{0xFF, 0xFF, 0x01, 0x04, 0x02, 0x2B, 0x01, 0xCC}));
}

TEST(DxlProtocol, BroadcastWriteIdVectorFromEManual) {
  EXPECT_EQ(make_write(kBroadcastId, ax12::kId, {1}),
            (Bytes{0xFF, 0xFF, 0xFE, 0x04, 0x03, 0x03, 0x01, 0xF6}));
}

TEST(DxlProtocol, SyncWriteVectorFromEManual) {
  // ID 0..3: Goal Position + Moving Speed (4 bayt).
  const Bytes p = make_sync_write(ax12::kGoalPosition, 4,
                                  {{0, {0x10, 0x00, 0x50, 0x01}},
                                   {1, {0x20, 0x02, 0x60, 0x03}},
                                   {2, {0x30, 0x00, 0x70, 0x01}},
                                   {3, {0x20, 0x02, 0x80, 0x03}}});
  const Bytes want{0xFF, 0xFF, 0xFE, 0x18, 0x83, 0x1E, 0x04, 0x00, 0x10, 0x00,
                   0x50, 0x01, 0x01, 0x20, 0x02, 0x60, 0x03, 0x02, 0x30, 0x00,
                   0x70, 0x01, 0x03, 0x20, 0x02, 0x80, 0x03, 0x12};
  EXPECT_EQ(p, want);
}

TEST(DxlProtocol, ChecksumAndHelpers) {
  const std::uint8_t body[] = {0x01, 0x02, 0x00};
  EXPECT_EQ(checksum(body, 3), 0xFC);
  EXPECT_EQ(le16(0x03FF), (Bytes{0xFF, 0x03}));
  const std::uint8_t raw[] = {0x34, 0x12};
  EXPECT_EQ(get_le16(raw), 0x1234);
  EXPECT_EQ(baud_from_code(1), 1000000);
  EXPECT_EQ(baud_from_code(34), 57142);
}

TEST(DxlProtocol, RejectsOversizedPacketsAndBadSyncData) {
  EXPECT_NO_THROW(make_packet(1, kWriteData, Bytes(253, 0)));
  EXPECT_THROW(make_packet(1, kWriteData, Bytes(254, 0)), std::invalid_argument);
  EXPECT_THROW(make_sync_write(ax12::kGoalPosition, 2, {{1, {0x00}}}), std::invalid_argument);
}

TEST(DxlProtocol, DescribeErrorBits) {
  EXPECT_EQ(describe_error(0), "");
  EXPECT_EQ(describe_error(kErrOverheating | kErrOverload), "aşırı ısınma, aşırı yük");
  EXPECT_EQ(describe_error(0x7F),
            "giriş gerilimi, açı limiti, aşırı ısınma, aralık dışı, sağlama toplamı, aşırı yük, "
            "geçersiz komut");
  EXPECT_EQ(describe_error(0x80), "bilinmeyen bit 7");
  EXPECT_EQ(describe_error(0x81), "giriş gerilimi, bilinmeyen bit 7");
}

// --- Durum ayrıştırıcısı ---

TEST(DxlParser, ParsesStatusVectorsFromEManual) {
  StatusParser p;
  p.feed(Bytes{0xFF, 0xFF, 0x01, 0x02, 0x00, 0xFC});        // ping yanıtı
  p.feed(Bytes{0xFF, 0xFF, 0x01, 0x03, 0x00, 0x20, 0xDB});  // sıcaklık 32 °C
  auto a = p.next();
  ASSERT_TRUE(a);
  EXPECT_EQ(a->id, 1);
  EXPECT_EQ(a->error, 0);
  EXPECT_TRUE(a->params.empty());
  auto b = p.next();
  ASSERT_TRUE(b);
  EXPECT_EQ(b->params, (Bytes{0x20}));
  EXPECT_FALSE(p.next());
  EXPECT_EQ(p.pending(), 0u);
}

TEST(DxlParser, ExposesErrorByte) {
  StatusParser p;
  p.feed(Bytes{0xFF, 0xFF, 0x01, 0x02, 0x24, 0xD8});
  auto s = p.next();
  ASSERT_TRUE(s);
  EXPECT_EQ(s->error, kErrOverheating | kErrOverload);
}

TEST(DxlParser, ResyncsAfterGarbage) {
  StatusParser p;
  p.feed(Bytes{0x00, 0x13, 0xFF, 0x42, 0xFF});  // tek FF'ler başlık değildir
  EXPECT_FALSE(p.next());
  p.feed(make_packet(7, 0, {0xAA}));
  auto s = p.next();
  ASSERT_TRUE(s);
  EXPECT_EQ(s->id, 7);
  EXPECT_EQ(s->params, (Bytes{0xAA}));
  EXPECT_EQ(p.discarded_bytes(), 5u);
}

TEST(DxlParser, DiscardsGarbageWithoutHeaderEntirely) {
  StatusParser p;
  p.feed(Bytes{0x01, 0x02, 0x03});
  EXPECT_FALSE(p.next());
  EXPECT_EQ(p.pending(), 0u);
  p.feed(Bytes{0x05, 0xFF});  // sondaki FF bir sonraki başlığın parçası olabilir
  EXPECT_FALSE(p.next());
  EXPECT_EQ(p.pending(), 1u);
}

TEST(DxlParser, TripleHeaderIsSkipped) {
  StatusParser p;
  Bytes b{0xFF};
  const Bytes pkt = make_packet(2, 0, {});
  b.insert(b.end(), pkt.begin(), pkt.end());
  p.feed(b);
  auto s = p.next();
  ASSERT_TRUE(s);
  EXPECT_EQ(s->id, 2);
}

TEST(DxlParser, ByteByByteFeed) {
  StatusParser p;
  const Bytes pkt = make_packet(3, 0, {1, 2, 3, 4, 5, 6, 7, 8});
  for (std::size_t i = 0; i + 1 < pkt.size(); ++i) {
    p.feed(&pkt[i], 1);
    EXPECT_FALSE(p.next()) << i;
  }
  p.feed(&pkt.back(), 1);
  auto s = p.next();
  ASSERT_TRUE(s);
  EXPECT_EQ(s->params.size(), 8u);
}

TEST(DxlParser, G4_BadChecksumRejectedThenRecovers) {
  StatusParser p;
  Bytes bad = make_packet(1, 0, {0x10, 0x20});
  bad.back() ^= 0x01;
  p.feed(bad);
  p.feed(make_packet(1, 0, {0x30}));
  auto s = p.next();
  ASSERT_TRUE(s);
  EXPECT_EQ(s->params, (Bytes{0x30}));
  EXPECT_EQ(p.bad_checksums(), 1u);
  EXPECT_FALSE(p.next());
}

TEST(DxlParser, G4_BadLengthRejected) {
  StatusParser p;
  p.feed(Bytes{0xFF, 0xFF, 0x01, 0x01, 0x00, 0xFD});  // LEN 1 < 2
  p.feed(Bytes{0xFF, 0xFF, 0x01, 0x00, 0xFE});        // LEN 0
  p.feed(make_packet(4, 0, {}));
  auto s = p.next();
  ASSERT_TRUE(s);
  EXPECT_EQ(s->id, 4);
  EXPECT_EQ(p.bad_lengths(), 2u);
}

TEST(DxlParser, TruncatedPacketWaitsAndResetClears) {
  StatusParser p;
  const Bytes pkt = make_packet(1, 0, {9, 9, 9});
  p.feed(pkt.data(), pkt.size() - 2);
  EXPECT_FALSE(p.next());
  EXPECT_GT(p.pending(), 0u);
  p.reset();
  EXPECT_EQ(p.pending(), 0u);
}

// Basit LCG: tekrarlanabilir sözde rastgele baytlar.
std::uint8_t lcg(std::uint32_t& s) {
  s = s * 1664525u + 1013904223u;
  return static_cast<std::uint8_t>(s >> 24);
}

TEST(DxlParser, G4_RandomStreamsNeverYieldInvalidPackets) {
  // Rastgele akış: çökme ya da istisna yok, çıkan paketler geçerli başlık/uzunlukta.
  for (std::uint32_t seed = 1; seed <= 200; ++seed) {
    std::uint32_t s = seed;
    StatusParser p;
    for (int chunk = 0; chunk < 40; ++chunk) {
      Bytes b(lcg(s) % 32);
      for (auto& x : b) x = (lcg(s) % 4 == 0) ? 0xFF : lcg(s);
      p.feed(b);
      while (auto pkt = p.next()) {
        EXPECT_NE(pkt->id, 0xFF);
        EXPECT_LE(pkt->params.size(), kMaxParams);
      }
    }
    EXPECT_LE(p.pending(), 258u);  // tampon sınırsız büyümez (en çok bir aday paket)
  }
}

TEST(DxlParser, G4_ValidPacketsRecoveredFromGarbageWithoutHeaders) {
  // Başlık içermeyen çöp arasına gömülü tüm geçerli paketler sırayla çıkar.
  std::uint32_t s = 42;
  StatusParser p;
  std::vector<int> want;
  for (int k = 0; k < 300; ++k) {
    Bytes junk(lcg(s) % 9);
    for (auto& x : junk) x = lcg(s) % 0xFF;  // 0xFF yok
    p.feed(junk);
    const int id = lcg(s) % 254;
    p.feed(make_packet(static_cast<std::uint8_t>(id), 0, Bytes(lcg(s) % 6, 0x11)));
    want.push_back(id);
  }
  std::vector<int> got;
  while (auto pkt = p.next()) got.push_back(pkt->id);
  EXPECT_EQ(got, want);
}

// --- İşlem katmanı (Bus) ---

TEST(DxlBus, PingReadWriteAgainstFake) {
  FakeServoBus fake({1});
  Bus bus(fake, {});
  EXPECT_TRUE(bus.ping(1).ok());
  BusResult r = bus.read(1, ax12::kModelNumber, 2);
  ASSERT_TRUE(r.ok());
  EXPECT_EQ(get_le16(r.data.data()), 12);
  EXPECT_TRUE(bus.write(1, ax12::kMovingSpeed, le16(100)).ok());
  EXPECT_EQ(fake.servo(1).u16(ax12::kMovingSpeed), 100);
  EXPECT_GE(fake.flushes(), 3);  // her işlemden önce eski baytlar atılır
  EXPECT_EQ(std::string(bus_error_name(BusError::kNone)), "yok");
}

TEST(DxlBus, BroadcastAndSyncWriteExpectNoReply) {
  FakeServoBus fake({1, 2});
  Bus bus(fake, {});
  EXPECT_TRUE(bus.ping(kBroadcastId).ok());
  EXPECT_TRUE(bus.write(kBroadcastId, ax12::kTorqueEnable, {1}).ok());
  EXPECT_EQ(fake.servo(2).table[ax12::kTorqueEnable], 1);
  EXPECT_TRUE(bus.sync_write(ax12::kMovingSpeed, 2, {{1, le16(5)}, {2, le16(6)}}).ok());
  EXPECT_EQ(fake.servo(1).u16(ax12::kMovingSpeed), 5);
  EXPECT_EQ(fake.servo(2).u16(ax12::kMovingSpeed), 6);
}

TEST(DxlBus, TimeoutWhenNoServo) {
  FakeServoBus fake({1});
  Bus bus(fake, {});
  const BusResult r = bus.ping(9);
  EXPECT_EQ(r.error, BusError::kTimeout);
  EXPECT_EQ(r.describe(), "zaman aşımı");
}

TEST(DxlBus, ChecksumErrorWhenOnlyCorruptReply) {
  FakeServoBus fake({1});
  fake.servo(1).corrupt_checksum = true;
  Bus bus(fake, {});
  EXPECT_EQ(bus.read(1, ax12::kPresentPosition, 2).error, BusError::kChecksum);
  EXPECT_GT(bus.discarded_bytes(), 0u);
}

TEST(DxlBus, WrongIdServoErrorAndLength) {
  FakeServoBus fake({1, 2, 3});
  fake.servo(1).reply_as_id = 5;
  fake.servo(2).error_bits = kErrOverheating;
  fake.servo(3).extra_param_bytes = 1;
  Bus bus(fake, {});
  EXPECT_EQ(bus.ping(1).error, BusError::kWrongId);
  const BusResult r = bus.ping(2);
  EXPECT_EQ(r.error, BusError::kServoError);
  EXPECT_EQ(r.servo_error, kErrOverheating);
  EXPECT_EQ(r.describe(), "servo hatası (aşırı ısınma)");
  EXPECT_EQ(bus.read(3, ax12::kPresentPosition, 2).error, BusError::kLength);
}

TEST(DxlBus, GarbageBeforeReplyIsSkipped) {
  FakeServoBus fake({1});
  fake.inject_garbage({0x00, 0xFF, 0x13, 0xFF, 0xFF, 0xFF});
  Bus bus(fake, {});
  EXPECT_TRUE(bus.read(1, ax12::kPresentPosition, 2).ok());
}

TEST(DxlBus, WriteFailureReported) {
  FakeServoBus fake({1});
  fake.set_write_fails(true);
  Bus bus(fake, {});
  EXPECT_EQ(bus.ping(1).error, BusError::kWriteFailed);
  EXPECT_EQ(bus.sync_write(ax12::kGoalPosition, 2, {{1, le16(1)}}).error, BusError::kWriteFailed);
}

TEST(DxlBus, LocalEchoConsumedAndVerified) {
  FakeServoBus fake({1});
  fake.set_echo(true);
  BusOptions o;
  o.local_echo = true;
  Bus bus(fake, o);
  EXPECT_TRUE(bus.read(1, ax12::kPresentPosition, 2).ok());
  EXPECT_TRUE(bus.sync_write(ax12::kGoalPosition, 2, {{1, le16(1)}}).ok());
  // Yankı yoksa (hat ya da yön sorunu) hata.
  fake.set_echo(false);
  EXPECT_EQ(bus.ping(1).error, BusError::kEcho);
}

// Elle yazılmış yanıt akışı veren port: yankı uyuşmazlığı ve bölünmüş yanıt.
class ScriptedPort : public SerialPort {
 public:
  std::deque<Bytes> chunks;
  bool write(const std::uint8_t*, std::size_t) override { return true; }
  std::size_t read(std::uint8_t* buf, std::size_t max, int) override {
    if (chunks.empty()) return 0;
    Bytes c = chunks.front();
    chunks.pop_front();
    const std::size_t n = std::min(max, c.size());
    std::copy(c.begin(), c.begin() + static_cast<std::ptrdiff_t>(n), buf);
    return n;
  }
  void flush_input() override {}
};

TEST(DxlBus, EchoMismatchAndSplitReply) {
  ScriptedPort port;
  BusOptions o;
  o.local_echo = true;
  Bus echo_bus(port, o);
  Bytes wrong = make_ping(1);
  wrong[2] = 2;
  port.chunks = {wrong};
  EXPECT_EQ(echo_bus.ping(1).error, BusError::kEcho);

  Bus bus(port, {});
  const Bytes reply = make_packet(1, 0, {0x10, 0x00});
  port.chunks = {Bytes(reply.begin(), reply.begin() + 3), Bytes(reply.begin() + 3, reply.end())};
  const BusResult r = bus.read(1, ax12::kPresentPosition, 2);
  ASSERT_TRUE(r.ok());
  EXPECT_EQ(r.data, (Bytes{0x10, 0x00}));
}

TEST(DxlBus, WriteWithoutRepliesAtStatusLevelOne) {
  FakeServoBus fake({1});
  fake.servo(1).table[ax12::kStatusReturnLevel] = 1;
  BusOptions o;
  o.write_replies = false;
  Bus bus(fake, o);
  EXPECT_TRUE(bus.write(1, ax12::kMovingSpeed, le16(7)).ok());
  EXPECT_EQ(fake.servo(1).u16(ax12::kMovingSpeed), 7);
  EXPECT_TRUE(bus.read(1, ax12::kMovingSpeed, 2).ok());
}

TEST(DxlBus, BusErrorNamesAreDistinct) {
  const BusError all[] = {BusError::kNone,    BusError::kWriteFailed, BusError::kEcho,
                          BusError::kTimeout, BusError::kChecksum,    BusError::kWrongId,
                          BusError::kLength,  BusError::kServoError};
  for (std::size_t i = 0; i < std::size(all); ++i) {
    for (std::size_t k = i + 1; k < std::size(all); ++k)
      EXPECT_STRNE(bus_error_name(all[i]), bus_error_name(all[k]));
  }
}

TEST(FakeServoBus, RangeAndInstructionErrorsAndBadChecksum) {
  FakeServoBus fake({1});
  Bus bus(fake, {});
  EXPECT_EQ(bus.read(1, 0x30, 4).servo_error, kErrRange);
  EXPECT_EQ(bus.write(1, 0x31, {1, 2}).servo_error, kErrRange);
  fake.write(make_packet(1, 0x55, {}).data(), 6);  // bilinmeyen komut
  std::uint8_t buf[16];
  StatusParser p;
  p.feed(buf, fake.read(buf, sizeof buf, 0));
  auto s = p.next();
  ASSERT_TRUE(s);
  EXPECT_EQ(s->error, kErrInstruction);
  Bytes bad = make_ping(1);
  bad.back() ^= 0xFF;
  fake.write(bad.data(), bad.size());
  p.feed(buf, fake.read(buf, sizeof buf, 0));
  s = p.next();
  ASSERT_TRUE(s);
  EXPECT_EQ(s->error, kErrChecksum);
  EXPECT_THROW(fake.servo(99), std::out_of_range);
}

}  // namespace
}  // namespace delta_edge::dxl
