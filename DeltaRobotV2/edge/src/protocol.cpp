// Kenar protokolü v1 ayrıştırıcı ve yazıcı (nlohmann-json, istisnasız ayrıştırma).
#include "delta_edge/protocol.hpp"

#include <cmath>
#include <initializer_list>
#include <limits>
#include <nlohmann/json.hpp>

namespace delta_edge {
namespace {

using nlohmann::json;

ParseResult fail(std::string why) {
  ParseResult r;
  r.error = std::move(why);
  return r;
}

ParseResult pass(ServerMessage m) {
  ParseResult r;
  r.message = std::move(m);
  return r;
}

// Bilinmeyen alan sessizce yok sayılmaz: yanlış yazılmış bir alan (ör. "magent") hata olmalı.
bool only_keys(const json& j, std::initializer_list<std::string_view> allowed, std::string* bad) {
  for (const auto& item : j.items()) {
    bool found = false;
    for (std::string_view a : allowed) {
      if (item.key() == a) {
        found = true;
        break;
      }
    }
    if (!found) {
      *bad = item.key().substr(0, 32);
      return false;
    }
  }
  return true;
}

// Tam sayı (işaretli/işaretsiz); kayan noktalı (1.0) ve int64 dışı kabul edilmez.
std::optional<std::int64_t> as_int(const json& j) {
  if (j.is_number_unsigned()) {
    const auto u = j.get<std::uint64_t>();
    if (u > static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()))
      return std::nullopt;
    return static_cast<std::int64_t>(u);
  }
  if (j.is_number_integer()) return j.get<std::int64_t>();
  return std::nullopt;
}

bool valid_id(const std::string& id) {
  if (id.empty() || id.size() > kMaxIdLength) return false;
  for (char c : id) {
    const bool ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
                    c == '_' || c == '-' || c == '.' || c == ':';
    if (!ok) return false;
  }
  return true;
}

std::optional<bool> get_on(const json& j) {
  const auto on = j.find("on");
  if (on == j.end() || !on->is_boolean()) return std::nullopt;
  return on->get<bool>();
}

ParseResult parse_trajectory(const json& j) {
  TrajectoryMsg m;
  const auto id = j.find("id");
  if (id == j.end() || !id->is_string() || !valid_id(id->get<std::string>()))
    return fail("trajectory.id 1..64 karakter [A-Za-z0-9_.:-] olmalı");
  m.id = id->get<std::string>();

  const auto period = j.find("period_ms");
  const std::optional<std::int64_t> p = period == j.end() ? std::nullopt : as_int(*period);
  if (!p || *p < kMinPeriodMs || *p > kMaxPeriodMs)
    return fail("trajectory.period_ms " + std::to_string(kMinPeriodMs) + ".." +
                std::to_string(kMaxPeriodMs) + " aralığında tam sayı olmalı");
  m.period_ms = static_cast<int>(*p);

  const auto magnet = j.find("magnet");
  if (magnet != j.end()) {
    if (!magnet->is_boolean()) return fail("trajectory.magnet mantıksal değer olmalı");
    m.magnet = magnet->get<bool>();
  }

  const auto pts = j.find("points");
  if (pts == j.end() || !pts->is_array()) return fail("trajectory.points dizi olmalı");
  if (pts->empty()) return fail("trajectory.points boş");
  if (pts->size() > kMaxPoints)
    return fail("trajectory.points en fazla " + std::to_string(kMaxPoints) + " nokta");
  m.points.reserve(pts->size());
  for (std::size_t i = 0; i < pts->size(); ++i) {
    const json& pt = (*pts)[i];
    if (!pt.is_array() || pt.size() != 3)
      return fail("trajectory.points[" + std::to_string(i) + "] 3 elemanlı dizi olmalı");
    Angles a{};
    for (std::size_t k = 0; k < 3; ++k) {
      if (!pt[k].is_number())
        return fail("trajectory.points[" + std::to_string(i) + "] sayı olmayan değer");
      a[k] = pt[k].get<double>();
      if (!std::isfinite(a[k]))
        return fail("trajectory.points[" + std::to_string(i) + "] sonlu olmayan değer");
    }
    m.points.push_back(a);
  }
  return pass(std::move(m));
}

ParseResult parse_impl(std::string_view text) {
  if (text.size() > kMaxMessageBytes) return fail("mesaj çok büyük");
  const json j = json::parse(text.begin(), text.end(), nullptr, /*allow_exceptions=*/false);
  if (j.is_discarded()) return fail("bozuk JSON");
  if (!j.is_object()) return fail("kök JSON nesnesi değil");

  const auto t = j.find("type");
  if (t == j.end() || !t->is_string()) return fail("'type' alanı eksik ya da metin değil");
  const auto v = j.find("v");
  const std::optional<std::int64_t> ver = v == j.end() ? std::nullopt : as_int(*v);
  if (!ver || *ver != kProtocolVersion)
    return fail("desteklenmeyen protokol sürümü (beklenen v=" + std::to_string(kProtocolVersion) +
                ")");

  const std::string& type = t->get_ref<const std::string&>();
  std::string bad;
  const auto unknown = [&bad, &type]() { return fail(type + ": bilinmeyen alan '" + bad + "'"); };

  if (type == "heartbeat") {
    if (!only_keys(j, {"v", "type", "seq"}, &bad)) return unknown();
    const auto seq = j.find("seq");
    if (seq == j.end() || !seq->is_number_unsigned())
      return fail("heartbeat.seq negatif olmayan tam sayı olmalı");
    return pass(HeartbeatMsg{seq->get<std::uint64_t>()});
  }
  if (type == "trajectory") {
    if (!only_keys(j, {"v", "type", "id", "period_ms", "points", "magnet"}, &bad)) return unknown();
    return parse_trajectory(j);
  }
  if (type == "stop" || type == "hold" || type == "reset") {
    if (!only_keys(j, {"v", "type"}, &bad)) return unknown();
    if (type == "stop") return pass(StopMsg{});
    if (type == "hold") return pass(HoldMsg{});
    return pass(ResetMsg{});
  }
  if (type == "torque" || type == "magnet") {
    if (!only_keys(j, {"v", "type", "on"}, &bad)) return unknown();
    const std::optional<bool> on = get_on(j);
    if (!on) return fail(type + ".on mantıksal değer olmalı");
    if (type == "torque") return pass(TorqueMsg{*on});
    return pass(MagnetMsg{*on});
  }
  return fail("bilinmeyen mesaj tipi '" + type.substr(0, 32) + "'");
}

std::string dump(const json& j) {
  // Geçersiz UTF-8 istisna fırlatmasın: değiştirilerek yazılır.
  return j.dump(-1, ' ', false, json::error_handler_t::replace);
}

}  // namespace

ParseResult parse_server_message(std::string_view text) noexcept {
  try {
    return parse_impl(text);
  } catch (...) {
    // nlohmann allow_exceptions=false ile parse etmez; kalan tek olasılık bellek yetersizliği.
    return fail("ayrıştırma sırasında iç hata");
  }
}

std::string serialize_telemetry(const Telemetry& t) {
  json j = {{"v", kProtocolVersion},    {"type", "telemetry"}, {"state", t.state},
            {"angles", t.angles},       {"temps", t.temps_c},  {"loads", t.loads_pct},
            {"voltages", t.voltages_v}, {"index", t.index},    {"magnet", t.magnet}};
  if (t.traj_id.empty()) {
    j["traj_id"] = nullptr;
  } else {
    j["traj_id"] = t.traj_id;
  }
  return dump(j);
}

std::string serialize_fault(std::string_view code, std::string_view detail) {
  const json j = {{"v", kProtocolVersion},
                  {"type", "fault"},
                  {"code", std::string(code)},
                  {"detail", std::string(detail)}};
  return dump(j);
}

std::string serialize_ack(std::string_view id) {
  const json j = {{"v", kProtocolVersion}, {"type", "ack"}, {"id", std::string(id)}};
  return dump(j);
}

}  // namespace delta_edge
