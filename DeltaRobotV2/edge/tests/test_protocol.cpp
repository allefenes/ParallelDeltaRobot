// Protokol ayrıştırıcı (G4: bozuk ya da sonlu olmayan veri motorlara ulaşmaz) ve yazıcı.
#include <gtest/gtest.h>

#include <string>

#include "delta_edge/protocol.hpp"
#include "test_util.hpp"

namespace delta_edge {
namespace {

using test::json;

ParseResult parse(const std::string& s) { return parse_server_message(s); }

void expect_reject(const std::string& s) {
  const ParseResult r = parse(s);
  EXPECT_FALSE(r.ok()) << s;
  EXPECT_FALSE(r.error.empty()) << s;
}

TEST(Protocol, ParsesEveryServerMessage) {
  {
    const ParseResult r = parse(R"({"v":1,"type":"heartbeat","seq":42})");
    ASSERT_TRUE(r.ok()) << r.error;
    EXPECT_EQ(std::get<HeartbeatMsg>(*r.message).seq, 42u);
  }
  {
    const ParseResult r = parse(R"({"v":1,"type":"trajectory","id":"t-1.a:b_2","period_ms":10,)"
                                R"("points":[[0,1.5,-2],[3,4,5]],"magnet":true})");
    ASSERT_TRUE(r.ok()) << r.error;
    const auto& t = std::get<TrajectoryMsg>(*r.message);
    EXPECT_EQ(t.id, "t-1.a:b_2");
    EXPECT_EQ(t.period_ms, 10);
    ASSERT_EQ(t.points.size(), 2u);
    EXPECT_DOUBLE_EQ(t.points[0][1], 1.5);
    EXPECT_DOUBLE_EQ(t.points[1][2], 5.0);
    ASSERT_TRUE(t.magnet.has_value());
    EXPECT_TRUE(*t.magnet);
  }
  {
    const ParseResult r =
        parse(R"({"v":1,"type":"trajectory","id":"x","period_ms":5,"points":[[0,0,0]]})");
    ASSERT_TRUE(r.ok()) << r.error;
    EXPECT_FALSE(std::get<TrajectoryMsg>(*r.message).magnet.has_value());
  }
  EXPECT_TRUE(std::holds_alternative<StopMsg>(*parse(R"({"v":1,"type":"stop"})").message));
  EXPECT_TRUE(std::holds_alternative<HoldMsg>(*parse(R"({"v":1,"type":"hold"})").message));
  EXPECT_TRUE(std::holds_alternative<ResetMsg>(*parse(R"({"v":1,"type":"reset"})").message));
  EXPECT_TRUE(std::get<TorqueMsg>(*parse(R"({"v":1,"type":"torque","on":true})").message).on);
  EXPECT_FALSE(std::get<TorqueMsg>(*parse(R"({"v":1,"type":"torque","on":false})").message).on);
  EXPECT_TRUE(std::get<MagnetMsg>(*parse(R"({"v":1,"type":"magnet","on":true})").message).on);
  EXPECT_FALSE(std::get<MagnetMsg>(*parse(R"({"v":1,"type":"magnet","on":false})").message).on);
}

TEST(Protocol, G4_RejectsMalformedJson) {
  expect_reject("");
  expect_reject("{");
  expect_reject("not json");
  expect_reject(R"({"v":1,"type":"stop"} trailing)");
  expect_reject(R"({"v":1,"type":"stop",})");
  expect_reject("[1,2,3]");
  expect_reject("42");
  expect_reject("\xff\xfe");
  expect_reject(R"({"v":1,"type":"stop") "\0" R"(})");
  expect_reject(std::string(R"({"v":1,"type":"tr)") + '\0' + R"(ajectory"})");
}

TEST(Protocol, G4_RejectsNonFiniteNumbers) {
  // JSON'da NaN/Infinity yok; taşan sayılar sonsuza dönüşür ve reddedilmelidir.
  expect_reject(R"({"v":1,"type":"trajectory","id":"a","period_ms":10,"points":[[NaN,0,0]]})");
  expect_reject(R"({"v":1,"type":"trajectory","id":"a","period_ms":10,"points":[[Infinity,0,0]]})");
  expect_reject(R"({"v":1,"type":"trajectory","id":"a","period_ms":10,"points":[[1e400,0,0]]})");
  expect_reject(R"({"v":1,"type":"trajectory","id":"a","period_ms":10,"points":[[0,-1e999,0]]})");
  expect_reject(R"({"v":1,"type":"trajectory","id":"a","period_ms":10,"points":[[0,0,null]]})");
  expect_reject(R"({"v":1,"type":"trajectory","id":"a","period_ms":10,"points":[[0,0,"1"]]})");
  expect_reject(R"({"v":1,"type":"trajectory","id":"a","period_ms":10,"points":[[0,0,true]]})");
}

TEST(Protocol, G4_RejectsWrongArraySizes) {
  const std::string head = R"({"v":1,"type":"trajectory","id":"a","period_ms":10,"points":)";
  expect_reject(head + "[]}");
  expect_reject(head + "[[0,0]]}");
  expect_reject(head + "[[0,0,0,0]]}");
  expect_reject(head + "[[0,0,0],[1,1]]}");
  expect_reject(head + "[0,0,0]}");
  expect_reject(head + "{}}");
  expect_reject(head + "[[[0],0,0]]}");
  expect_reject(R"({"v":1,"type":"trajectory","id":"a","period_ms":10})");
}

TEST(Protocol, RejectsTooManyPointsButAcceptsCap) {
  std::vector<Angles> pts(kMaxPoints, Angles{0, 0, 0});
  EXPECT_TRUE(parse(test::traj_msg("cap", 10, pts)).ok());
  pts.push_back({0, 0, 0});
  const ParseResult r = parse(test::traj_msg("over", 10, pts));
  EXPECT_FALSE(r.ok());
  EXPECT_NE(r.error.find("10000"), std::string::npos);
}

TEST(Protocol, RejectsOversizedMessage) {
  std::string big = R"({"v":1,"type":"stop","pad":")";
  big += std::string(kMaxMessageBytes, 'x');
  big += "\"}";
  const ParseResult r = parse(big);
  EXPECT_FALSE(r.ok());
  EXPECT_NE(r.error.find("büyük"), std::string::npos);
}

TEST(Protocol, PeriodBoundsInclusive) {
  const auto msg = [](const std::string& p) {
    return R"({"v":1,"type":"trajectory","id":"a","period_ms":)" + p + R"(,"points":[[0,0,0]]})";
  };
  EXPECT_TRUE(parse(msg("5")).ok());
  EXPECT_TRUE(parse(msg("50")).ok());
  expect_reject(msg("4"));
  expect_reject(msg("51"));
  expect_reject(msg("0"));
  expect_reject(msg("-10"));
  expect_reject(msg("10.0"));
  expect_reject(msg("10.5"));
  expect_reject(msg("\"10\""));
  expect_reject(msg("18446744073709551615"));
  expect_reject(msg("null"));
}

TEST(Protocol, RejectsWrongVersion) {
  expect_reject(R"({"type":"stop"})");
  expect_reject(R"({"v":0,"type":"stop"})");
  expect_reject(R"({"v":2,"type":"stop"})");
  expect_reject(R"({"v":-1,"type":"stop"})");
  expect_reject(R"({"v":1.0,"type":"stop"})");
  expect_reject(R"({"v":"1","type":"stop"})");
  expect_reject(R"({"v":18446744073709551615,"type":"stop"})");
  expect_reject(R"({"v":9223372036854775808,"type":"stop"})");
}

TEST(Protocol, RejectsUnknownOrMissingType) {
  expect_reject(R"({"v":1})");
  expect_reject(R"({"v":1,"type":5})");
  expect_reject(R"({"v":1,"type":"teleport"})");
  expect_reject(R"({"v":1,"type":"telemetry"})");  // Pi -> sunucu tipi, gelemez
  expect_reject(R"({"v":1,"type":"STOP"})");
  const ParseResult r = parse(R"({"v":1,"type":")" + std::string(500, 'q') + R"("})");
  EXPECT_FALSE(r.ok());
  EXPECT_LT(r.error.size(), 120u);  // hata metni girdiyle büyümez
}

TEST(Protocol, RejectsUnknownFields) {
  expect_reject(R"({"v":1,"type":"stop","x":1})");
  expect_reject(R"({"v":1,"type":"hold","on":true})");
  expect_reject(R"({"v":1,"type":"reset","seq":1})");
  expect_reject(R"({"v":1,"type":"heartbeat","seq":1,"t":0})");
  expect_reject(R"({"v":1,"type":"torque","on":true,"force":1})");
  expect_reject(R"({"v":1,"type":"magnet","on":true,"x":1})");
  expect_reject(
      R"({"v":1,"type":"trajectory","id":"a","period_ms":10,"points":[[0,0,0]],"magent":true})");
}

TEST(Protocol, RejectsBadFieldTypes) {
  expect_reject(R"({"v":1,"type":"heartbeat"})");
  expect_reject(R"({"v":1,"type":"heartbeat","seq":-1})");
  expect_reject(R"({"v":1,"type":"heartbeat","seq":1.5})");
  expect_reject(R"({"v":1,"type":"heartbeat","seq":"1"})");
  expect_reject(R"({"v":1,"type":"torque"})");
  expect_reject(R"({"v":1,"type":"torque","on":1})");
  expect_reject(R"({"v":1,"type":"magnet","on":"true"})");
  expect_reject(R"({"v":1,"type":"magnet","on":null})");
  const std::string tail = R"(,"period_ms":10,"points":[[0,0,0]]})";
  expect_reject(R"({"v":1,"type":"trajectory")" + tail);
  expect_reject(R"({"v":1,"type":"trajectory","id":""")" + tail);
  expect_reject(R"({"v":1,"type":"trajectory","id":5)" + tail);
  expect_reject(R"({"v":1,"type":"trajectory","id":"a b")" + tail);
  expect_reject(R"({"v":1,"type":"trajectory","id":"a/b")" + tail);
  expect_reject(R"({"v":1,"type":"trajectory","id":"ğ")" + tail);
  expect_reject(R"({"v":1,"type":"trajectory","id":")" + std::string(65, 'a') + "\"" + tail);
  EXPECT_TRUE(
      parse(R"({"v":1,"type":"trajectory","id":")" + std::string(64, 'a') + "\"" + tail).ok());
  // Kimlikte izin verilen her karakter sınıfı.
  EXPECT_TRUE(parse(R"({"v":1,"type":"trajectory","id":"azAZ09_-.:")" + tail).ok());
  expect_reject(R"({"v":1,"type":"trajectory","id":"a@")" + tail);
  expect_reject(R"({"v":1,"type":"trajectory","id":"a[")" + tail);
  expect_reject(R"({"v":1,"type":"trajectory","id":"a{")" + tail);
  expect_reject(R"({"v":1,"type":"trajectory","id":"a`")" + tail);
  expect_reject(R"({"v":1,"type":"trajectory","id":"a/")" + tail);
  expect_reject(R"({"v":1,"type":"trajectory","id":"a;")" + tail);
  expect_reject(
      R"({"v":1,"type":"trajectory","id":"a","period_ms":10,"points":[[0,0,0]],"magnet":1})");
}

TEST(Protocol, NeverThrowsOnHostileInput) {
  // Derin iç içe dizi: yığın taşmamalı, istisna fırlatmamalı.
  std::string deep(100000, '[');
  deep += std::string(100000, ']');
  EXPECT_NO_THROW({
    const ParseResult r = parse(deep);
    EXPECT_FALSE(r.ok());
  });
}

TEST(Protocol, SerializesOutgoingMessages) {
  Telemetry t;
  t.state = "RUNNING";
  t.angles = {1, 2, 3};
  t.temps_c = {30, 31, 32};
  t.loads_pct = {-5, 0, 5};
  t.voltages_v = {12, 12, 12};
  t.traj_id = "abc";
  t.index = 7;
  const json j = json::parse(serialize_telemetry(t));
  EXPECT_EQ(j["v"], 1);
  EXPECT_EQ(j["type"], "telemetry");
  EXPECT_EQ(j["state"], "RUNNING");
  EXPECT_EQ(j["angles"], json::array({1.0, 2.0, 3.0}));
  EXPECT_EQ(j["temps"][2], 32.0);
  EXPECT_EQ(j["loads"][0], -5.0);
  EXPECT_EQ(j["voltages"][1], 12.0);
  EXPECT_EQ(j["traj_id"], "abc");
  EXPECT_EQ(j["index"], 7);

  t.traj_id.clear();
  EXPECT_TRUE(json::parse(serialize_telemetry(t))["traj_id"].is_null());

  const json f = json::parse(serialize_fault("joint_limit", "nokta 3"));
  EXPECT_EQ(f["v"], 1);
  EXPECT_EQ(f["type"], "fault");
  EXPECT_EQ(f["code"], "joint_limit");
  EXPECT_EQ(f["detail"], "nokta 3");

  const json a = json::parse(serialize_ack("t1"));
  EXPECT_EQ(a["type"], "ack");
  EXPECT_EQ(a["id"], "t1");
  EXPECT_EQ(a["v"], 1);

  // Geçersiz UTF-8 ayrıntı istisna fırlatmaz.
  EXPECT_NO_THROW(serialize_fault("x", "\xff\xfe"));
}

}  // namespace
}  // namespace delta_edge
