// Sunucu adresi ayrıştırma: yalnız wss://.
#include <gtest/gtest.h>

#include "delta_edge/url.hpp"

namespace delta_edge {
namespace {

TEST(Url, ParsesHostPortPath) {
  std::string err;
  auto u = parse_server_url("wss://server:8443/edge", &err);
  ASSERT_TRUE(u) << err;
  EXPECT_EQ(u->host, "server");
  EXPECT_EQ(u->port, "8443");
  EXPECT_EQ(u->path, "/edge");
  EXPECT_EQ(u->host_header(), "server:8443");

  u = parse_server_url("wss://example.org", &err);
  ASSERT_TRUE(u);
  EXPECT_EQ(u->port, "443");
  EXPECT_EQ(u->path, "/");

  u = parse_server_url("wss://[::1]:9000/a/b?x=1", &err);
  ASSERT_TRUE(u) << err;
  EXPECT_EQ(u->host, "::1");
  EXPECT_EQ(u->port, "9000");
  EXPECT_EQ(u->path, "/a/b?x=1");
  EXPECT_EQ(u->host_header(), "[::1]:9000");

  u = parse_server_url("wss://[fe80::2]", &err);
  ASSERT_TRUE(u) << err;
  EXPECT_EQ(u->port, "443");
}

TEST(Url, RejectsInvalid) {
  std::string err;
  for (const char* bad :
       {"ws://server/edge", "https://x", "server:8443", "", "wss://", "wss:///edge",
        "wss://:8443/x", "wss://host:/x", "wss://host:0", "wss://host:65536", "wss://host:12a",
        "wss://host:123456", "wss://user@host/x", "wss://[::1", "wss://[::1]x",
        "wss://[::1]:", "wss://[]:80"}) {
    EXPECT_FALSE(parse_server_url(bad, &err)) << bad;
    EXPECT_FALSE(err.empty()) << bad;
  }
  EXPECT_FALSE(parse_server_url("ws://x", nullptr));
  EXPECT_TRUE(parse_server_url("wss://h:65535", nullptr));
  EXPECT_TRUE(parse_server_url("wss://h:1", nullptr));
}

}  // namespace
}  // namespace delta_edge
