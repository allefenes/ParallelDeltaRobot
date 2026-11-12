// Kenar protokolü v1: sunucu <-> Pi, WebSocket metin çerçevesinde JSON.
// Ayrıştırıcı KATIdır: bilinmeyen tip ya da alan, yanlış sürüm, sonlu olmayan sayı, yanlış dizi
// boyu, sınır dışı period_ms, aşırı nokta sayısı reddedilir. Hiçbir zaman istisna fırlatmaz.
#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <variant>
#include <vector>

#include "delta_edge/types.hpp"

namespace delta_edge {

constexpr int kProtocolVersion = 1;
constexpr int kMinPeriodMs = 5;                            // örnekleme periyodu alt sınırı, ms
constexpr int kMaxPeriodMs = 50;                           // üst sınır, ms
constexpr std::size_t kMaxPoints = 10000;                  // 10 ms'de 100 s hareket
constexpr std::size_t kMaxMessageBytes = 2 * 1024 * 1024;  // 10000 nokta ~0.8 MB; 2 MiB pay
constexpr std::size_t kMaxIdLength = 64;

// --- Sunucu -> Pi ---
struct TrajectoryMsg {
  std::string id;              // [A-Za-z0-9_.:-], 1..64 karakter
  int period_ms{0};            // noktalar arası süre, ms
  std::vector<Angles> points;  // motor açıları, deg; ilk nokta t=0
  std::optional<bool> magnet;  // varsa yörünge başında mıknatıs bu duruma alınır
};
struct HeartbeatMsg {
  std::uint64_t seq{0};  // oturum içinde kesin artan
};
struct StopMsg {};   // yörüngeyi kes, ölçülen konumda dur -> IDLE
struct HoldMsg {};   // yörüngeyi kes, ölçülen konumda tut -> HOLDING (devam için torque on)
struct ResetMsg {};  // ESTOP / FAULT mandalını çöz (koşullar sağlanırsa)
struct TorqueMsg {
  bool on{false};
};
struct MagnetMsg {
  bool on{false};
};

using ServerMessage =
    std::variant<TrajectoryMsg, HeartbeatMsg, StopMsg, HoldMsg, ResetMsg, TorqueMsg, MagnetMsg>;

struct ParseResult {
  std::optional<ServerMessage> message;
  std::string error;  // message boşsa nedeni
  bool ok() const { return message.has_value(); }
};

ParseResult parse_server_message(std::string_view text) noexcept;

// --- Pi -> sunucu ---
struct Telemetry {
  std::string state;
  Angles angles{};      // ölçülen, deg
  Angles temps_c{};     // °C
  Angles loads_pct{};   // %, işaretli
  Angles voltages_v{};  // V
  std::string traj_id;  // boşsa null
  long long index{-1};  // oynatılan nokta indisi; yoksa -1
};

std::string serialize_telemetry(const Telemetry& t);
std::string serialize_fault(std::string_view code, std::string_view detail);
std::string serialize_ack(std::string_view id);

}  // namespace delta_edge
