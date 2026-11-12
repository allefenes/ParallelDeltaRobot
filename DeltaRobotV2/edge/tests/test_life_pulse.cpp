// G13: donanım bekçisi yaşam darbesi. Döngü çalıştıkça çıkış her tick'te ters çevrilir; döngü
// durursa (takılma, çökme) yeni kenar oluşmaz ve dış monostable servo gücünü keser.
#include <gtest/gtest.h>

#include <vector>

#include "delta_edge/life_pulse.hpp"

namespace delta_edge {
namespace {

class RecordingOutput : public PulseOutput {
 public:
  void write(bool level) override { levels.push_back(level); }
  std::vector<bool> levels;
};

TEST(LifePulse, G13_TogglesOncePerCompletedTick) {
  RecordingOutput out;
  LifePulse pulse(out);
  for (int i = 0; i < 6; ++i) pulse.on_tick_completed();
  EXPECT_EQ(pulse.edges(), 6u);
  ASSERT_EQ(out.levels.size(), 6u);
  for (std::size_t i = 0; i < out.levels.size(); ++i) {
    EXPECT_EQ(out.levels[i], i % 2 == 0) << "kare dalga, kenar " << i;
  }
}

TEST(LifePulse, G13_NoEdgesWhenLoopStops) {
  // Döngü öldüğünde on_tick_completed çağrılmaz: çıkış son seviyede donar, kenar gelmez.
  RecordingOutput out;
  LifePulse pulse(out);
  pulse.on_tick_completed();
  pulse.on_tick_completed();
  const auto before = out.levels;
  // ... döngü durdu: hiçbir çağrı yok ...
  EXPECT_EQ(out.levels, before);
  EXPECT_EQ(pulse.edges(), 2u);
}

TEST(LifePulse, G13_StartsLowSoFirstEdgeIsRising) {
  RecordingOutput out;
  LifePulse pulse(out);
  pulse.on_tick_completed();
  EXPECT_TRUE(out.levels.front());
}

}  // namespace
}  // namespace delta_edge
