// Sahte sürücü: testler ve "sanal Pi" için. Birinci dereceden servo dinamiği + hız sınırı,
// basit ısıl model ve hata enjeksiyon kancaları. Zaman dışarıdan verilen saatle ilerler.
#pragma once

#include <functional>
#include <optional>

#include "delta_edge/driver.hpp"

namespace delta_edge {

class MockDriver : public Driver {
 public:
  using Clock = std::function<Micros()>;

  struct Params {
    double tau_s{0.03};             // konum döngüsü zaman sabiti, s
    double max_speed_dps{354.0};    // AX-12A yüksüz hız (59 rpm), deg/s
    double ambient_c{25.0};         // °C
    double temp_tau_s{120.0};       // ısıl zaman sabiti, s
    double temp_per_load{0.4};      // kararlı durumda % yük başına sıcaklık artışı, °C
    double supply_v{12.0};          // V
    Angles initial{0.0, 0.0, 0.0};  // başlangıç açısı, deg
  };

  explicit MockDriver(Clock clock);
  MockDriver(Clock clock, Params params);

  void set_goal(const Angles& angles_deg) override;
  DriverState read_state() override;
  void set_torque(bool on) override;
  void set_magnet(bool on) override;

  // --- Hata enjeksiyonu (testler, sanal Pi) ---
  void inject_temperature(int servo, double celsius);
  void inject_load(int servo, double pct);
  void inject_voltage(double volts);  // tüm servolar
  void set_read_ok(bool ok);
  void clear_injections();

  // --- Gözlem ---
  bool torque() const { return torque_; }
  bool magnet() const { return magnet_; }
  const Angles& goal() const { return goal_; }
  const Angles& position() const { return pos_; }
  long long goal_count() const { return goal_count_; }
  // Gönderilen tüm hedeflerin eklem başına en küçük / en büyük değeri (G1 kanıtı için).
  const Angles& min_goal() const { return min_goal_; }
  const Angles& max_goal() const { return max_goal_; }

 private:
  void advance();
  void step(double h_s);

  Clock clock_;
  Params p_;
  Micros last_;
  Angles pos_{};
  Angles goal_{};
  Angles temps_{};
  Angles loads_{};
  Angles min_goal_{};
  Angles max_goal_{};
  long long goal_count_{0};
  bool torque_{false};
  bool magnet_{false};
  bool read_ok_{true};
  std::optional<double> inj_temp_[3];
  std::optional<double> inj_load_[3];
  std::optional<double> inj_voltage_;
};

// Ayarlanabilir sahte acil stop girişi.
class MockEstop : public EstopInput {
 public:
  void set(bool active) { active_ = active; }
  bool active() override { return active_; }

 private:
  bool active_{false};
};

}  // namespace delta_edge
