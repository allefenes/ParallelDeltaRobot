// Sahte sürücü: dinamik, ısıl model, hata enjeksiyonu.
#include <gtest/gtest.h>

#include <cmath>

#include "delta_edge/ax12_driver.hpp"
#include "delta_edge/mock_driver.hpp"

namespace delta_edge {
namespace {

constexpr Micros kMs = kMicrosPerMs;

TEST(MockDriver, FollowsGoalWithSpeedLimit) {
  Micros now = 0;
  MockDriver d([&] { return now; });
  d.set_torque(true);
  d.set_goal({90, -45, 0});
  now = 100 * kMs;  // 354 deg/s ile 100 ms'de en fazla 35.4 deg
  const DriverState s = d.read_state();
  EXPECT_TRUE(s.ok);
  EXPECT_LE(s.angles[0], 35.4 + 1e-6);
  EXPECT_GT(s.angles[0], 30.0);
  EXPECT_LT(s.angles[1], -10.0);
  EXPECT_GT(s.loads_pct[0], 50.0);   // hızlı hareket -> yüksek yük
  EXPECT_LT(s.loads_pct[1], -50.0);  // ters yön -> negatif yük
  now = 2000 * kMs;
  const DriverState s2 = d.read_state();
  EXPECT_NEAR(s2.angles[0], 90.0, 1e-3);
  EXPECT_NEAR(s2.angles[1], -45.0, 1e-3);
  EXPECT_DOUBLE_EQ(s2.voltages_v[0], 12.0);
}

TEST(MockDriver, TorqueOffDoesNotMove) {
  Micros now = 0;
  MockDriver d([&] { return now; });
  d.set_goal({90, 0, 0});
  now = 1000 * kMs;
  const DriverState s = d.read_state();
  EXPECT_DOUBLE_EQ(s.angles[0], 0.0);
  EXPECT_DOUBLE_EQ(s.loads_pct[0], 0.0);
  EXPECT_FALSE(d.torque());
}

TEST(MockDriver, TemperatureRisesWithLoad) {
  Micros now = 0;
  MockDriver::Params p;
  p.temp_tau_s = 1.0;
  MockDriver d([&] { return now; }, p);
  d.set_torque(true);
  now = 5000 * kMs;
  const DriverState s = d.read_state();
  // Tutma yükü %10 -> kararlı 25 + 0.4*10 = 29 °C.
  EXPECT_NEAR(s.temps_c[0], 29.0, 0.1);
}

TEST(MockDriver, InjectionHooks) {
  Micros now = 0;
  MockDriver d([&] { return now; });
  d.inject_temperature(1, 80.0);
  d.inject_load(2, -95.0);
  d.inject_voltage(8.0);
  DriverState s = d.read_state();
  EXPECT_DOUBLE_EQ(s.temps_c[1], 80.0);
  EXPECT_DOUBLE_EQ(s.loads_pct[2], -95.0);
  EXPECT_DOUBLE_EQ(s.voltages_v[0], 8.0);
  d.set_read_ok(false);
  EXPECT_FALSE(d.read_state().ok);
  d.clear_injections();
  s = d.read_state();
  EXPECT_TRUE(s.ok);
  EXPECT_DOUBLE_EQ(s.temps_c[1], 25.0);
  EXPECT_DOUBLE_EQ(s.voltages_v[0], 12.0);
}

TEST(MockDriver, RecordsGoalExtremesAndMagnet) {
  Micros now = 0;
  MockDriver d([&] { return now; });
  d.set_goal({1, 2, 3});
  d.set_goal({-1, 5, 0});
  EXPECT_EQ(d.goal_count(), 2);
  EXPECT_DOUBLE_EQ(d.min_goal()[0], -1.0);
  EXPECT_DOUBLE_EQ(d.max_goal()[1], 5.0);
  EXPECT_DOUBLE_EQ(d.goal()[2], 0.0);
  d.set_magnet(true);
  EXPECT_TRUE(d.magnet());
}

TEST(MockDriver, ClockGoingBackwardsIsIgnored) {
  Micros now = 1000 * kMs;
  MockDriver d([&] { return now; });
  d.set_torque(true);
  d.set_goal({10, 0, 0});
  now = 0;
  EXPECT_DOUBLE_EQ(d.read_state().angles[0], 0.0);
}

TEST(Ax12Driver, StubReportsNotOk) {
  // TODO(F5) arka ucu: okuma başarısız -> EdgeCore torku açmaz.
  Ax12Driver d("/dev/ttyAMA0", 1000000);
  EXPECT_FALSE(d.read_state().ok);
  d.set_goal({0, 0, 0});
  d.set_torque(true);
  d.set_magnet(true);
  EXPECT_EQ(d.device(), "/dev/ttyAMA0");
  EXPECT_EQ(d.baud(), 1000000);
}

}  // namespace
}  // namespace delta_edge
