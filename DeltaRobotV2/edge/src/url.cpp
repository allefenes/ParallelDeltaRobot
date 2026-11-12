// wss://host[:port][/path] ayrıştırıcı. Kullanıcı bilgisi (user@) ve TLS'siz şema reddedilir.
#include "delta_edge/url.hpp"

namespace delta_edge {
namespace {

std::optional<ServerUrl> fail(std::string* error, const char* why) {
  if (error) *error = why;
  return std::nullopt;
}

}  // namespace

std::string ServerUrl::host_header() const {
  const bool ipv6 = host.find(':') != std::string::npos;
  return (ipv6 ? "[" + host + "]" : host) + ":" + port;
}

std::optional<ServerUrl> parse_server_url(std::string_view url, std::string* error) {
  constexpr std::string_view kScheme = "wss://";
  if (url.substr(0, kScheme.size()) != kScheme)
    return fail(error, "yalnız wss:// desteklenir (TLS zorunlu)");
  url.remove_prefix(kScheme.size());

  const std::size_t slash = url.find('/');
  const std::string_view authority = url.substr(0, slash);
  ServerUrl out;
  if (slash != std::string_view::npos) out.path = std::string(url.substr(slash));
  if (authority.empty()) return fail(error, "sunucu adı eksik");
  if (authority.find('@') != std::string_view::npos)
    return fail(error, "adreste kullanıcı bilgisi olamaz");

  std::string_view port;
  if (authority.front() == '[') {
    const std::size_t close = authority.find(']');
    if (close == std::string_view::npos) return fail(error, "IPv6 adresi kapanmamış");
    out.host = std::string(authority.substr(1, close - 1));
    const std::string_view rest = authority.substr(close + 1);
    if (!rest.empty()) {
      if (rest.front() != ':') return fail(error, "IPv6 adresinden sonra ':' bekleniyor");
      port = rest.substr(1);
      if (port.empty()) return fail(error, "port boş");
    }
  } else {
    const std::size_t colon = authority.rfind(':');
    out.host = std::string(authority.substr(0, colon));
    if (colon != std::string_view::npos) {
      port = authority.substr(colon + 1);
      if (port.empty()) return fail(error, "port boş");
    }
  }
  if (out.host.empty()) return fail(error, "sunucu adı eksik");
  if (!port.empty()) {
    if (port.size() > 5) return fail(error, "geçersiz port");
    long value = 0;
    for (char c : port) {
      if (c < '0' || c > '9') return fail(error, "geçersiz port");
      value = value * 10 + (c - '0');
    }
    if (value < 1 || value > 65535) return fail(error, "port 1..65535 olmalı");
    out.port = std::string(port);
  }
  return out;
}

}  // namespace delta_edge
