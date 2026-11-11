// Delta robot kinematiği: ileri/ters kinematik, Jacobian, limit kontrolü.
//
// Çerçeve (V2): orijin üç motor ekseninin düzleminin merkezi, +Z yukarı. Kol i için
//   u_i = (cos a_i, sin a_i, 0)  radyal dışa,  t_i = (-sin a_i, cos a_i, 0)  motor ekseni.
// Motor açısı θ (derece): 0'da kısa kol u_i yönünde yatay; pozitif θ kolu aşağı indirir.
// P: platform eklem düzleminin merkezi (alt küresel eklem merkezlerinin ortalaması), mm.
// V1'de +Z aşağıydı: V2 (x, y, z) = V1 (x, -y, -z), kol sırası V2 [1,2,3] = V1 [1,3,2].
#pragma once

#include <array>
#include <optional>
#include <string>

#include "delta_core/params.hpp"
#include "delta_core/vec3.hpp"

namespace delta_core {

using Angles = std::array<double, 3>;  // motor açıları, derece

// Limit kontrolünün sonucu; ok=false ise `reason` neden reddedildiğini, `arm` hangi kol
// olduğunu (0..2, kolla ilgisizse -1) söyler.
struct LimitCheck {
  bool ok{true};
  int arm{-1};
  std::string reason;
};

class DeltaKinematics {
 public:
  explicit DeltaKinematics(DeltaParams params);

  const DeltaParams& params() const { return p_; }

  // Kol i'nin motor ekseni noktası A_i.
  Vec3 shoulder(int i) const;
  // Kol i'nin üst küresel eklem merkezi B_i (θ derece).
  Vec3 elbow(int i, double theta_deg) const;
  // Kol i'nin alt küresel eklem merkezi C_i = P + r·u_i (platform yönelimi sabit).
  Vec3 wrist(int i, const Vec3& P) const;

  // Ters kinematik: P -> θ. Erişilemezse boş. Dirseği dışarıda tutan kök seçilir.
  std::optional<Angles> inverse(const Vec3& P) const;
  // İleri kinematik: θ -> P. Üç kürenin kesişimi; platformun aşağıdaki çözümü seçilir.
  std::optional<Vec3> forward(const Angles& theta_deg) const;

  // Jacobian J = dP/dθ (mm/rad), satır=P bileşeni, sütun=motor. Tekil konumda boş.
  std::optional<Mat3> jacobian(const Angles& theta_deg) const;
  // J'nin koşul sayısı (σ_max/σ_min). Tekil konumda +sonsuz.
  double condition_number(const Angles& theta_deg) const;

  // Kol i'nin uzun kolunun motor eksenine dik düzlemden sapması (rot başı yanal açısı), derece.
  double rod_tilt_deg(int i, double theta_deg, const Vec3& P) const;

  // Motor açı limitleri ve rot başı sınırı. Sayı olmayan (NaN/sonsuz) girdi reddedilir.
  LimitCheck check_limits(const Angles& theta_deg, const Vec3& P) const;
  // P için ters kinematik + limit kontrolü; erişilemezse ok=false.
  LimitCheck check_point(const Vec3& P) const;

 private:
  DeltaParams p_;
  std::array<Vec3, 3> u_{};
  std::array<Vec3, 3> t_{};
};

// Simetrik 3x3 matrisin özdeğerleri (artan sırada); analitik yöntem.
std::array<double, 3> symmetric_eigenvalues(const Mat3& m);

}  // namespace delta_core
