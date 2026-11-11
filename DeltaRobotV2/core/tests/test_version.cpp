#include <gtest/gtest.h>

#include <string>

#include "delta_core/version.hpp"

TEST(Version, MatchesComponents) {
  const std::string expected = std::to_string(delta_core::kVersionMajor) + "." +
                               std::to_string(delta_core::kVersionMinor) + "." +
                               std::to_string(delta_core::kVersionPatch);
  EXPECT_EQ(expected, delta_core::kVersion);
}
