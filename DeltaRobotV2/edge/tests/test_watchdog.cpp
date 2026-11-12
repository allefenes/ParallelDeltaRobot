// Bekçi eşikleri (G6 T_stop, G7 T_off) ve kalp atışı sıra numarası kuralları.
#include <gtest/gtest.h>

#include "delta_edge/watchdog.hpp"

namespace delta_edge {
namespace {

constexpr Micros kMs = kMicrosPerMs;
constexpr Micros kTick = 10 * kMs;

TEST(Watchdog, NeverFedIsOff) {
  const Watchdog w(200, 1000, kTick);
  EXPECT_EQ(w.level(0), WatchdogLevel::kOff);
  EXPECT_EQ(w.level(1000000 * kMs), WatchdogLevel::kOff);
}

TEST(Watchdog, G6_HoldThresholdIsTStopMinusOneTick) {
  Watchdog w(200, 1000, kTick);
  EXPECT_EQ(w.hold_after_us(), 190 * kMs);
  const Micros t0 = 5000 * kMs;
  ASSERT_TRUE(w.feed(1, t0));
  EXPECT_EQ(w.level(t0), WatchdogLevel::kOk);
  EXPECT_EQ(w.level(t0 + 190 * kMs - 1), WatchdogLevel::kOk);
  EXPECT_EQ(w.level(t0 + 190 * kMs), WatchdogLevel::kHold);
  EXPECT_EQ(w.level(t0 + 200 * kMs), WatchdogLevel::kHold);
}

TEST(Watchdog, G7_OffThresholdIsTOffMinusOneTick) {
  Watchdog w(200, 1000, kTick);
  EXPECT_EQ(w.off_after_us(), 990 * kMs);
  ASSERT_TRUE(w.feed(1, 0));
  EXPECT_EQ(w.level(990 * kMs - 1), WatchdogLevel::kHold);
  EXPECT_EQ(w.level(990 * kMs), WatchdogLevel::kOff);
  EXPECT_EQ(w.level(100000 * kMs), WatchdogLevel::kOff);
}

TEST(Watchdog, ThresholdsFollowConfig) {
  Watchdog w(100, 300, 5 * kMs);
  EXPECT_EQ(w.hold_after_us(), 95 * kMs);
  EXPECT_EQ(w.off_after_us(), 295 * kMs);
  ASSERT_TRUE(w.feed(0, 0));
  EXPECT_EQ(w.level(94 * kMs), WatchdogLevel::kOk);
  EXPECT_EQ(w.level(95 * kMs), WatchdogLevel::kHold);
  EXPECT_EQ(w.level(295 * kMs), WatchdogLevel::kOff);
}

TEST(Watchdog, FreshHeartbeatRestoresOk) {
  Watchdog w(200, 1000, kTick);
  ASSERT_TRUE(w.feed(1, 0));
  EXPECT_EQ(w.level(500 * kMs), WatchdogLevel::kHold);
  ASSERT_TRUE(w.feed(2, 500 * kMs));
  EXPECT_EQ(w.level(500 * kMs), WatchdogLevel::kOk);
  EXPECT_EQ(w.level(689 * kMs), WatchdogLevel::kOk);
}

TEST(Watchdog, RepeatedOrOldSeqIgnored) {
  Watchdog w(200, 1000, kTick);
  ASSERT_TRUE(w.feed(5, 0));
  EXPECT_FALSE(w.feed(5, 150 * kMs));  // tekrar
  EXPECT_FALSE(w.feed(4, 150 * kMs));  // eski
  EXPECT_FALSE(w.feed(0, 150 * kMs));
  // Reddedilen kalp atışı süreyi tazelemez.
  EXPECT_EQ(w.level(190 * kMs), WatchdogLevel::kHold);
  EXPECT_TRUE(w.feed(6, 190 * kMs));
  EXPECT_EQ(w.level(190 * kMs), WatchdogLevel::kOk);
}

TEST(Watchdog, NewSessionResetsSeqButNotTime) {
  Watchdog w(200, 1000, kTick);
  ASSERT_TRUE(w.feed(100, 0));
  w.new_session();
  // Bağlanmak tek başına kalp atışı değildir.
  EXPECT_EQ(w.level(195 * kMs), WatchdogLevel::kHold);
  EXPECT_TRUE(w.feed(0, 195 * kMs));  // yeni oturumda sayaç 0'dan başlayabilir
  EXPECT_EQ(w.level(195 * kMs), WatchdogLevel::kOk);
  EXPECT_FALSE(w.feed(0, 196 * kMs));
}

TEST(Watchdog, FirstHeartbeatAnySeq) {
  Watchdog w(200, 1000, kTick);
  EXPECT_TRUE(w.feed(0, 0));
  Watchdog w2(200, 1000, kTick);
  EXPECT_TRUE(w2.feed(18446744073709551615ull, 0));
  EXPECT_FALSE(w2.feed(18446744073709551615ull, 1));
}

}  // namespace
}  // namespace delta_edge
