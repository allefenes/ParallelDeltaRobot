// Ax12Driver: FakeServoBus üzerinde ilklendirme, durum okuma, hedef (Sync Write, kırpma, NaN),
// tork sırası (Goal = Present önce), hata enjeksiyonu -> ok=false ve EdgeCore ile birlikte.
#include <gtest/gtest.h>

#include <cmath>
#include <filesystem>
#include <fstream>
#include <limits>
#include <string>

#include "delta_edge/ax12_driver.hpp"
#include "delta_edge/edge.hpp"
#include "delta_edge/faults.hpp"
#include "delta_edge/mock_driver.hpp"
#include "fake_servo_bus.hpp"
#include "test_util.hpp"

namespace delta_edge {
namespace {

using test::FakeServoBus;
namespace reg = dxl::ax12;

constexpr double kNaN = std::numeric_limits<double>::quiet_NaN();

struct Rig {
  FakeServoBus bus{{1, 2, 3}};
  MotorConfig cfg{};
  NullMagnetOutput magnet;
  Ax12Driver drv{bus, cfg, magnet};
};

int sync_goal_writes(const FakeServoBus& b) { return b.count(dxl::kSyncWrite, reg::kGoalPosition); }

TEST(Ax12Driver, InitializeConfiguresServosOnce) {
  Rig r;
  EXPECT_EQ(r.drv.initialize(), "");
  EXPECT_TRUE(r.drv.initialized());
  for (int id : {1, 2, 3}) {
    const auto& s = r.bus.servo(id);
    EXPECT_EQ(s.u16(reg::kCwAngleLimit), 138);  // eklem penceresi (G1 donanım tarafı)
    EXPECT_EQ(s.u16(reg::kCcwAngleLimit), 888);
    EXPECT_EQ(s.table[reg::kReturnDelay], 50);  // 100 us / 2
    EXPECT_EQ(s.u16(reg::kMovingSpeed), 0);
  }
  const int eeprom_writes = r.bus.count(dxl::kWriteData, reg::kCwAngleLimit) +
                            r.bus.count(dxl::kWriteData, reg::kReturnDelay);
  EXPECT_EQ(eeprom_writes, 6);
  // İkinci ilklendirme EEPROM'u yeniden yazmaz (değerler aynı).
  EXPECT_EQ(r.drv.initialize(), "");
  EXPECT_EQ(r.bus.count(dxl::kWriteData, reg::kCwAngleLimit) +
                r.bus.count(dxl::kWriteData, reg::kReturnDelay),
            eeprom_writes);
}

TEST(Ax12Driver, InitializeWithoutAngleLimitWrites) {
  Rig r;
  r.cfg.write_angle_limits = false;
  Ax12Driver d(r.bus, r.cfg, r.magnet);
  EXPECT_EQ(d.initialize(), "");
  EXPECT_EQ(r.bus.servo(1).u16(reg::kCcwAngleLimit), 1023);
}

TEST(Ax12Driver, InitializeFixesStatusReturnLevel) {
  Rig r;
  r.bus.servo(2).table[reg::kStatusReturnLevel] = 1;
  EXPECT_EQ(r.drv.initialize(), "");
  EXPECT_EQ(r.bus.servo(2).table[reg::kStatusReturnLevel], 2);
}

TEST(Ax12Driver, InitializeReportsMissingWrongModelAndFailedWrites) {
  {
    Rig r;
    r.bus.servo(3).drop_replies = -1;
    const std::string e = r.drv.initialize();
    EXPECT_NE(e.find("servo 3 (ID 3): ping: zaman aşımı"), std::string::npos) << e;
    EXPECT_FALSE(r.drv.initialized());
  }
  {
    Rig r;
    r.bus.servo(1).set_u16(reg::kModelNumber, 29);  // MX-28
    EXPECT_NE(r.drv.initialize().find("model numarası 29"), std::string::npos);
  }
}

// İlk N işlemden sonra hiçbir yanıtı geçirmeyen port sarmalı (adım adım hata).
class CutAfter : public SerialPort {
 public:
  CutAfter(FakeServoBus& inner, int writes) : inner_(inner), left_(writes) {}
  bool write(const std::uint8_t* d, std::size_t n) override {
    --left_;
    return inner_.write(d, n);
  }
  std::size_t read(std::uint8_t* b, std::size_t m, int t) override {
    return left_ >= 0 ? inner_.read(b, m, t) : 0;
  }
  void flush_input() override { inner_.flush_input(); }

 private:
  FakeServoBus& inner_;
  int left_;
};

TEST(Ax12Driver, InitializeFailsCleanlyAtEveryStep) {
  // Servo 1'in ilklendirmesi: ping, model, srl oku, (srl yaz, srl oku), delay oku, delay yaz,
  // limit oku, limit yaz, speed yaz = 10 işlem. Her kesme noktasında hata metni dolu döner.
  for (int cut = 0; cut < 10; ++cut) {
    FakeServoBus bus({1, 2, 3});
    bus.servo(1).table[reg::kStatusReturnLevel] = 1;
    bus.servo(1).table[reg::kReturnDelay] = 0;
    CutAfter port(bus, cut);
    MotorConfig cfg;
    NullMagnetOutput m;
    Ax12Driver d(port, cfg, m);
    const std::string e = d.initialize();
    EXPECT_NE(e, "") << cut;
    EXPECT_NE(e.find("servo 1"), std::string::npos) << cut << ": " << e;
  }
}

TEST(Ax12Driver, G9_ReadStateConvertsUnits) {
  Rig r;
  auto& s1 = r.bus.servo(1);
  s1.set_u16(reg::kPresentPosition, 512);      // θ = 136 * 300/1024 = 39.84375
  s1.set_u16(reg::kPresentLoad, 0x400 | 500);  // CW, 50 %
  s1.table[reg::kPresentVoltage] = 118;
  s1.table[reg::kPresentTemperature] = 41;
  r.bus.servo(2).set_u16(reg::kPresentPosition, 138);
  r.bus.servo(2).set_u16(reg::kPresentLoad, 250);  // CCW, 25 %
  const DriverState st = r.drv.read_state();
  EXPECT_TRUE(st.ok);
  EXPECT_DOUBLE_EQ(st.angles[0], 39.84375);
  EXPECT_DOUBLE_EQ(st.loads_pct[0], -50.0);
  EXPECT_DOUBLE_EQ(st.voltages_v[0], 11.8);
  EXPECT_DOUBLE_EQ(st.temps_c[0], 41.0);
  EXPECT_NEAR(st.angles[1], -69.7265625, 1e-12);
  EXPECT_DOUBLE_EQ(st.loads_pct[1], 25.0);
  EXPECT_DOUBLE_EQ(st.voltages_v[2], 12.0);
  EXPECT_DOUBLE_EQ(st.temps_c[2], 30.0);
}

TEST(Ax12Driver, G9_LoadSignFollowsJointDirection) {
  Rig r;
  r.cfg.joints[0] = {1, 700.0, -1};
  Ax12Driver d(r.bus, r.cfg, r.magnet);
  r.bus.servo(1).set_u16(reg::kPresentLoad, 0x400 | 100);  // CW = tick azalan = θ artan
  r.bus.servo(1).set_u16(reg::kPresentPosition, 600);
  const DriverState st = d.read_state();
  EXPECT_DOUBLE_EQ(st.loads_pct[0], 10.0);
  EXPECT_DOUBLE_EQ(st.angles[0], 100 * 300.0 / 1024);
}

TEST(Ax12Driver, G9_FaultInjectionMakesReadNotOk) {
  const auto not_ok = [](auto inject) {
    Rig r;
    EXPECT_TRUE(r.drv.read_state().ok);
    inject(r.bus);
    const DriverState s = r.drv.read_state();
    return !s.ok;
  };
  EXPECT_TRUE(not_ok([](FakeServoBus& b) { b.servo(2).drop_replies = 1; }));  // zaman aşımı
  EXPECT_TRUE(not_ok([](FakeServoBus& b) { b.servo(1).corrupt_checksum = true; }));
  EXPECT_TRUE(not_ok([](FakeServoBus& b) { b.servo(3).error_bits = dxl::kErrOverheating; }));
  EXPECT_TRUE(not_ok([](FakeServoBus& b) { b.servo(3).error_bits = dxl::kErrInputVoltage; }));
  EXPECT_TRUE(not_ok([](FakeServoBus& b) { b.servo(1).error_bits = dxl::kErrOverload; }));
  EXPECT_TRUE(not_ok([](FakeServoBus& b) { b.servo(2).reply_as_id = 3; }));  // yanlış ID
  EXPECT_TRUE(not_ok([](FakeServoBus& b) { b.servo(2).extra_param_bytes = 2; }));
  EXPECT_TRUE(not_ok([](FakeServoBus& b) { b.set_write_fails(true); }));
  // Çöp bayt tek başına hata değildir: ayrıştırıcı yeniden eşlenir.
  EXPECT_FALSE(not_ok([](FakeServoBus& b) { b.inject_garbage({0x00, 0xFF, 0x01}); }));
}

TEST(Ax12Driver, G4_FailedReadKeepsLastFiniteValues) {
  Rig r;
  r.bus.servo(2).set_u16(reg::kPresentPosition, 600);
  const DriverState good = r.drv.read_state();
  r.bus.servo(2).drop_replies = -1;
  const DriverState bad = r.drv.read_state();
  EXPECT_FALSE(bad.ok);
  EXPECT_DOUBLE_EQ(bad.angles[1], good.angles[1]);
  for (int j = 0; j < 3; ++j) EXPECT_TRUE(std::isfinite(bad.angles[j]));
  EXPECT_NE(r.drv.last_error().find("servo 2 (ID 2): durum okuma"), std::string::npos);
  r.bus.servo(2).drop_replies = 0;
  EXPECT_TRUE(r.drv.read_state().ok);  // yapışkan değil: hat düzelince ok
}

TEST(Ax12Driver, G1_TorqueOnWritesGoalEqualsPresentBeforeEnable) {
  Rig r;
  const int present[] = {300, 400, 500};
  for (int j = 0; j < 3; ++j) {
    r.bus.servo(j + 1).set_u16(reg::kPresentPosition, present[j]);
    r.bus.servo(j + 1).set_u16(reg::kGoalPosition, 880);  // eski, uzak hedef
  }
  r.bus.goal_enables_torque = false;
  r.bus.clear_log();
  r.drv.set_torque(true);
  ASSERT_TRUE(r.drv.torque_on());
  for (int j = 0; j < 3; ++j) {
    const auto& s = r.bus.servo(j + 1);
    EXPECT_EQ(s.u16(reg::kGoalPosition), present[j]);  // sıçrama yok
    EXPECT_EQ(s.table[reg::kTorqueEnable], 1);
  }
  // Sıra: Goal = Present Sync Write, tüm Torque Enable yazımlarından önce.
  int goal_at = -1;
  int first_torque = -1;
  const auto& log = r.bus.log();
  for (int i = 0; i < static_cast<int>(log.size()); ++i) {
    const auto& in = log[static_cast<std::size_t>(i)];
    if (in.instr == dxl::kSyncWrite && in.params[0] == reg::kGoalPosition && goal_at < 0)
      goal_at = i;
    if (in.instr == dxl::kWriteData && in.params[0] == reg::kTorqueEnable && first_torque < 0)
      first_torque = i;
  }
  ASSERT_GE(goal_at, 0);
  ASSERT_GE(first_torque, 0);
  EXPECT_LT(goal_at, first_torque);
  EXPECT_EQ(r.bus.count(dxl::kWriteData, reg::kTorqueEnable), 3);
  EXPECT_TRUE(r.drv.read_state().ok);
}

TEST(Ax12Driver, GoalNotSentWhileTorqueOff) {
  Rig r;
  r.drv.set_goal({10, 20, 30});
  EXPECT_EQ(sync_goal_writes(r.bus), 0);
  EXPECT_EQ(r.bus.servo(1).table[reg::kTorqueEnable], 0);  // Goal yazımı torku açmadı
  EXPECT_EQ(r.drv.goals_sent(), 0);
}

TEST(Ax12Driver, G1_SetGoalIsOneClampedSyncWrite) {
  Rig r;
  r.drv.set_torque(true);
  r.bus.clear_log();
  r.drv.set_goal({500.0, -500.0, 0.0});
  ASSERT_EQ(r.bus.log().size(), 1u);  // tek paket, üç servo
  const auto& in = r.bus.log()[0];
  EXPECT_EQ(in.id, dxl::kBroadcastId);
  EXPECT_EQ(in.instr, dxl::kSyncWrite);
  EXPECT_EQ(in.params[0], reg::kGoalPosition);
  EXPECT_EQ(in.params[1], 2);
  ASSERT_EQ(in.params.size(), 2u + 3u * 3u);
  EXPECT_EQ(r.bus.servo(1).u16(reg::kGoalPosition), 888);  // 150 deg'e kırpıldı
  EXPECT_EQ(r.bus.servo(2).u16(reg::kGoalPosition), 138);  // -70 deg'e kırpıldı
  EXPECT_EQ(r.bus.servo(3).u16(reg::kGoalPosition), 376);  // θ = 0
  EXPECT_EQ(r.drv.goals_sent(), 1);
}

TEST(Ax12Driver, G4_NonFiniteGoalNeverSent) {
  Rig r;
  r.drv.set_torque(true);
  r.drv.set_goal({1.0, 2.0, 3.0});
  const int before = sync_goal_writes(r.bus);
  const int g1 = r.bus.servo(1).u16(reg::kGoalPosition);
  r.drv.set_goal({kNaN, 0.0, 0.0});
  r.drv.set_goal({0.0, std::numeric_limits<double>::infinity(), 0.0});
  r.drv.set_goal({0.0, 0.0, -std::numeric_limits<double>::infinity()});
  EXPECT_EQ(sync_goal_writes(r.bus), before);  // hiçbir eklem için paket yok
  EXPECT_EQ(r.bus.servo(1).u16(reg::kGoalPosition), g1);
  EXPECT_EQ(r.drv.goals_rejected(), 3);
}

TEST(Ax12Driver, GoalSendFailureReportedOnce) {
  Rig r;
  r.drv.set_torque(true);
  r.bus.set_write_fails(true);
  r.drv.set_goal({1, 1, 1});
  EXPECT_NE(r.drv.last_error().find("hedef gönderilemedi"), std::string::npos);
  r.bus.set_write_fails(false);
  EXPECT_FALSE(r.drv.read_state().ok);
  EXPECT_TRUE(r.drv.read_state().ok);
}

TEST(Ax12Driver, G9_FailedTorqueOnLeavesAllOffAndReportsNotOk) {
  for (int failing : {1, 2, 3}) {
    Rig r;
    ASSERT_EQ(r.drv.initialize(), "");
    r.bus.servo(failing).drop_replies = -1;
    r.drv.set_torque(true);
    EXPECT_FALSE(r.drv.torque_on());
    r.bus.servo(failing).drop_replies = 0;
    for (int id : {1, 2, 3}) EXPECT_EQ(r.bus.servo(id).table[reg::kTorqueEnable], 0) << failing;
    // Hat düzelse de başarılı bir tork komutuna dek ok=false (EdgeCore torku açmaz).
    EXPECT_FALSE(r.drv.read_state().ok);
    r.drv.set_torque(true);
    EXPECT_TRUE(r.drv.torque_on());
    EXPECT_TRUE(r.drv.read_state().ok);
  }
}

TEST(Ax12Driver, TorqueOnFailsWhenEnableWriteFails) {
  Rig r;
  ASSERT_EQ(r.drv.initialize(), "");
  r.bus.servo(3).error_bits = dxl::kErrOverload;  // okumalar da hata verir
  r.drv.set_torque(true);
  EXPECT_FALSE(r.drv.torque_on());
  EXPECT_NE(r.drv.last_error().find("servo 3"), std::string::npos);
}

TEST(Ax12Driver, TorqueOnRetriesInitialization) {
  Rig r;
  r.bus.servo(1).drop_replies = -1;
  EXPECT_NE(r.drv.initialize(), "");
  r.drv.set_torque(true);
  EXPECT_FALSE(r.drv.torque_on());
  r.bus.servo(1).drop_replies = 0;
  r.drv.set_torque(true);
  EXPECT_TRUE(r.drv.initialized());
  EXPECT_TRUE(r.drv.torque_on());
}

TEST(Ax12Driver, TorqueOnFailsWhenGoalSyncWriteFails) {
  Rig r;
  ASSERT_EQ(r.drv.initialize(), "");
  // Okumalar geçer, ilk yazma (Sync Write) başarısız: tork açılmaz.
  class FailSync : public SerialPort {
   public:
    explicit FailSync(FakeServoBus& b) : b_(b) {}
    bool write(const std::uint8_t* d, std::size_t n) override {
      if (n > 4 && d[4] == dxl::kSyncWrite) return false;
      return b_.write(d, n);
    }
    std::size_t read(std::uint8_t* x, std::size_t m, int t) override { return b_.read(x, m, t); }
    void flush_input() override { b_.flush_input(); }

   private:
    FakeServoBus& b_;
  } port(r.bus);
  Ax12Driver d(port, r.cfg, r.magnet);
  ASSERT_EQ(d.initialize(), "");
  d.set_torque(true);
  EXPECT_FALSE(d.torque_on());
  EXPECT_NE(d.last_error().find("goal = present"), std::string::npos);
}

TEST(Ax12Driver, TorqueOffBroadcastsThenVerifiesEach) {
  Rig r;
  r.drv.set_torque(true);
  r.bus.clear_log();
  r.drv.set_torque(false);
  EXPECT_FALSE(r.drv.torque_on());
  ASSERT_GE(r.bus.log().size(), 4u);
  EXPECT_EQ(r.bus.log()[0].id, dxl::kBroadcastId);
  for (int id : {1, 2, 3}) EXPECT_EQ(r.bus.servo(id).table[reg::kTorqueEnable], 0);
  EXPECT_TRUE(r.drv.read_state().ok);
  // Bir servo yanıt vermezse kapatma yine de denenir; okuma ok=false.
  r.bus.servo(2).drop_replies = 1;
  r.drv.set_torque(false);
  EXPECT_FALSE(r.drv.read_state().ok);
}

TEST(Ax12Driver, MagnetOutputs) {
  Rig r;
  r.drv.set_magnet(true);
  EXPECT_TRUE(r.magnet.on());
  r.drv.set_magnet(false);
  EXPECT_FALSE(r.magnet.on());

  const auto path = std::filesystem::temp_directory_path() / "delta_edge_magnet";
  FileMagnetOutput f(path.string());
  f.set(true);
  EXPECT_TRUE(f.last_write_ok());
  std::string v;
  std::ifstream(path) >> v;
  EXPECT_EQ(v, "1");
  f.set(false);
  std::ifstream(path) >> v;
  EXPECT_EQ(v, "0");
  FileMagnetOutput bad("/yok/dizin/magnet");
  bad.set(true);
  EXPECT_FALSE(bad.last_write_ok());
}

TEST(Ax12Driver, StatusReturnLevelOneSkipsWriteReplies) {
  FakeServoBus bus({1, 2, 3});
  for (int id : {1, 2, 3}) bus.servo(id).table[reg::kStatusReturnLevel] = 1;
  MotorConfig cfg;
  cfg.status_return_level = 1;
  NullMagnetOutput m;
  Ax12Driver d(bus, cfg, m);
  EXPECT_EQ(d.initialize(), "");
  d.set_torque(true);
  EXPECT_TRUE(d.torque_on());
  EXPECT_TRUE(d.read_state().ok);
}

// --- EdgeCore ile birlikte (G9: sürücü okunamıyorsa tork açılmaz) ---

TEST(Ax12Driver, G9_EdgeCoreRefusesTorqueWhenServoSilent) {
  Rig r;
  r.bus.servo(2).drop_replies = -1;
  MockEstop estop;
  EdgeCore core(EdgeLimits{}, r.drv, estop, 0);
  core.on_message(test::hb_msg(1), 0);
  const auto out = core.on_message(test::on_msg("torque", true), 0);
  EXPECT_TRUE(test::find_msg(out, "fault", fault::kDriver));
  EXPECT_EQ(core.state(), State::kTorqueOff);
  for (int id : {1, 3}) EXPECT_EQ(r.bus.servo(id).table[reg::kTorqueEnable], 0);
}

TEST(Ax12Driver, G1_EdgeCoreTorqueOnAndTrajectoryStayInsideWindow) {
  Rig r;
  for (int id : {1, 2, 3}) r.bus.servo(id).set_u16(reg::kPresentPosition, 376);  // θ = 0
  MockEstop estop;
  Micros now = 0;
  EdgeCore core(EdgeLimits{}, r.drv, estop, now);
  core.on_message(test::hb_msg(1), now);
  core.on_message(test::on_msg("torque", true), now);
  ASSERT_EQ(core.state(), State::kIdle);
  EXPECT_TRUE(r.drv.torque_on());
  const auto pts = test::smooth({0, 0, 0}, {150, -70, 30}, 2000, 10);
  const auto ack = core.on_message(test::traj_msg("t1", 10, pts), now);
  ASSERT_TRUE(test::find_msg(ack, "ack"));
  std::uint64_t seq = 2;
  for (int k = 0; k < 260; ++k) {
    now += 10 * kMicrosPerMs;
    if (k % 5 == 0) core.on_message(test::hb_msg(seq++), now);
    core.tick(now);
    for (int id : {1, 2, 3}) {
      const int g = r.bus.servo(id).u16(reg::kGoalPosition);
      EXPECT_GE(g, 138);
      EXPECT_LE(g, 888);
    }
  }
  EXPECT_EQ(r.bus.servo(1).u16(reg::kGoalPosition), 888);
  EXPECT_EQ(r.bus.servo(2).u16(reg::kGoalPosition), 138);
  EXPECT_EQ(core.state(), State::kIdle);
}

}  // namespace
}  // namespace delta_edge
