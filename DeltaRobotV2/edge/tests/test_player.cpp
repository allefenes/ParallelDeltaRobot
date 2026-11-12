// Oynatıcı zamanlaması: 100 Hz döngü, enjekte saat, doğrusal ara değerleme.
#include <gtest/gtest.h>

#include "delta_edge/player.hpp"

namespace delta_edge {
namespace {

constexpr Micros kMs = kMicrosPerMs;

std::vector<Angles> ramp(int n) {
  std::vector<Angles> pts;
  for (int k = 0; k < n; ++k) pts.push_back({double(k), -double(k), 2.0 * k});
  return pts;
}

TEST(Player, IndicesAt100HzMatchPeriod10ms) {
  Player p;
  const Micros t0 = 123456789;
  p.start("a", ramp(50), 10, t0);
  ASSERT_TRUE(p.active());
  EXPECT_EQ(p.id(), "a");
  EXPECT_EQ(p.size(), 50u);
  for (int k = 0; k < 49; ++k) {
    const auto s = p.sample(t0 + k * 10 * kMs);  // 100 Hz döngü anları
    EXPECT_EQ(s.index, static_cast<std::size_t>(k));
    EXPECT_DOUBLE_EQ(s.command[0], k);
    EXPECT_DOUBLE_EQ(s.command[1], -k);
    EXPECT_DOUBLE_EQ(s.command[2], 2.0 * k);
    EXPECT_FALSE(s.finished);
  }
  const auto end = p.sample(t0 + 490 * kMs);
  EXPECT_EQ(end.index, 49u);
  EXPECT_TRUE(end.finished);
  EXPECT_DOUBLE_EQ(end.command[0], 49.0);
}

TEST(Player, SlowerPeriodInterpolatesLinearly) {
  Player p;
  p.start("b", ramp(5), 20, 0);
  // 100 Hz döngüde 20 ms periyot: her nokta iki döngü, arada yarı yol.
  auto s = p.sample(10 * kMs);
  EXPECT_EQ(s.index, 0u);
  EXPECT_DOUBLE_EQ(s.command[0], 0.5);
  EXPECT_DOUBLE_EQ(s.command[1], -0.5);
  s = p.sample(20 * kMs);
  EXPECT_EQ(s.index, 1u);
  EXPECT_DOUBLE_EQ(s.command[0], 1.0);
  s = p.sample(25 * kMs);
  EXPECT_DOUBLE_EQ(s.command[0], 1.25);
  s = p.sample(79 * kMs);
  EXPECT_EQ(s.index, 3u);
  EXPECT_FALSE(s.finished);
  s = p.sample(80 * kMs);
  EXPECT_TRUE(s.finished);
  EXPECT_EQ(s.index, 4u);
}

TEST(Player, FasterPeriodSkipsPointsButKeepsTime) {
  Player p;
  p.start("c", ramp(21), 5, 0);  // 5 ms periyot, 100 ms toplam
  const auto s = p.sample(30 * kMs);
  EXPECT_EQ(s.index, 6u);
  EXPECT_DOUBLE_EQ(s.command[0], 6.0);
  EXPECT_TRUE(p.sample(100 * kMs).finished);
  EXPECT_FALSE(p.sample(99 * kMs).finished);
}

TEST(Player, BeforeStartAndAfterEnd) {
  Player p;
  p.start("d", ramp(3), 10, 1000 * kMs);
  const auto before = p.sample(0);
  EXPECT_EQ(before.index, 0u);
  EXPECT_DOUBLE_EQ(before.command[0], 0.0);
  const auto after = p.sample(5000 * kMs);
  EXPECT_TRUE(after.finished);
  EXPECT_DOUBLE_EQ(after.command[2], 4.0);
}

TEST(Player, SinglePointFinishesImmediately) {
  Player p;
  p.start("e", {{1, 2, 3}}, 10, 0);
  const auto s = p.sample(0);
  EXPECT_TRUE(s.finished);
  EXPECT_DOUBLE_EQ(s.command[1], 2.0);
}

TEST(Player, ClearDeactivates) {
  Player p;
  EXPECT_FALSE(p.active());
  p.start("f", ramp(3), 10, 0);
  EXPECT_TRUE(p.active());
  p.clear();
  EXPECT_FALSE(p.active());
  EXPECT_EQ(p.id(), "");
}

}  // namespace
}  // namespace delta_edge
