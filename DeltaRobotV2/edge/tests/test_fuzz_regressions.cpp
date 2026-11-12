// Fuzz tohum ve regresyon girdileri: her biri ayrıştırıcıdan ve EdgeCore'dan çökmeden geçmeli;
// hiçbir girdi sınır dışı hedefin servolara ulaşmasına yol açmamalı (G1, G4).
#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <sstream>

#include "delta_edge/edge.hpp"
#include "delta_edge/mock_driver.hpp"
#include "test_util.hpp"

namespace delta_edge {
namespace {

namespace fs = std::filesystem;

std::string slurp(const fs::path& p) {
  std::ifstream in(p, std::ios::binary);
  std::stringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

void run_input(const std::string& data) {
  Micros now = 0;
  MockDriver drv([&] { return now; });
  MockEstop estop;
  EdgeCore core(EdgeLimits{}, drv, estop, now);
  // Hazır robot: kalp atışı + tork açık, sonra girdi.
  core.on_message(test::hb_msg(1), now);
  core.on_message(test::on_msg("torque", true), now);
  core.on_message(data, now);
  for (int i = 0; i < 50; ++i) {
    now += 10 * kMicrosPerMs;
    core.on_message(test::hb_msg(2 + i), now);
    core.tick(now);
  }
  if (drv.goal_count() > 0) {
    for (int j = 0; j < 3; ++j) {
      EXPECT_GE(drv.min_goal()[j], -70.0);
      EXPECT_LE(drv.max_goal()[j], 150.0);
    }
  }
}

TEST(FuzzRegressions, G4_CorpusAndRegressionInputsAreSafe) {
  int n = 0;
  for (const char* dir : {"fuzz/corpus", "fuzz/regressions"}) {
    const fs::path d = fs::path(DELTA_EDGE_SRC) / dir;
    if (!fs::exists(d)) continue;
    for (const auto& e : fs::directory_iterator(d)) {
      if (!e.is_regular_file()) continue;
      SCOPED_TRACE(e.path().string());
      const std::string data = slurp(e.path());
      EXPECT_NO_THROW(parse_server_message(data));
      run_input(data);
      ++n;
    }
  }
  EXPECT_GT(n, 5);
}

}  // namespace
}  // namespace delta_edge
