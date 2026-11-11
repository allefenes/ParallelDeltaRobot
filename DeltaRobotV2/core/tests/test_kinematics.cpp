// delta_core kinematik birim testleri. Gereksinim kimlikleri docs/guvenlik-gereksinimleri.md'de.
#include <gtest/gtest.h>

#include <cmath>
#include <limits>

#include "delta_core/kinematics.hpp"

using delta_core::Angles;
using delta_core::DeltaKinematics;
using delta_core::DeltaParams;
using delta_core::Mat3;
using delta_core::Vec3;

namespace {

DeltaKinematics robot() { return DeltaKinematics(DeltaParams{}); }

constexpr double kNaN = std::numeric_limits<double>::quiet_NaN();
constexpr double kInf = std::numeric_limits<double>::infinity();

}  // namespace

TEST(Kinematics, KnownPointMatchesV1) {
  // V1: (0, 0, 240) noktası her kol için 52.93°. V2 çerçevesinde z = -240.
  const auto th = robot().inverse({0, 0, -240});
  ASSERT_TRUE(th.has_value());
  for (double t : *th) EXPECT_NEAR(t, 52.93, 0.01);
}

TEST(Kinematics, HomeForwardIsCentered) {
  const auto P = robot().forward({0, 0, 0});
  ASSERT_TRUE(P.has_value());
  EXPECT_NEAR(P->x, 0.0, 1e-9);
  EXPECT_NEAR(P->y, 0.0, 1e-9);
  EXPECT_NEAR(P->z, -177.665, 1e-3);  // V1 FK(0,0,0)
}

TEST(Kinematics, RoundTripGrid) {
  const auto k = robot();
  int n = 0;
  for (double x = -60; x <= 60; x += 20)
    for (double y = -60; y <= 60; y += 20)
      for (double z = -230; z <= -150; z += 20) {
        const Vec3 P{x, y, z};
        const auto th = k.inverse(P);
        if (!th) continue;
        const auto Q = k.forward(*th);
        ASSERT_TRUE(Q.has_value());
        EXPECT_NEAR(norm(*Q - P), 0.0, 1e-8);
        ++n;
      }
  EXPECT_GT(n, 200);
}

TEST(Kinematics, ElbowDistanceIsBicep) {
  const auto k = robot();
  for (int i = 0; i < 3; ++i) EXPECT_NEAR(norm(k.elbow(i, 33.0) - k.shoulder(i)), 64.0, 1e-12);
}

TEST(Kinematics, UnreachableReturnsEmpty) {
  const auto k = robot();
  EXPECT_FALSE(k.inverse({0, 0, -400}).has_value());
  EXPECT_FALSE(k.inverse({500, 0, -200}).has_value());
}

TEST(Kinematics, NonFiniteInputRejected) {  // G4
  const auto k = robot();
  EXPECT_FALSE(k.inverse({kNaN, 0, -200}).has_value());
  EXPECT_FALSE(k.inverse({0, kInf, -200}).has_value());
  EXPECT_FALSE(k.forward({kNaN, 0, 0}).has_value());
  EXPECT_FALSE(k.check_limits({0, kNaN, 0}, {0, 0, -200}).ok);
  EXPECT_FALSE(k.check_limits({0, 0, 0}, {kNaN, 0, -200}).ok);
}

TEST(Kinematics, MotorLimitRejected) {  // G1
  const auto k = robot();
  // V1 bulgusu: (60, 0, 140) noktasında θ1 = -71.7° (limit -70°)
  const auto r = k.check_point({60, 0, -140});
  EXPECT_FALSE(r.ok);
  EXPECT_EQ(r.arm, 0);
  EXPECT_EQ(r.reason, "motor açı limiti");
  EXPECT_FALSE(k.check_limits({151, 0, 0}, {0, 0, -200}).ok);
}

TEST(Kinematics, RodTiltLimitRejected) {  // G2
  const auto k = robot();
  // V1 bulgusu: (-80, 0, 200) noktasında yanal açı 20°
  const auto r = k.check_point({-80, 0, -200});
  EXPECT_FALSE(r.ok);
  EXPECT_EQ(r.reason, "rot başı açı limiti");
}

TEST(Kinematics, ValidPointAccepted) {
  const auto r = robot().check_point({0, 0, -200});
  EXPECT_TRUE(r.ok) << r.reason;
}

TEST(Kinematics, UnreachablePointRejected) {
  const auto r = robot().check_point({0, 0, -500});
  EXPECT_FALSE(r.ok);
  EXPECT_EQ(r.reason, "erişilemez");
}

TEST(Kinematics, JacobianMatchesFiniteDifference) {
  const auto k = robot();
  const Angles th{20, 35, 10};
  const auto J = k.jacobian(th);
  ASSERT_TRUE(J.has_value());
  const double h = 1e-6;  // derece
  for (int c = 0; c < 3; ++c) {
    Angles a = th, b = th;
    a[c] += h;
    b[c] -= h;
    const Vec3 d = (*k.forward(a) - *k.forward(b)) * (1.0 / (2 * h * M_PI / 180.0));
    EXPECT_NEAR((*J)[0][c], d.x, 1e-4);
    EXPECT_NEAR((*J)[1][c], d.y, 1e-4);
    EXPECT_NEAR((*J)[2][c], d.z, 1e-4);
  }
}

TEST(Kinematics, ConditionNumberFiniteAtHome) {
  const double c = robot().condition_number({20, 20, 20});
  EXPECT_GE(c, 1.0);
  EXPECT_LT(c, 10.0);
}

TEST(Kinematics, SymmetryOf120Degrees) {
  const auto k = robot();
  const Vec3 P{30, 10, -200};
  const double a = 2.0 * M_PI / 3.0;
  const Vec3 Q{P.x * std::cos(a) - P.y * std::sin(a), P.x * std::sin(a) + P.y * std::cos(a), P.z};
  const auto tp = k.inverse(P);
  const auto tq = k.inverse(Q);
  ASSERT_TRUE(tp && tq);
  // 120° döndürmek kolları bir kaydırır: θ_Q[i+1] = θ_P[i]
  for (int i = 0; i < 3; ++i) EXPECT_NEAR((*tq)[(i + 1) % 3], (*tp)[i], 1e-9);
}

TEST(Kinematics, ForwardDegenerateGeometry) {
  DeltaParams p;
  p.forearm_length = 10.0;  // küreler kesişemez
  EXPECT_FALSE(DeltaKinematics(p).forward({0, 0, 0}).has_value());
  EXPECT_EQ(DeltaKinematics(p).condition_number({0, 0, 0}), kInf);
  DeltaParams q;
  q.arm_angles = {0, 0, 0};  // tüm kollar üst üste: tekil
  EXPECT_FALSE(DeltaKinematics(q).forward({0, 0, 0}).has_value());
  DeltaParams r;
  r.arm_angles = {0, 180, 0};  // iki kol aynı: küre merkezleri doğrusal
  EXPECT_FALSE(DeltaKinematics(r).forward({0, 0, 0}).has_value());
}

TEST(Kinematics, SymmetricEigenvalues) {
  const Mat3 diag{{{3, 0, 0}, {0, 1, 0}, {0, 0, 2}}};
  const auto e = delta_core::symmetric_eigenvalues(diag);
  EXPECT_DOUBLE_EQ(e[0], 1);
  EXPECT_DOUBLE_EQ(e[2], 3);
  const Mat3 m{{{2, 1, 0}, {1, 2, 0}, {0, 0, 5}}};  // özdeğerler 1, 3, 5
  const auto f = delta_core::symmetric_eigenvalues(m);
  EXPECT_NEAR(f[0], 1, 1e-12);
  EXPECT_NEAR(f[1], 3, 1e-12);
  EXPECT_NEAR(f[2], 5, 1e-12);
}

TEST(Kinematics, RodTiltZeroOnSymmetryAxis) {
  const auto k = robot();
  const Vec3 P{0, 0, -200};
  const auto th = k.inverse(P);
  ASSERT_TRUE(th.has_value());
  for (int i = 0; i < 3; ++i) EXPECT_NEAR(k.rod_tilt_deg(i, (*th)[i], P), 0.0, 1e-9);
}
