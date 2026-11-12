// EdgeCore uçtan uca (ağsız): durum makinesi, G1/G5/G6/G7/G8/G9, acil stop mandalı, kurtarma
// kuralları. Saat enjekte edilir; döngü 100 Hz (10 ms), sunucu kalp atışı 50 ms'de bir.
#include <gtest/gtest.h>

#include <cmath>
#include <functional>
#include <memory>

#include "delta_edge/edge.hpp"
#include "delta_edge/faults.hpp"
#include "delta_edge/mock_driver.hpp"
#include "test_util.hpp"

namespace delta_edge {
namespace {

using test::find_msg;
using test::json;
using Out = std::vector<std::string>;

constexpr Micros kMs = kMicrosPerMs;
constexpr Micros kTick = 10 * kMs;

void append(Out& a, const Out& b) { a.insert(a.end(), b.begin(), b.end()); }

class Edge : public ::testing::Test {
 protected:
  Micros now = 1000 * kMs;
  MockDriver drv{[this] { return now; }};
  MockEstop estop;
  EdgeLimits lim;
  std::unique_ptr<EdgeCore> core;
  std::uint64_t seq = 0;
  Micros last_hb = 0;

  void SetUp() override { core = std::make_unique<EdgeCore>(lim, drv, estop, now); }

  Out send(const std::string& m) { return core->on_message(m, now); }
  Out heartbeat() {
    last_hb = now;
    return send(test::hb_msg(++seq));
  }
  Out tick() {
    now += kTick;
    return core->tick(now);
  }
  // ms süre boyunca 10 ms döngü; hb_ms > 0 ise o aralıkla kalp atışı.
  Out run(int ms, int hb_ms = 50) {
    Out all;
    const Micros end = now + ms * kMs;
    while (now < end) {
      now += kTick;
      if (hb_ms > 0 && (now / kMs) % hb_ms == 0) append(all, heartbeat());
      append(all, core->tick(now));
    }
    return all;
  }
  void arm() {
    heartbeat();
    const Out o = send(test::on_msg("torque", true));
    ASSERT_TRUE(o.empty()) << o[0];
    ASSERT_EQ(core->state(), State::kIdle);
    run(20);
  }
  State state() const { return core->state(); }
};

// ---------------- açılış ve kurtarma ----------------

TEST_F(Edge, BootsTorqueOffMagnetOff) {
  EXPECT_EQ(state(), State::kTorqueOff);
  EXPECT_FALSE(drv.torque());
  EXPECT_FALSE(drv.magnet());
  const Out o = run(100, 0);
  EXPECT_EQ(state(), State::kTorqueOff);
  const auto t = find_msg(o, "telemetry");
  ASSERT_TRUE(t);
  EXPECT_EQ((*t)["state"], "TORQUE_OFF");
  EXPECT_EQ(drv.goal_count(), 0);  // tork kapalıyken hedef gönderilmez
}

TEST_F(Edge, Recovery_TorqueOnRequiresFreshHeartbeat) {
  Out o = send(test::on_msg("torque", true));
  EXPECT_TRUE(find_msg(o, "fault", fault::kHeartbeatRequired));
  EXPECT_EQ(state(), State::kTorqueOff);
  EXPECT_FALSE(drv.torque());
  heartbeat();
  o = send(test::on_msg("torque", true));
  EXPECT_TRUE(o.empty());
  EXPECT_EQ(state(), State::kIdle);
  EXPECT_TRUE(drv.torque());
  // Tork açılmadan önce hedef = ölçülen konum.
  EXPECT_EQ(drv.goal(), drv.position());
}

TEST_F(Edge, Recovery_StaleHeartbeatIsNotFresh) {
  heartbeat();
  run(195, 0);  // T_stop - 1 döngü eşiği aşıldı
  const Out o = send(test::on_msg("torque", true));
  EXPECT_TRUE(find_msg(o, "fault", fault::kHeartbeatRequired));
  EXPECT_EQ(state(), State::kTorqueOff);
}

TEST_F(Edge, TorqueOnWhenAlreadyRunningIsNoop) {
  arm();
  EXPECT_TRUE(send(test::on_msg("torque", true)).empty());
  EXPECT_EQ(state(), State::kIdle);
}

TEST_F(Edge, ParseErrorReportedStateUnchanged) {
  arm();
  const Out o = send("{bozuk");
  const auto f = find_msg(o, "fault", fault::kParseError);
  ASSERT_TRUE(f);
  EXPECT_EQ(state(), State::kIdle);
}

// ---------------- G8 + oynatma ----------------

TEST_F(Edge, G8_ValidTrajectoryAckedAndPlayed) {
  arm();
  const Angles target{60, -30, 45};
  const auto pts = test::smooth({0, 0, 0}, target, 1000, 10);
  Out o = send(test::traj_msg("t-ok", 10, pts));
  const auto ack = find_msg(o, "ack");
  ASSERT_TRUE(ack);
  EXPECT_EQ((*ack)["id"], "t-ok");
  EXPECT_EQ(state(), State::kRunning);
  o = run(500);
  const auto tel = find_msg(o, "telemetry");
  ASSERT_TRUE(tel);
  EXPECT_EQ((*tel)["state"], "RUNNING");
  EXPECT_EQ((*tel)["traj_id"], "t-ok");
  EXPECT_GT((*tel)["index"].get<int>(), 0);
  run(600);
  EXPECT_EQ(state(), State::kIdle);
  for (int j = 0; j < 3; ++j) EXPECT_NEAR(drv.position()[j], target[j], 0.05);
}

TEST_F(Edge, G8_JointLimitTrajectoryNeverStarts) {
  arm();
  auto pts = test::smooth({0, 0, 0}, {149.9, 0, 0}, 3000, 10);
  pts.back()[0] = 150.5;  // son nokta sınır dışında; hareketin başı geçerli olsa da başlamaz
  const long long goals_before = drv.goal_count();
  const Out o = send(test::traj_msg("t-bad", 10, pts));
  const auto f = find_msg(o, "fault", fault::kJointLimit);
  ASSERT_TRUE(f);
  const std::string detail = (*f)["detail"];
  EXPECT_NE(detail.find("t-bad"), std::string::npos) << detail;
  EXPECT_NE(detail.find("reddedildi"), std::string::npos) << detail;
  EXPECT_NE(detail.find("nokta 300"), std::string::npos) << detail;
  EXPECT_FALSE(find_msg(o, "ack"));
  EXPECT_EQ(state(), State::kIdle);
  const Out later = run(500);
  EXPECT_EQ(state(), State::kIdle);
  EXPECT_GT(drv.goal_count(), goals_before);  // tutma hedefi gönderiliyor...
  EXPECT_NEAR(drv.max_goal()[0], 0.0, 1e-9);  // ...ama hiç hareket yok
  EXPECT_NEAR(drv.position()[0], 0.0, 1e-9);
  const auto tel = find_msg(later, "telemetry");
  ASSERT_TRUE(tel);
  EXPECT_TRUE((*tel)["traj_id"].is_null());
}

TEST_F(Edge, G8_G5_VelocityAndFirstPointJumpRejected) {
  arm();
  // 0.2 s'de 60 deg: tepe 471 deg/s. Örnek sırasıyla önce ivme sınırı aşılır; ikisi de G5'tir.
  Out o = send(test::traj_msg("fast", 10, test::smooth({0, 0, 0}, {60, 0, 0}, 200, 10)));
  EXPECT_TRUE(find_msg(o, "fault", fault::kVelocity) || find_msg(o, "fault", fault::kAccel));
  EXPECT_EQ(state(), State::kIdle);
  // Robot 0'da, yörünge 30 deg'den başlıyor: ilk nokta sıçraması.
  o = send(test::traj_msg("jump", 10, test::smooth({30, 0, 0}, {40, 0, 0}, 1000, 10)));
  const auto f = find_msg(o, "fault", fault::kVelocity);
  ASSERT_TRUE(f);
  EXPECT_NE((*f)["detail"].get<std::string>().find("ilk nokta"), std::string::npos);
  EXPECT_EQ(state(), State::kIdle);
  run(200);
  EXPECT_NEAR(drv.max_goal()[0], 0.0, 1e-9);
}

TEST_F(Edge, G8_TrajectoryOnlyAcceptedInIdle) {
  const auto pts = test::smooth({0, 0, 0}, {30, 0, 0}, 1000, 10);
  heartbeat();
  Out o = send(test::traj_msg("off", 10, pts));  // TORQUE_OFF
  EXPECT_TRUE(find_msg(o, "fault", fault::kNotReady));
  arm();
  ASSERT_TRUE(find_msg(send(test::traj_msg("a", 10, pts)), "ack"));
  o = send(test::traj_msg("b", 10, pts));  // RUNNING
  const auto f = find_msg(o, "fault", fault::kNotReady);
  ASSERT_TRUE(f);
  EXPECT_NE((*f)["detail"].get<std::string>().find("RUNNING"), std::string::npos);
  EXPECT_EQ(state(), State::kRunning);
  send(test::simple_msg("hold"));
  EXPECT_TRUE(find_msg(send(test::traj_msg("c", 10, pts)), "fault", fault::kNotReady));
}

TEST_F(Edge, G8_TrajectoryNeedsFreshHeartbeatAndHealth) {
  arm();
  const auto pts = test::smooth({0, 0, 0}, {30, 0, 0}, 1000, 10);
  // Döngü henüz HOLD'a geçmeden mesaj gelirse de taze kalp atışı aranır.
  now = last_hb + 195 * kMs;
  EXPECT_TRUE(find_msg(send(test::traj_msg("x", 10, pts)), "fault", fault::kHeartbeatRequired));
  heartbeat();
  drv.inject_voltage(8.0);
  EXPECT_TRUE(find_msg(send(test::traj_msg("y", 10, pts)), "fault", fault::kVoltage));
  EXPECT_EQ(state(), State::kIdle);
}

// ---------------- G1 ----------------

TEST_F(Edge, G1_LimitEdgesReachableNothingBeyondReachesDriver) {
  arm();
  const Angles edge{150.0, -70.0, 150.0};
  const auto pts = test::smooth({0, 0, 0}, edge, 3000, 10);
  ASSERT_TRUE(find_msg(send(test::traj_msg("edge", 10, pts)), "ack"));
  run(3200);
  EXPECT_EQ(state(), State::kIdle);
  for (int j = 0; j < 3; ++j) {
    EXPECT_GE(drv.min_goal()[j], -70.0);
    EXPECT_LE(drv.max_goal()[j], 150.0);
    EXPECT_NEAR(drv.position()[j], edge[j], 0.05);
  }
}

// ---------------- G6 ----------------

TEST_F(Edge, G6_HeartbeatLossMidTrajectoryHoldsWithinTStop) {
  arm();
  const auto pts = test::smooth({0, 0, 0}, {90, -45, 60}, 2000, 10);
  ASSERT_TRUE(find_msg(send(test::traj_msg("long", 10, pts)), "ack"));
  run(500);  // hareketin ortası, kalp atışları geliyor
  ASSERT_EQ(state(), State::kRunning);
  const Micros t_last = last_hb;
  const Angles before = drv.position();
  Micros t_hold = 0;
  Out hold_out;
  while (state() == State::kRunning && now - t_last < 1000 * kMs) {
    hold_out = tick();
    if (state() == State::kHolding) t_hold = now;
  }
  ASSERT_EQ(state(), State::kHolding);
  EXPECT_LE(t_hold - t_last, lim.t_stop_ms * kMs);  // en geç T_stop
  EXPECT_GE(t_hold - t_last, lim.t_stop_ms * kMs - kTick);
  EXPECT_TRUE(find_msg(hold_out, "fault", fault::kHeartbeatHold));
  EXPECT_GT(std::abs(drv.position()[0] - before[0]), 1.0);  // gerçekten hareket ediyordu
  // Tutma hedefi = HOLD anındaki ölçülen konum (hareketin ortasında dondurma).
  const Angles held = core->hold_target();
  EXPECT_TRUE(drv.torque());
  run(150, 0);  // hâlâ kalp atışı yok, T_off'a gelmedi
  ASSERT_EQ(state(), State::kHolding);
  for (int j = 0; j < 3; ++j) {
    EXPECT_DOUBLE_EQ(drv.goal()[j], held[j]);
    EXPECT_NEAR(drv.position()[j], held[j], 0.5);
  }
}

TEST_F(Edge, G6_HeartbeatReturnDoesNotResumeTrajectory) {
  arm();
  const auto pts = test::smooth({0, 0, 0}, {90, 0, 0}, 2000, 10);
  ASSERT_TRUE(find_msg(send(test::traj_msg("r", 10, pts)), "ack"));
  run(400);
  run(250, 0);
  ASSERT_EQ(state(), State::kHolding);
  const Angles held = core->hold_target();
  run(300);  // kalp atışı geri geldi
  EXPECT_EQ(state(), State::kHolding);
  EXPECT_NEAR(drv.position()[0], held[0], 0.5);
  // Kurtarma: açık torque on; eski yörünge devam etmez.
  EXPECT_TRUE(send(test::on_msg("torque", true)).empty());
  EXPECT_EQ(state(), State::kIdle);
  run(500);
  EXPECT_NEAR(drv.position()[0], held[0], 0.5);
}

TEST_F(Edge, G6_HoldAlsoWhenIdle) {
  arm();
  const Micros t_last = last_hb;
  Out o;
  while (state() == State::kIdle) append(o, tick());
  EXPECT_EQ(state(), State::kHolding);
  EXPECT_LE(now - t_last, lim.t_stop_ms * kMs);
  EXPECT_TRUE(find_msg(o, "fault", fault::kHeartbeatHold));
}

TEST_F(Edge, G6_ReplayedHeartbeatDoesNotKeepAlive) {
  arm();
  const Micros t_last = last_hb;
  const std::string same = test::hb_msg(seq);  // aynı seq tekrar tekrar
  while (state() == State::kIdle && now - t_last < 500 * kMs) {
    send(same);
    tick();
  }
  EXPECT_EQ(state(), State::kHolding);
  EXPECT_LE(now - t_last, lim.t_stop_ms * kMs);
}

TEST_F(Edge, NewConnectionResetsHeartbeatSequence) {
  arm();
  core->on_connection_open();
  seq = 0;  // sunucu yeniden başladı: seq 1'den
  run(500);
  EXPECT_EQ(state(), State::kIdle);
}

// ---------------- G7 ----------------

TEST_F(Edge, G7_TorqueOffAndMagnetOffAfterTOff) {
  arm();
  const auto pts = test::smooth({0, 0, 0}, {60, 0, 0}, 3000, 10);
  ASSERT_TRUE(find_msg(send(test::traj_msg("m", 10, pts, true)), "ack"));
  EXPECT_TRUE(drv.magnet());
  run(300);
  const Micros t_last = last_hb;
  Micros t_off = 0;
  Out off_out;
  while (state() != State::kTorqueOff && now - t_last < 2000 * kMs) {
    const Out o = tick();
    if (state() == State::kHolding) {
      EXPECT_TRUE(drv.torque());  // T_stop..T_off arası: tutuyor, parça mıknatısta
      EXPECT_TRUE(drv.magnet());
    }
    if (state() == State::kTorqueOff) {
      t_off = now;
      off_out = o;
    }
  }
  ASSERT_EQ(state(), State::kTorqueOff);
  EXPECT_LE(t_off - t_last, lim.t_off_ms * kMs);  // en geç T_off
  EXPECT_GE(t_off - t_last, lim.t_off_ms * kMs - kTick);
  EXPECT_FALSE(drv.torque());
  EXPECT_FALSE(drv.magnet());  // tanımlı güvenli durum: KAPALI
  EXPECT_TRUE(find_msg(off_out, "fault", fault::kHeartbeatOff));
  const long long goals = drv.goal_count();
  run(500, 0);
  EXPECT_EQ(drv.goal_count(), goals);  // tork kapalıyken hedef gönderilmez
}

TEST_F(Edge, G7_RecoveryAfterTOffNeedsFreshHeartbeatAndTorqueOn) {
  arm();
  run(1100, 0);
  ASSERT_EQ(state(), State::kTorqueOff);
  // Yalnız kalp atışı yetmez.
  run(300);
  EXPECT_EQ(state(), State::kTorqueOff);
  EXPECT_FALSE(drv.torque());
  // Yalnız torque on da yetmez (kalp atışı bayat).
  run(300, 0);
  EXPECT_TRUE(find_msg(send(test::on_msg("torque", true)), "fault", fault::kHeartbeatRequired));
  EXPECT_EQ(state(), State::kTorqueOff);
  // İkisi birlikte.
  heartbeat();
  EXPECT_TRUE(send(test::on_msg("torque", true)).empty());
  EXPECT_EQ(state(), State::kIdle);
  EXPECT_TRUE(drv.torque());
  EXPECT_FALSE(drv.magnet());  // mıknatıs kendiliğinden açılmaz
}

TEST_F(Edge, G7_FaultStateAlsoTurnsTorqueOffAfterTOff) {
  arm();
  drv.inject_temperature(0, 80.0);
  tick();
  ASSERT_EQ(state(), State::kFault);
  run(1100, 0);
  EXPECT_EQ(state(), State::kTorqueOff);
  EXPECT_FALSE(drv.torque());
}

// ---------------- komutlar ----------------

TEST_F(Edge, StopMidTrajectoryHoldsAndAcceptsNext) {
  arm();
  ASSERT_TRUE(find_msg(
      send(test::traj_msg("s1", 10, test::smooth({0, 0, 0}, {60, 0, 0}, 2000, 10))), "ack"));
  run(600);
  send(test::simple_msg("stop"));
  EXPECT_EQ(state(), State::kIdle);
  const Angles held = core->hold_target();
  run(300);
  EXPECT_NEAR(drv.position()[0], held[0], 0.5);
  const Angles here = drv.position();
  const auto next = test::smooth(here, {0, 0, 0}, 1500, 10);
  EXPECT_TRUE(find_msg(send(test::traj_msg("s2", 10, next)), "ack"));
  send(test::simple_msg("stop"));
  send(test::simple_msg("stop"));  // IDLE'da stop etkisiz
  EXPECT_EQ(state(), State::kIdle);
}

TEST_F(Edge, HoldCommandRequiresTorqueOnToContinue) {
  arm();
  send(test::simple_msg("hold"));
  EXPECT_EQ(state(), State::kHolding);
  send(test::simple_msg("hold"));
  EXPECT_EQ(state(), State::kHolding);
  EXPECT_TRUE(send(test::on_msg("torque", true)).empty());
  EXPECT_EQ(state(), State::kIdle);
  // TORQUE_OFF'ta hold etkisiz.
  send(test::on_msg("torque", false));
  send(test::simple_msg("hold"));
  EXPECT_EQ(state(), State::kTorqueOff);
}

TEST_F(Edge, TorqueOffCommandFromRunning) {
  arm();
  send(test::traj_msg("t", 10, test::smooth({0, 0, 0}, {60, 0, 0}, 2000, 10), true));
  run(300);
  send(test::on_msg("torque", false));
  EXPECT_EQ(state(), State::kTorqueOff);
  EXPECT_FALSE(drv.torque());
  EXPECT_FALSE(drv.magnet());
}

TEST_F(Edge, MagnetCommandsRespectState) {
  heartbeat();
  // Tork kapalıyken mıknatıs açılamaz.
  EXPECT_TRUE(find_msg(send(test::on_msg("magnet", true)), "fault", fault::kNotReady));
  EXPECT_FALSE(drv.magnet());
  arm();
  EXPECT_TRUE(send(test::on_msg("magnet", true)).empty());
  EXPECT_TRUE(drv.magnet());
  send(test::on_msg("magnet", false));
  EXPECT_FALSE(drv.magnet());
  send(test::simple_msg("hold"));
  send(test::on_msg("magnet", true));
  EXPECT_TRUE(drv.magnet());  // HOLDING'de izinli
  // Yörünge mıknatısı kapatabilir.
  send(test::on_msg("torque", true));
  send(test::traj_msg("off", 10, {{0, 0, 0}}, false));
  EXPECT_FALSE(drv.magnet());
  run(30);
  send(test::traj_msg("on", 10, test::smooth({0, 0, 0}, {10, 0, 0}, 500, 10), true));
  EXPECT_EQ(state(), State::kRunning);
  EXPECT_TRUE(send(test::on_msg("magnet", true)).empty());  // RUNNING'de izinli
  // Sağlık hatasında (FAULT) mıknatıs açılamaz; kapatmak her zaman serbest.
  drv.inject_load(0, 99.0);
  tick();
  ASSERT_EQ(state(), State::kFault);
  send(test::on_msg("magnet", false));
  EXPECT_TRUE(find_msg(send(test::on_msg("magnet", true)), "fault", fault::kNotReady));
  EXPECT_FALSE(drv.magnet());
}

TEST_F(Edge, ShutdownTurnsEverythingOff) {
  arm();
  send(test::on_msg("magnet", true));
  core->shutdown();
  EXPECT_FALSE(drv.torque());
  EXPECT_FALSE(drv.magnet());
  EXPECT_EQ(state(), State::kTorqueOff);
}

// ---------------- G9 ----------------

TEST_F(Edge, G9_OverTemperatureMidTrajectoryStopsHoldsAndFaults) {
  arm();
  ASSERT_TRUE(find_msg(
      send(test::traj_msg("hot", 10, test::smooth({0, 0, 0}, {80, 0, 0}, 2000, 10))), "ack"));
  run(500);
  drv.inject_temperature(1, 70.0);  // sınırda: devam
  run(20);
  ASSERT_EQ(state(), State::kRunning);
  drv.inject_temperature(1, 70.5);
  Out o;
  append(o, run(10));
  EXPECT_EQ(state(), State::kFault);
  const auto f = find_msg(o, "fault", fault::kOverTemp);
  ASSERT_TRUE(f);
  EXPECT_NE((*f)["detail"].get<std::string>().find("servo 2"), std::string::npos);
  const Angles held = core->hold_target();
  run(300);
  EXPECT_EQ(state(), State::kFault);
  EXPECT_TRUE(drv.torque());  // dur ve tut
  EXPECT_NEAR(drv.position()[0], held[0], 0.5);
  EXPECT_EQ(test::count_type(run(300), "fault"), 0);  // hata bir kez bildirilir
  // Sıcakken reset reddedilir; FAULT'ta torque on reddedilir.
  EXPECT_TRUE(find_msg(send(test::simple_msg("reset")), "fault", fault::kOverTemp));
  EXPECT_TRUE(find_msg(send(test::on_msg("torque", true)), "fault", fault::kNotReady));
  EXPECT_EQ(state(), State::kFault);
  // Soğuyunca reset -> IDLE, eski yörünge devam etmez.
  drv.clear_injections();
  EXPECT_TRUE(send(test::simple_msg("reset")).empty());
  EXPECT_EQ(state(), State::kIdle);
  run(300);
  EXPECT_NEAR(drv.position()[0], held[0], 0.5);
}

TEST_F(Edge, G9_VoltageAndLoadTrips) {
  struct Case {
    std::function<void(MockDriver&)> inject;
    const char* code;
  };
  const Case cases[] = {
      {[](MockDriver& d) { d.inject_voltage(8.9); }, fault::kVoltage},
      {[](MockDriver& d) { d.inject_voltage(13.1); }, fault::kVoltage},
      {[](MockDriver& d) { d.inject_load(2, 91.0); }, fault::kOverLoad},
      {[](MockDriver& d) { d.inject_load(0, -91.0); }, fault::kOverLoad},
      {[](MockDriver& d) { d.set_read_ok(false); }, fault::kDriver},
  };
  for (const Case& c : cases) {
    drv.clear_injections();
    if (state() == State::kFault) send(test::simple_msg("reset"));
    if (state() != State::kIdle) arm();
    ASSERT_EQ(state(), State::kIdle);
    c.inject(drv);
    const Out o = tick();
    EXPECT_EQ(state(), State::kFault) << c.code;
    EXPECT_TRUE(find_msg(o, "fault", c.code)) << c.code;
    run(50);
  }
}

TEST_F(Edge, G9_HoldingTripsToFault) {
  arm();
  send(test::simple_msg("hold"));
  drv.inject_temperature(0, 75.0);
  tick();
  EXPECT_EQ(state(), State::kFault);
}

TEST_F(Edge, G9_UnhealthyServoBlocksTorqueOn) {
  heartbeat();
  drv.inject_temperature(2, 71.0);
  EXPECT_TRUE(find_msg(send(test::on_msg("torque", true)), "fault", fault::kOverTemp));
  EXPECT_EQ(state(), State::kTorqueOff);
  EXPECT_FALSE(drv.torque());
  run(50);
  EXPECT_EQ(state(), State::kTorqueOff);  // tork kapalıyken sağlık durumu değiştirmez
}

TEST_F(Edge, ResetInFaultNeedsFreshHeartbeat) {
  arm();
  drv.inject_temperature(0, 75.0);
  tick();
  ASSERT_EQ(state(), State::kFault);
  drv.clear_injections();
  run(195, 0);
  EXPECT_TRUE(find_msg(send(test::simple_msg("reset")), "fault", fault::kHeartbeatRequired));
  EXPECT_EQ(state(), State::kFault);
}

// ---------------- ESTOP ----------------

TEST_F(Edge, Estop_LatchesUntilReleasedAndReset) {
  arm();
  send(test::traj_msg("e", 10, test::smooth({0, 0, 0}, {60, 0, 0}, 2000, 10), true));
  run(300);
  estop.set(true);
  const Out o = tick();
  EXPECT_EQ(state(), State::kEstop);
  EXPECT_FALSE(drv.torque());
  EXPECT_FALSE(drv.magnet());
  EXPECT_TRUE(find_msg(o, "fault", fault::kEstop));
  const long long goals = drv.goal_count();
  // Buton bırakıldı: mandal sürer.
  estop.set(false);
  run(300);
  EXPECT_EQ(state(), State::kEstop);
  EXPECT_EQ(drv.goal_count(), goals);
  EXPECT_EQ(test::count_type(run(100), "fault"), 0);  // bir kez bildirilir
  // ESTOP'ta torque on, magnet on, hold, stop, torque off etkisiz.
  EXPECT_TRUE(find_msg(send(test::on_msg("torque", true)), "fault", fault::kNotReady));
  EXPECT_TRUE(find_msg(send(test::on_msg("magnet", true)), "fault", fault::kNotReady));
  send(test::on_msg("torque", false));
  send(test::simple_msg("hold"));
  send(test::simple_msg("stop"));
  EXPECT_EQ(state(), State::kEstop);
  EXPECT_FALSE(drv.torque());
  // Buton basılıyken reset reddedilir.
  estop.set(true);
  EXPECT_TRUE(find_msg(send(test::simple_msg("reset")), "fault", fault::kEstop));
  EXPECT_EQ(state(), State::kEstop);
  // Bırak + reset -> TORQUE_OFF; devam için torque on.
  estop.set(false);
  EXPECT_TRUE(send(test::simple_msg("reset")).empty());
  EXPECT_EQ(state(), State::kTorqueOff);
  EXPECT_FALSE(drv.torque());
  EXPECT_TRUE(send(test::on_msg("torque", true)).empty());
  EXPECT_EQ(state(), State::kIdle);
}

TEST_F(Edge, Estop_FromTorqueOffAndBlocksTorqueOnBeforeTick) {
  heartbeat();
  estop.set(true);
  // Döngü henüz ESTOP'a geçmeden torque on gelirse de reddedilir.
  EXPECT_TRUE(find_msg(send(test::on_msg("torque", true)), "fault", fault::kEstop));
  tick();
  EXPECT_EQ(state(), State::kEstop);
  core->shutdown();
  EXPECT_EQ(state(), State::kEstop);  // kapanış ESTOP'u silmez
}

TEST_F(Edge, ResetOutsideFaultOrEstopIsNoop) {
  arm();
  EXPECT_TRUE(send(test::simple_msg("reset")).empty());
  EXPECT_EQ(state(), State::kIdle);
}

// ---------------- telemetri ----------------

TEST_F(Edge, TelemetryAt20Hz) {
  arm();
  const Out o = run(1000);
  EXPECT_EQ(test::count_type(o, "telemetry"), 20);
  const auto t = find_msg(o, "telemetry");
  ASSERT_TRUE(t);
  EXPECT_EQ((*t)["v"], 1);
  EXPECT_EQ((*t)["state"], "IDLE");
  EXPECT_EQ((*t)["angles"].size(), 3u);
  EXPECT_EQ((*t)["temps"].size(), 3u);
  EXPECT_EQ((*t)["loads"].size(), 3u);
  EXPECT_EQ((*t)["voltages"][0], 12.0);
  EXPECT_EQ((*t)["index"], -1);
}

TEST_F(Edge, TelemetryIndexAdvancesAt100Hz) {
  arm();
  ASSERT_TRUE(find_msg(send(test::traj_msg("i", 10, test::smooth({0, 0, 0}, {30, 0, 0}, 2000, 10))),
                       "ack"));
  Out o;
  for (int k = 1; k <= 50; ++k) {
    if (k % 5 == 0) heartbeat();  // kalp atışı yoksa bekçi T_stop'ta HOLD'a geçer (G6)
    o = tick();
    if (auto t = find_msg(o, "telemetry")) {
      EXPECT_EQ((*t)["index"], k);
    }
  }
}

}  // namespace
}  // namespace delta_edge
