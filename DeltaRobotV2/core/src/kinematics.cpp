// Delta robot kinematiği. Açıklamalar ve çerçeve tanımı: include/delta_core/kinematics.hpp
#include "delta_core/kinematics.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace delta_core {
namespace {

constexpr double kPi = 3.14159265358979323846;
constexpr double kDeg = kPi / 180.0;
constexpr Vec3 kUp{0.0, 0.0, 1.0};

bool finite(const Vec3& v) {
  return std::isfinite(v.x) && std::isfinite(v.y) && std::isfinite(v.z);
}

// 3x3 matrisin tersi (adjoint / determinant). |det| çok küçükse boş.
std::optional<Mat3> inverse3(const Mat3& m) {
  const double d = det(m);
  if (!std::isfinite(d) || std::abs(d) < 1e-12) return std::nullopt;
  Mat3 r{};
  r[0][0] = (m[1][1] * m[2][2] - m[1][2] * m[2][1]) / d;
  r[0][1] = (m[0][2] * m[2][1] - m[0][1] * m[2][2]) / d;
  r[0][2] = (m[0][1] * m[1][2] - m[0][2] * m[1][1]) / d;
  r[1][0] = (m[1][2] * m[2][0] - m[1][0] * m[2][2]) / d;
  r[1][1] = (m[0][0] * m[2][2] - m[0][2] * m[2][0]) / d;
  r[1][2] = (m[0][2] * m[1][0] - m[0][0] * m[1][2]) / d;
  r[2][0] = (m[1][0] * m[2][1] - m[1][1] * m[2][0]) / d;
  r[2][1] = (m[0][1] * m[2][0] - m[0][0] * m[2][1]) / d;
  r[2][2] = (m[0][0] * m[1][1] - m[0][1] * m[1][0]) / d;
  return r;
}

}  // namespace

DeltaKinematics::DeltaKinematics(DeltaParams params) : p_(params) {
  for (int i = 0; i < 3; ++i) {
    const double a = p_.arm_angles[i] * kDeg;
    u_[i] = {std::cos(a), std::sin(a), 0.0};
    t_[i] = {-std::sin(a), std::cos(a), 0.0};
  }
}

Vec3 DeltaKinematics::shoulder(int i) const { return u_[i] * p_.base_radius; }

Vec3 DeltaKinematics::elbow(int i, double theta_deg) const {
  const double th = theta_deg * kDeg;
  // B = (R + L1·cosθ)·u - L1·sinθ·z  (pozitif θ aşağı)
  return u_[i] * (p_.base_radius + p_.bicep_length * std::cos(th)) -
         kUp * (p_.bicep_length * std::sin(th));
}

Vec3 DeltaKinematics::wrist(int i, const Vec3& P) const { return P + u_[i] * p_.platform_radius; }

std::optional<Angles> DeltaKinematics::inverse(const Vec3& P) const {
  if (!finite(P)) return std::nullopt;
  Angles out{};
  const double L1 = p_.bicep_length;
  const double L2 = p_.forearm_length;
  for (int i = 0; i < 3; ++i) {
    // Kol düzleminde c = C_i - A_i; |B - C| = L2 koşulu  cx·cosθ - cz·sinθ = K  verir.
    const Vec3 c = wrist(i, P) - shoulder(i);
    const double cx = dot(c, u_[i]);
    const double cz = c.z;
    const double k = (L1 * L1 + dot(c, c) - L2 * L2) / (2.0 * L1);
    const double rho = std::hypot(cx, cz);
    if (rho < 1e-12 || std::abs(k) > rho) return std::nullopt;
    const double phi = std::atan2(cz, cx);
    const double a = std::acos(k / rho);
    // cx·cosθ - cz·sinθ = ρ·cos(θ + φ): kökler θ = -φ ± a. Dirsek dışarıda: cos θ büyük olan.
    const double r1 = std::remainder(-phi + a, 2.0 * kPi);
    const double r2 = std::remainder(-phi - a, 2.0 * kPi);
    out[i] = (std::cos(r1) >= std::cos(r2) ? r1 : r2) / kDeg;
  }
  return out;
}

std::optional<Vec3> DeltaKinematics::forward(const Angles& theta_deg) const {
  for (double t : theta_deg)
    if (!std::isfinite(t)) return std::nullopt;
  // P, merkezleri S_i = B_i - r·u_i olan üç L2 yarıçaplı kürenin kesişimidir.
  std::array<Vec3, 3> s{};
  for (int i = 0; i < 3; ++i) s[i] = elbow(i, theta_deg[i]) - u_[i] * p_.platform_radius;
  const Vec3 d21 = s[1] - s[0];
  const double d = norm(d21);
  if (d < 1e-9) return std::nullopt;
  const Vec3 ex = d21 * (1.0 / d);
  const Vec3 d31 = s[2] - s[0];
  const double i = dot(ex, d31);
  Vec3 ey = d31 - ex * i;
  const double ey_n = norm(ey);
  if (ey_n < 1e-9) return std::nullopt;
  ey = ey * (1.0 / ey_n);
  const Vec3 ez = cross(ex, ey);
  const double j = dot(ey, d31);
  // Eşit yarıçaplı üç küre: x = d/2, y = (i² + j²)/(2j) - (i/j)·x
  const double x = d / 2.0;
  const double y = (i * i + j * j) / (2.0 * j) - (i / j) * x;
  const double z2 = p_.forearm_length * p_.forearm_length - x * x - y * y;
  if (z2 < 0.0) return std::nullopt;
  const double z = std::sqrt(z2);
  const Vec3 base = s[0] + ex * x + ey * y;
  const Vec3 a = base + ez * z;
  const Vec3 b = base - ez * z;
  return a.z < b.z ? a : b;  // platform motorların altında
}

std::optional<Mat3> DeltaKinematics::jacobian(const Angles& theta_deg) const {
  const auto P = forward(theta_deg);
  if (!P) return std::nullopt;
  // Kısıt |C_i - B_i|² = L2² türevlenir: c_i·dP = c_i·(dB_i/dθ_i)·dθ_i  ->  A·dP = diag(b)·dθ
  Mat3 A{};
  std::array<double, 3> b{};
  for (int i = 0; i < 3; ++i) {
    const double th = theta_deg[i] * kDeg;
    const Vec3 c = wrist(i, *P) - elbow(i, theta_deg[i]);
    const Vec3 dB = (u_[i] * -std::sin(th) - kUp * std::cos(th)) * p_.bicep_length;
    A[i] = {c.x, c.y, c.z};
    b[i] = dot(c, dB);
  }
  const auto Ainv = inverse3(A);
  if (!Ainv) return std::nullopt;
  Mat3 J{};
  for (int r = 0; r < 3; ++r)
    for (int col = 0; col < 3; ++col) J[r][col] = (*Ainv)[r][col] * b[col];
  return J;
}

double DeltaKinematics::condition_number(const Angles& theta_deg) const {
  const auto J = jacobian(theta_deg);
  if (!J) return std::numeric_limits<double>::infinity();
  Mat3 jtj{};
  for (int r = 0; r < 3; ++r)
    for (int c = 0; c < 3; ++c)
      for (int k = 0; k < 3; ++k) jtj[r][c] += (*J)[k][r] * (*J)[k][c];
  const auto ev = symmetric_eigenvalues(jtj);
  if (ev[0] <= 0.0) return std::numeric_limits<double>::infinity();
  return std::sqrt(ev[2] / ev[0]);
}

double DeltaKinematics::rod_tilt_deg(int i, double theta_deg, const Vec3& P) const {
  const Vec3 d = wrist(i, P) - elbow(i, theta_deg);
  const double n = norm(d);
  const double s = std::clamp(std::abs(dot(d, t_[i])) / n, 0.0, 1.0);
  return std::asin(s) / kDeg;
}

LimitCheck DeltaKinematics::check_limits(const Angles& theta_deg, const Vec3& P) const {
  if (!finite(P)) return {false, -1, "konum sayı değil"};
  for (int i = 0; i < 3; ++i) {
    const double t = theta_deg[i];
    if (!std::isfinite(t)) return {false, i, "açı sayı değil"};
    if (t < p_.motor_limit_min || t > p_.motor_limit_max) return {false, i, "motor açı limiti"};
    if (rod_tilt_deg(i, t, P) > p_.spherical_joint_limit) return {false, i, "rot başı açı limiti"};
  }
  return {};
}

LimitCheck DeltaKinematics::check_point(const Vec3& P) const {
  const auto th = inverse(P);
  if (!th) return {false, -1, "erişilemez"};
  return check_limits(*th, P);
}

std::array<double, 3> symmetric_eigenvalues(const Mat3& m) {
  // Kapalı biçim (trigonometrik) çözüm; m simetrik varsayılır.
  const double p1 = m[0][1] * m[0][1] + m[0][2] * m[0][2] + m[1][2] * m[1][2];
  std::array<double, 3> ev{};
  if (p1 < 1e-300) {
    ev = {m[0][0], m[1][1], m[2][2]};
  } else {
    const double q = (m[0][0] + m[1][1] + m[2][2]) / 3.0;
    const double p2 = (m[0][0] - q) * (m[0][0] - q) + (m[1][1] - q) * (m[1][1] - q) +
                      (m[2][2] - q) * (m[2][2] - q) + 2.0 * p1;
    const double p = std::sqrt(p2 / 6.0);
    Mat3 b{};
    for (int r = 0; r < 3; ++r)
      for (int c = 0; c < 3; ++c) b[r][c] = (m[r][c] - (r == c ? q : 0.0)) / p;
    const double rr = std::clamp(det(b) / 2.0, -1.0, 1.0);
    const double phi = std::acos(rr) / 3.0;
    const double e1 = q + 2.0 * p * std::cos(phi);
    const double e3 = q + 2.0 * p * std::cos(phi + 2.0 * kPi / 3.0);
    ev = {e1, 3.0 * q - e1 - e3, e3};
  }
  std::sort(ev.begin(), ev.end());
  return ev;
}

}  // namespace delta_core
