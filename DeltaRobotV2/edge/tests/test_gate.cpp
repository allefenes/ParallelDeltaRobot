// Son kapı: G1 (eklem limiti), G4 (sonlu olmayan), G5 (hız/ivme, ilk nokta sıçraması dahil),
// G9 (sağlık), kırpma (derinlemesine savunma).
#include <gtest/gtest.h>

#include <cmath>
#include <limits>

#include "delta_edge/faults.hpp"
#include "delta_edge/gate.hpp"
#include "delta_edge/protocol.hpp"
#include "test_util.hpp"

namespace delta_edge {
namespace {

constexpr double kInf = std::numeric_limits<double>::infinity();
const double kNaN = std::nan("");

// Hız/ivme sınırını yalıtmak için çok gevşek limitler.
EdgeLimits loose() {
  EdgeLimits l;
  l.max_velocity_dps = 1e9;
  l.max_accel_dps2 = 1e12;
  l.start_tolerance_deg = 0.0;
  return l;
}

DriverState healthy() {
  DriverState s;
  s.ok = true;
  s.angles = {0, 0, 0};
  s.temps_c = {30, 30, 30};
  s.loads_pct = {10, -10, 0};
  s.voltages_v = {12, 12, 12};
  return s;
}

// ---------------- G1: eklem limitleri ----------------

TEST(Gate, G1_JointLimitExactEdgesAccepted) {
  const Gate g(loose());
  EXPECT_TRUE(g.check_point({-70.0, 150.0, 0.0}).ok);
  EXPECT_TRUE(g.check_point({150.0, -70.0, 150.0}).ok);
  EXPECT_TRUE(g.validate_trajectory({-70, 150, 0}, {{-70.0, 150.0, 0.0}}, 10).ok);
}

TEST(Gate, G1_JointLimitJustOutsideRejected) {
  const Gate g(loose());
  const double above = std::nextafter(150.0, kInf);
  const double below = std::nextafter(-70.0, -kInf);
  for (int j = 0; j < 3; ++j) {
    Angles hi{0, 0, 0};
    hi[j] = above;
    Angles lo{0, 0, 0};
    lo[j] = below;
    const GateResult rh = g.check_point(hi);
    EXPECT_FALSE(rh.ok);
    EXPECT_EQ(rh.code, fault::kJointLimit);
    EXPECT_NE(rh.detail.find("eklem " + std::to_string(j + 1)), std::string::npos);
    const GateResult rl = g.check_point(lo);
    EXPECT_FALSE(rl.ok);
    EXPECT_EQ(rl.code, fault::kJointLimit);
  }
}

TEST(Gate, G1_TrajectoryWithOneBadPointRejectedWithIndex) {
  const Gate g(loose());
  std::vector<Angles> pts = {{0, 0, 0}, {1, 1, 1}, {2, 2, 151}, {3, 3, 3}};
  const GateResult r = g.validate_trajectory({0, 0, 0}, pts, 10);
  EXPECT_FALSE(r.ok);
  EXPECT_EQ(r.code, fault::kJointLimit);
  EXPECT_NE(r.detail.find("nokta 2"), std::string::npos) << r.detail;
  EXPECT_NE(r.detail.find("eklem 3"), std::string::npos) << r.detail;
}

TEST(Gate, G1_UsesConfiguredLimits) {
  EdgeLimits l = loose();
  l.joint_min_deg = -10.0;
  l.joint_max_deg = 10.0;
  const Gate g(l);
  EXPECT_TRUE(g.check_point({10, -10, 0}).ok);
  EXPECT_FALSE(g.check_point({10.5, 0, 0}).ok);
  EXPECT_FALSE(g.check_point({0, -10.5, 0}).ok);
}

// ---------------- G4: sonlu olmayan değerler ----------------

TEST(Gate, G4_NonFinitePointRejected) {
  const Gate g(loose());
  for (int j = 0; j < 3; ++j) {
    for (double bad : {kNaN, kInf, -kInf}) {
      Angles p{0, 0, 0};
      p[j] = bad;
      const GateResult r = g.check_point(p);
      EXPECT_FALSE(r.ok);
      EXPECT_EQ(r.code, fault::kNonFinite);
      EXPECT_FALSE(g.validate_trajectory({0, 0, 0}, {{0, 0, 0}, p}, 10).ok);
    }
  }
}

TEST(Gate, G4_NonFiniteCurrentPositionRejected) {
  const Gate g(loose());
  for (int j = 0; j < 3; ++j) {
    Angles cur{0, 0, 0};
    cur[j] = kNaN;
    const GateResult r = g.validate_trajectory(cur, {{0, 0, 0}}, 10);
    EXPECT_FALSE(r.ok);
    EXPECT_EQ(r.code, fault::kNonFinite);
  }
}

// ---------------- period / boyut ----------------

TEST(Gate, PeriodAndSizeChecked) {
  const Gate g(loose());
  const std::vector<Angles> one = {{0, 0, 0}};
  EXPECT_TRUE(g.validate_trajectory({0, 0, 0}, one, kMinPeriodMs).ok);
  EXPECT_TRUE(g.validate_trajectory({0, 0, 0}, one, kMaxPeriodMs).ok);
  EXPECT_EQ(g.validate_trajectory({0, 0, 0}, one, kMinPeriodMs - 1).code, fault::kPeriod);
  EXPECT_EQ(g.validate_trajectory({0, 0, 0}, one, kMaxPeriodMs + 1).code, fault::kPeriod);
  EXPECT_EQ(g.validate_trajectory({0, 0, 0}, {}, 10).code, fault::kEmpty);
  std::vector<Angles> cap(kMaxPoints, Angles{0, 0, 0});
  EXPECT_TRUE(g.validate_trajectory({0, 0, 0}, cap, 10).ok);
  cap.push_back({0, 0, 0});
  EXPECT_EQ(g.validate_trajectory({0, 0, 0}, cap, 10).code, fault::kTooManyPoints);
}

// ---------------- G5: hız ----------------

TEST(Gate, G5_VelocityAtLimitAcceptedAboveRejected) {
  EdgeLimits l = loose();
  l.max_velocity_dps = 300.0;  // T = 10 ms -> adım başına en fazla 3 deg
  const Gate g(l);
  for (int j = 0; j < 3; ++j) {
    Angles a{0, 0, 0}, b{0, 0, 0}, c{0, 0, 0};
    b[j] = 3.0;
    c[j] = 6.0;
    EXPECT_TRUE(g.validate_trajectory({0, 0, 0}, {a, b, c}, 10).ok);
    c[j] = 6.0 + 1e-9;
    const GateResult r = g.validate_trajectory({0, 0, 0}, {a, b, c}, 10);
    EXPECT_FALSE(r.ok);
    EXPECT_EQ(r.code, fault::kVelocity);
    EXPECT_NE(r.detail.find("nokta 2"), std::string::npos) << r.detail;
    EXPECT_NE(r.detail.find("eklem " + std::to_string(j + 1)), std::string::npos) << r.detail;
    // Negatif yön de denetlenir.
    b[j] = -3.0;
    c[j] = -6.0 - 1e-9;
    EXPECT_EQ(g.validate_trajectory({0, 0, 0}, {a, b, c}, 10).code, fault::kVelocity);
  }
}

TEST(Gate, G5_VelocityScalesWithPeriod) {
  EdgeLimits l = loose();
  l.max_velocity_dps = 300.0;
  const Gate g(l);
  // 50 ms'de 15 deg = 300 deg/s: kabul; 10 ms'de aynı adım 1500 deg/s: red.
  EXPECT_TRUE(g.validate_trajectory({0, 0, 0}, {{0, 0, 0}, {15, 0, 0}}, 50).ok);
  EXPECT_FALSE(g.validate_trajectory({0, 0, 0}, {{0, 0, 0}, {15, 0, 0}}, 10).ok);
  EXPECT_TRUE(g.validate_trajectory({0, 0, 0}, {{0, 0, 0}, {1.5, 0, 0}}, 5).ok);
  EXPECT_FALSE(g.validate_trajectory({0, 0, 0}, {{0, 0, 0}, {1.6, 0, 0}}, 5).ok);
}

TEST(Gate, G5_FirstPointJumpFromCurrentPositionRejected) {
  EdgeLimits l = loose();
  l.max_velocity_dps = 300.0;
  const Gate g(l);
  // Mevcut konum 0, ilk nokta 4 deg: 10 ms'de 400 deg/s sıçrama.
  const GateResult r = g.validate_trajectory({0, 0, 0}, {{4, 0, 0}, {4, 0, 0}}, 10);
  EXPECT_FALSE(r.ok);
  EXPECT_EQ(r.code, fault::kVelocity);
  EXPECT_NE(r.detail.find("ilk nokta"), std::string::npos) << r.detail;
  // Aynı nokta, mevcut konum yakınsa kabul.
  EXPECT_TRUE(g.validate_trajectory({3, 0, 0}, {{4, 0, 0}, {4, 0, 0}}, 10).ok);
  // Tek noktalı yörünge (konuma git) de aynı sıçrama kuralına tabi.
  EXPECT_FALSE(g.validate_trajectory({0, 0, 0}, {{0, 0, 100}}, 50).ok);
}

TEST(Gate, G5_StartToleranceAbsorbsMeasurementNoise) {
  EdgeLimits l;  // varsayılanlar: 300 deg/s, 3000 deg/s², tolerans 1 deg
  const Gate g(l);
  // |fark| <= 1 deg: sıçrama sayılmaz.
  EXPECT_TRUE(g.validate_trajectory({0, 0, 0}, {{1.0, -1.0, 0.5}}, 10).ok);
  // 1.25 deg: 0.25 deg kalır -> v=25 deg/s, a=2500 deg/s² kabul.
  EXPECT_TRUE(g.validate_trajectory({0, 0, 0}, {{1.25, 0, 0}}, 10).ok);
  // 1.31 deg: a = 3100 deg/s² -> ivme reddi.
  const GateResult r = g.validate_trajectory({0, 0, 0}, {{1.31, 0, 0}}, 10);
  EXPECT_FALSE(r.ok);
  EXPECT_EQ(r.code, fault::kAccel);
  // Negatif yönde de aynı.
  EXPECT_FALSE(g.validate_trajectory({0, 0, 0}, {{-1.31, 0, 0}}, 10).ok);
  EXPECT_TRUE(g.validate_trajectory({0, 0, 0}, {{-1.25, 0, 0}}, 10).ok);
}

// ---------------- G5: ivme ----------------

TEST(Gate, G5_AccelerationAtLimitAcceptedAboveRejected) {
  EdgeLimits l = loose();
  // Sınır ikili kayan noktada tam gösterilebilir seçildi: T = 10 ms -> adımda en fazla 25 deg/s.
  l.max_accel_dps2 = 2500.0;
  const Gate g(l);
  // v: 0 -> 25 -> 50 -> 25 -> 0 deg/s (adımlar 0.25, 0.5, 0.25 deg): her adım tam sınırda.
  const std::vector<Angles> ok = {{0, 0, 0}, {0.25, 0, 0}, {0.75, 0, 0}, {1.0, 0, 0}, {1.0, 0, 0}};
  EXPECT_TRUE(g.validate_trajectory({0, 0, 0}, ok, 10).ok);
  // Biraz fazlası: 0.25 + 1e-9 deg kalkış adımı.
  EXPECT_EQ(g.validate_trajectory({0, 0, 0}, {{0, 0, 0}, {0.25 + 1e-9, 0, 0}}, 10).code,
            fault::kAccel);
  // Ortada ani hız artışı: 0.25 -> 1.0 deg adım (25 -> 100 deg/s, 7500 deg/s²).
  const std::vector<Angles> bad = {{0, 0, 0}, {0.25, 0, 0}, {1.25, 0, 0}, {1.5, 0, 0}};
  const GateResult r = g.validate_trajectory({0, 0, 0}, bad, 10);
  EXPECT_FALSE(r.ok);
  EXPECT_EQ(r.code, fault::kAccel);
  EXPECT_NE(r.detail.find("nokta 2"), std::string::npos) << r.detail;
}

TEST(Gate, G5_AbruptStopAtEndRejected) {
  EdgeLimits l = loose();
  l.max_accel_dps2 = 2500.0;
  // Son adımda hız 25 deg/s, ardından duruş: -2500 deg/s² (sınırda) kabul.
  EXPECT_TRUE(Gate(l).validate_trajectory({0, 0, 0}, {{0, 0, 0}, {0.25, 0, 0}}, 10).ok);
  // Son duruşu yalıtmak için: adım başına 2500 deg/s² hızlanıp 125 deg/s'de biten yörünge;
  // sınır 5000 iken yalnız son duruş (-12500 deg/s²) aşar.
  l.max_accel_dps2 = 5000.0;
  const Gate g(l);
  const std::vector<Angles> pts = {{0, 0, 0},   {0.25, 0, 0}, {0.75, 0, 0},
                                   {1.5, 0, 0}, {2.5, 0, 0},  {3.75, 0, 0}};
  const GateResult r = g.validate_trajectory({0, 0, 0}, pts, 10);
  EXPECT_FALSE(r.ok);
  EXPECT_EQ(r.code, fault::kAccel);
  EXPECT_NE(r.detail.find("son noktada"), std::string::npos) << r.detail;
}

TEST(Gate, G5_PerJointIndependent) {
  EdgeLimits l = loose();
  l.max_accel_dps2 = 3000.0;
  const Gate g(l);
  for (int j = 0; j < 3; ++j) {
    std::vector<Angles> pts(3, Angles{0, 0, 0});
    pts[1][j] = 0.31;  // kalkış ivmesi 3100 deg/s²
    pts[2][j] = 0.31;
    const GateResult r = g.validate_trajectory({0, 0, 0}, pts, 10);
    EXPECT_FALSE(r.ok);
    EXPECT_EQ(r.code, fault::kAccel);
    EXPECT_NE(r.detail.find("eklem " + std::to_string(j + 1)), std::string::npos) << r.detail;
  }
}

TEST(Gate, G5_SmoothServerTrajectoryAccepted) {
  const Gate g{EdgeLimits{}};
  // 60 deg, 1 s kosinüs: tepe 94 deg/s, 296 deg/s².
  const auto pts = test::smooth({0, 0, 0}, {60, -30, 45}, 1000, 10);
  EXPECT_TRUE(g.validate_trajectory({0, 0, 0}, pts, 10).ok);
  // Aynı hareket 0.2 s'de: tepe 471 deg/s -> red.
  const auto fast = test::smooth({0, 0, 0}, {60, 0, 0}, 200, 10);
  EXPECT_FALSE(g.validate_trajectory({0, 0, 0}, fast, 10).ok);
}

// ---------------- kırpma (derinlemesine savunma) ----------------

TEST(Gate, ClampCommandLimitsAndStep) {
  const Gate g{EdgeLimits{}};  // 300 deg/s
  // dt = 10 ms -> en fazla 3 deg adım.
  auto c = g.clamp_command({0, 0, 0}, {10, -10, 1}, 0.01);
  ASSERT_TRUE(c);
  EXPECT_DOUBLE_EQ((*c)[0], 3.0);
  EXPECT_DOUBLE_EQ((*c)[1], -3.0);
  EXPECT_DOUBLE_EQ((*c)[2], 1.0);
  // Eklem limitine kırpma (G1, derinlemesine).
  c = g.clamp_command({149, -69, 0}, {200, -200, 0}, 0.01);
  ASSERT_TRUE(c);
  EXPECT_DOUBLE_EQ((*c)[0], 150.0);
  EXPECT_DOUBLE_EQ((*c)[1], -70.0);
  // Önceki komut sınır dışıysa önce sınıra çekilir.
  c = g.clamp_command({155, 0, 0}, {155, 0, 0}, 0.01);
  ASSERT_TRUE(c);
  EXPECT_DOUBLE_EQ((*c)[0], 150.0);
}

TEST(Gate, ClampCommandDtHandling) {
  const Gate g{EdgeLimits{}};
  // dt <= 0 ya da NaN: hareket yok.
  for (double dt : {0.0, -1.0, kNaN, kInf}) {
    const auto c = g.clamp_command({5, 5, 5}, {50, 50, 50}, dt);
    ASSERT_TRUE(c);
    EXPECT_DOUBLE_EQ((*c)[0], 5.0) << dt;
  }
  // dt büyükse kMaxCommandDtS ile sınırlanır: 300 * 0.05 = 15 deg.
  const auto c = g.clamp_command({0, 0, 0}, {100, 0, 0}, 10.0);
  ASSERT_TRUE(c);
  EXPECT_DOUBLE_EQ((*c)[0], 15.0);
  const auto c2 = g.clamp_command({0, 0, 0}, {100, 0, 0}, 0.05);
  ASSERT_TRUE(c2);
  EXPECT_DOUBLE_EQ((*c2)[0], 15.0);
}

TEST(Gate, G4_ClampCommandNonFinite) {
  const Gate g{EdgeLimits{}};
  // Sonlu olmayan hedef: eklem önceki komutta kalır.
  const auto c = g.clamp_command({1, 2, 3}, {kNaN, kInf, 3.5}, 0.01);
  ASSERT_TRUE(c);
  EXPECT_DOUBLE_EQ((*c)[0], 1.0);
  EXPECT_DOUBLE_EQ((*c)[1], 2.0);
  EXPECT_DOUBLE_EQ((*c)[2], 3.5);
  // Sonlu olmayan önceki komut: güvenli komut yok.
  for (int j = 0; j < 3; ++j) {
    Angles prev{0, 0, 0};
    prev[j] = kNaN;
    EXPECT_FALSE(g.clamp_command(prev, {0, 0, 0}, 0.01).has_value());
  }
}

TEST(Gate, ClampToLimits) {
  const Gate g{EdgeLimits{}};
  const Angles a = g.clamp_to_limits({-100, 200, 10});
  EXPECT_DOUBLE_EQ(a[0], -70.0);
  EXPECT_DOUBLE_EQ(a[1], 150.0);
  EXPECT_DOUBLE_EQ(a[2], 10.0);
  EXPECT_TRUE(std::isnan(g.clamp_to_limits({kNaN, 0, 0})[0]));
}

// ---------------- G9: sağlık ----------------

TEST(Gate, G9_HealthyStateAccepted) {
  const Gate g{EdgeLimits{}};
  EXPECT_TRUE(g.check_health(healthy()).ok);
  DriverState s = healthy();
  s.temps_c = {70, 70, 70};
  s.loads_pct = {90, -90, 90};
  s.voltages_v = {9, 13, 9};
  EXPECT_TRUE(g.check_health(s).ok);  // sınır değerleri dahil
}

TEST(Gate, G9_TemperatureTrip) {
  const Gate g{EdgeLimits{}};
  for (int j = 0; j < 3; ++j) {
    DriverState s = healthy();
    s.temps_c[j] = std::nextafter(70.0, kInf);
    const GateResult r = g.check_health(s);
    EXPECT_FALSE(r.ok);
    EXPECT_EQ(r.code, fault::kOverTemp);
    EXPECT_NE(r.detail.find("servo " + std::to_string(j + 1)), std::string::npos);
  }
}

TEST(Gate, G9_LoadTripBothDirections) {
  const Gate g{EdgeLimits{}};
  for (int j = 0; j < 3; ++j) {
    for (double load : {90.5, -90.5}) {
      DriverState s = healthy();
      s.loads_pct[j] = load;
      const GateResult r = g.check_health(s);
      EXPECT_FALSE(r.ok);
      EXPECT_EQ(r.code, fault::kOverLoad);
    }
  }
}

TEST(Gate, G9_VoltageTripLowAndHigh) {
  const Gate g{EdgeLimits{}};
  for (int j = 0; j < 3; ++j) {
    for (double v : {std::nextafter(9.0, 0.0), std::nextafter(13.0, kInf)}) {
      DriverState s = healthy();
      s.voltages_v[j] = v;
      const GateResult r = g.check_health(s);
      EXPECT_FALSE(r.ok);
      EXPECT_EQ(r.code, fault::kVoltage);
    }
  }
}

TEST(Gate, G9_DriverFailureAndNonFiniteReadings) {
  const Gate g{EdgeLimits{}};
  DriverState s = healthy();
  s.ok = false;
  EXPECT_EQ(g.check_health(s).code, fault::kDriver);
  for (int j = 0; j < 3; ++j) {
    for (int field = 0; field < 4; ++field) {
      DriverState t = healthy();
      Angles* arr[] = {&t.angles, &t.temps_c, &t.loads_pct, &t.voltages_v};
      (*arr[field])[j] = kNaN;
      EXPECT_EQ(g.check_health(t).code, fault::kNonFinite) << j << " " << field;
    }
  }
}

}  // namespace
}  // namespace delta_edge
