// Sunucu adresi ayrıştırma: yalnız wss:// (TLS zorunlu).
#pragma once

#include <optional>
#include <string>
#include <string_view>

namespace delta_edge {

struct ServerUrl {
  std::string host;
  std::string port{"443"};
  std::string path{"/"};
  // HTTP Host başlığı: IPv6 adresi köşeli parantezli.
  std::string host_header() const;
};

std::optional<ServerUrl> parse_server_url(std::string_view url, std::string* error);

}  // namespace delta_edge
