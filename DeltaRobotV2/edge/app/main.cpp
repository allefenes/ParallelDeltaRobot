// delta_edge: Raspberry Pi kenar servisi (ya da sanal Pi). Ağ katmanı incedir: tüm karar
// EdgeCore'dadır. Tek iş parçacığı, tek io_context: döngü zamanlayıcısı, WebSocket okuma/yazma ve
// yeniden bağlanma aynı sırada çalışır; EdgeCore'a eşzamanlı erişim yoktur.
//
// Bağlantıyı Pi açar (wss://, TLS zorunlu). Bağlantı yokken döngü sürer: bekçi T_stop'ta tutar,
// T_off'ta torku keser. Bağlantı yokken üretilen telemetri ve hata mesajları düşürülür.
#include <openssl/ssl.h>

#include <algorithm>
#include <boost/asio.hpp>
#include <boost/asio/ssl.hpp>
#include <boost/beast/core.hpp>
#include <boost/beast/ssl.hpp>
#include <boost/beast/websocket.hpp>
#include <boost/beast/websocket/ssl.hpp>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <deque>
#include <filesystem>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>

#include "delta_edge/ax12_driver.hpp"
#include "delta_edge/config.hpp"
#include "delta_edge/edge.hpp"
#include "delta_edge/mock_driver.hpp"
#include "delta_edge/url.hpp"

namespace {

namespace net = boost::asio;
namespace ssl = net::ssl;
namespace beast = boost::beast;
namespace websocket = beast::websocket;
using tcp = net::ip::tcp;
using delta_edge::Micros;
using std::chrono::milliseconds;

constexpr int kExitUsage = 2;           // yapılandırma / kullanım hatası
constexpr int kExitUnreachable = 3;     // --max-retries doldu
constexpr std::size_t kMaxQueue = 256;  // gönderim kuyruğu; doluysa en eskisi düşer
constexpr auto kConnectTimeout = std::chrono::seconds(5);
constexpr auto kBackoffMin = milliseconds(500);
constexpr auto kBackoffMax = milliseconds(30000);

Micros mono_now() {
  return std::chrono::duration_cast<std::chrono::microseconds>(
             std::chrono::steady_clock::now().time_since_epoch())
      .count();
}

std::string env_or(const char* name, const std::string& fallback) {
  const char* v = std::getenv(name);
  return (v && *v) ? std::string(v) : fallback;
}

void log_line(const std::string& msg) { std::cerr << "[delta_edge] " << msg << std::endl; }

void print_help() {
  std::cout <<
      R"(delta_edge: Delta Robotics V2 Raspberry Pi kenar servisi

Kullanım: delta_edge [seçenekler]

Seçenekler:
  --url URL            sunucu adresi (wss://host[:port]/yol); ortam: DELTA_SERVER_URL
  --robot-config PATH  robot.yaml (eklem limitleri); ortam: DELTA_ROBOT_YAML
                       varsayılan: config/robot.yaml
  --edge-config PATH   edge.yaml (kenar sınırları); ortam: DELTA_EDGE_YAML
                       varsayılan: edge/config/edge.yaml
  --max-retries N      art arda N başarısız bağlantıdan sonra 3 koduyla çık (0 = sınırsız);
                       ortam: DELTA_MAX_RETRIES
  --version            sürümü yaz
  -h, --help           bu yardım

Ortam değişkenleri:
  DELTA_DRIVER=mock|ax12  motor sürücüsü (ax12: F5'te; şimdilik desteklenmez)
  DELTA_CA_FILE=PATH      sunucu sertifikasını doğrulayan CA dosyası (yoksa sistem CA'ları)
  DELTA_INSECURE=1        YALNIZ GELİŞTİRME: sertifika doğrulaması kapalı
  DELTA_EDGE_TOKEN=...    WebSocket el sıkışmasında "Authorization: Bearer" belirteci
  DELTA_ESTOP_FILE=PATH   sanal Pi: bu dosya varsa acil stop girişi etkin

Çıkış kodları: 0 normal (SIGINT/SIGTERM), 2 kullanım/yapılandırma hatası, 3 sunucuya ulaşılamadı.
)";
}

// Sanal Pi acil stop girişi: dosyanın varlığı = buton basılı.
class FileEstop : public delta_edge::EstopInput {
 public:
  explicit FileEstop(std::string path) : path_(std::move(path)) {}
  bool active() override {
    std::error_code ec;
    return !path_.empty() && std::filesystem::exists(path_, ec);
  }

 private:
  std::string path_;
};

struct Options {
  std::string url;
  std::string robot_yaml;
  std::string edge_yaml;
  std::string ca_file;
  std::string token;
  std::string driver;
  std::string estop_file;
  bool insecure{false};
  int max_retries{0};
};

class App {
 public:
  App(const Options& opt, const delta_edge::ServerUrl& url, const delta_edge::EdgeLimits& limits,
      delta_edge::Driver& driver, delta_edge::EstopInput& estop)
      : opt_(opt),
        url_(url),
        ctx_(ssl::context::tls_client),
        resolver_(ioc_),
        tick_timer_(ioc_),
        reconnect_timer_(ioc_),
        signals_(ioc_, SIGINT, SIGTERM),
        core_(limits, driver, estop, mono_now()),
        period_(std::chrono::microseconds(limits.tick_period_us())) {}

  // TLS bağlamı; hata varsa açıklama döner.
  std::string configure_tls() {
    SSL_CTX_set_min_proto_version(ctx_.native_handle(), TLS1_2_VERSION);
    beast::error_code ec;
    if (opt_.insecure) {
      log_line("UYARI: DELTA_INSECURE=1, sertifika doğrulaması KAPALI (yalnız geliştirme)");
      ctx_.set_verify_mode(ssl::verify_none);
      return {};
    }
    ctx_.set_verify_mode(ssl::verify_peer);
    if (!opt_.ca_file.empty()) {
      ctx_.load_verify_file(opt_.ca_file, ec);
      if (ec) return "CA dosyası okunamadı: " + opt_.ca_file + ": " + ec.message();
    } else {
      ctx_.set_default_verify_paths(ec);
      if (ec) return "sistem CA'ları yüklenemedi: " + ec.message();
    }
    return {};
  }

  int run() {
    signals_.async_wait([this](const beast::error_code& ec, int sig) {
      if (ec) return;
      log_line("sinyal " + std::to_string(sig) + ": kapanıyor (mıknatıs ve tork kapatılıyor)");
      stop(0);
    });
    next_tick_ = std::chrono::steady_clock::now();
    schedule_tick();
    connect();
    ioc_.run();
    return exit_code_;
  }

 private:
  using Ws = websocket::stream<beast::ssl_stream<beast::tcp_stream>>;

  void stop(int code) {
    if (stopping_) return;
    stopping_ = true;
    exit_code_ = code;
    core_.shutdown();
    ++gen_;
    if (ws_) beast::get_lowest_layer(*ws_).close();
    ioc_.stop();
  }

  void schedule_tick() {
    tick_timer_.expires_at(next_tick_);
    tick_timer_.async_wait([this](const beast::error_code& ec) {
      if (ec || stopping_) return;
      on_tick();
    });
  }

  void on_tick() {
    const delta_edge::State before = core_.state();
    for (auto& m : core_.tick(mono_now())) send(std::move(m));
    if (core_.state() != before) {
      log_line(std::string("durum ") + delta_edge::state_name(before) + " -> " +
               delta_edge::state_name(core_.state()));
    }
    // Sabit hızlı zamanlama; gecikmede adım atlanır (birikmez).
    next_tick_ += period_;
    const auto now = std::chrono::steady_clock::now();
    if (next_tick_ < now) next_tick_ = now + period_;
    schedule_tick();
  }

  void connect() {
    const std::uint64_t g = ++gen_;
    ws_ = std::make_shared<Ws>(ioc_, ctx_);
    auto ws = ws_;
    log_line("bağlanılıyor: wss://" + url_.host_header() + url_.path);
    resolver_.async_resolve(
        url_.host, url_.port,
        [this, g, ws](const beast::error_code& ec, const tcp::resolver::results_type& res) {
          if (g != gen_) return;
          if (ec) return fail("ad çözümlenemedi", ec);
          beast::get_lowest_layer(*ws).expires_after(kConnectTimeout);
          beast::get_lowest_layer(*ws).async_connect(
              res, [this, g, ws](const beast::error_code& ec2, const tcp::endpoint&) {
                if (g != gen_) return;
                if (ec2) return fail("TCP bağlantısı kurulamadı", ec2);
                on_tcp(g, ws);
              });
        });
  }

  void on_tcp(std::uint64_t g, const std::shared_ptr<Ws>& ws) {
    if (!SSL_set_tlsext_host_name(ws->next_layer().native_handle(), url_.host.c_str())) {
      return fail("SNI ayarlanamadı", beast::error_code(static_cast<int>(::ERR_get_error()),
                                                        net::error::get_ssl_category()));
    }
    if (!opt_.insecure)
      ws->next_layer().set_verify_callback(ssl::host_name_verification(url_.host));
    ws->next_layer().async_handshake(ssl::stream_base::client,
                                     [this, g, ws](const beast::error_code& ec) {
                                       if (g != gen_) return;
                                       if (ec) return fail("TLS el sıkışması başarısız", ec);
                                       on_tls(g, ws);
                                     });
  }

  void on_tls(std::uint64_t g, const std::shared_ptr<Ws>& ws) {
    beast::get_lowest_layer(*ws).expires_never();
    websocket::stream_base::timeout to{};
    to.handshake_timeout = kConnectTimeout;
    to.idle_timeout = std::chrono::seconds(5);  // sunucu ~50 ms'de bir kalp atışı yollar
    to.keep_alive_pings = true;
    ws->set_option(to);
    ws->set_option(
        websocket::stream_base::decorator([token = opt_.token](websocket::request_type& req) {
          req.set(beast::http::field::user_agent, "delta_edge/" DELTA_EDGE_VERSION);
          if (!token.empty()) req.set(beast::http::field::authorization, "Bearer " + token);
        }));
    ws->read_message_max(delta_edge::kMaxMessageBytes);
    ws->async_handshake(url_.host_header(), url_.path, [this, g, ws](const beast::error_code& ec) {
      if (g != gen_) return;
      if (ec) return fail("WebSocket el sıkışması başarısız", ec);
      connected_ = true;
      attempts_ = 0;
      core_.on_connection_open();
      log_line("bağlandı");
      do_read(g, ws);
    });
  }

  void do_read(std::uint64_t g, const std::shared_ptr<Ws>& ws) {
    ws->async_read(rx_, [this, g, ws](const beast::error_code& ec, std::size_t) {
      if (g != gen_) return;
      if (ec) return fail("okuma", ec);
      const std::string text = beast::buffers_to_string(rx_.data());
      rx_.consume(rx_.size());
      for (auto& m : core_.on_message(text, mono_now())) send(std::move(m));
      do_read(g, ws);
    });
  }

  void send(std::string msg) {
    if (!connected_) return;
    queue_.push_back(std::move(msg));
    if (queue_.size() > kMaxQueue) queue_.pop_front();
    if (!writing_) do_write();
  }

  void do_write() {
    writing_ = true;
    // Yazılan mesaj işleyici bitene kadar yaşamalı: kuyruk temizlense bile tampon geçerli kalır.
    auto msg = std::make_shared<std::string>(std::move(queue_.front()));
    queue_.pop_front();
    const std::uint64_t g = gen_;
    auto ws = ws_;
    ws->text(true);
    ws->async_write(net::buffer(*msg),
                    [this, g, ws, msg](const beast::error_code& ec, std::size_t) {
                      if (g != gen_) return;
                      writing_ = false;
                      if (ec) return fail("yazma", ec);
                      if (!queue_.empty()) do_write();
                    });
  }

  void fail(const std::string& what, const beast::error_code& ec) {
    if (stopping_) return;
    log_line(what + ": " + ec.message());
    ++gen_;  // eski işleyiciler sessizce düşer
    if (ws_) {
      beast::get_lowest_layer(*ws_).close();
      ws_.reset();
    }
    queue_.clear();
    writing_ = false;
    rx_.consume(rx_.size());
    if (connected_) log_line("bağlantı koptu; bekçi devrede");
    connected_ = false;
    ++attempts_;
    if (opt_.max_retries > 0 && attempts_ >= opt_.max_retries) {
      log_line("sunucuya ulaşılamadı (" + std::to_string(attempts_) + " deneme): wss://" +
               url_.host_header() + url_.path + "; çıkılıyor");
      stop(kExitUnreachable);
      return;
    }
    const int shift = std::min(attempts_ - 1, 10);
    const auto delay = std::min(kBackoffMin * (1 << shift), kBackoffMax);
    log_line("yeniden bağlanma " + std::to_string(delay.count()) + " ms sonra");
    reconnect_timer_.expires_after(delay);
    reconnect_timer_.async_wait([this](const beast::error_code& e) {
      if (!e && !stopping_) connect();
    });
  }

  const Options& opt_;
  delta_edge::ServerUrl url_;
  net::io_context ioc_;
  ssl::context ctx_;
  tcp::resolver resolver_;
  net::steady_timer tick_timer_;
  net::steady_timer reconnect_timer_;
  net::signal_set signals_;
  delta_edge::EdgeCore core_;
  std::chrono::steady_clock::duration period_;
  std::chrono::steady_clock::time_point next_tick_;
  std::shared_ptr<Ws> ws_;
  beast::flat_buffer rx_;
  std::deque<std::string> queue_;
  std::uint64_t gen_{0};
  int attempts_{0};
  int exit_code_{0};
  bool connected_{false};
  bool writing_{false};
  bool stopping_{false};
};

int parse_int(const std::string& s, const char* what) {
  try {
    std::size_t used = 0;
    const int v = std::stoi(s, &used);
    if (used != s.size() || v < 0) throw std::invalid_argument(s);
    return v;
  } catch (const std::exception&) {
    throw std::runtime_error(std::string(what) + " negatif olmayan tam sayı olmalı: " + s);
  }
}

}  // namespace

int main(int argc, char** argv) {
  Options opt;
  try {
    opt.url = env_or("DELTA_SERVER_URL", "");
    opt.robot_yaml = env_or("DELTA_ROBOT_YAML", "config/robot.yaml");
    opt.edge_yaml = env_or("DELTA_EDGE_YAML", "edge/config/edge.yaml");
    opt.ca_file = env_or("DELTA_CA_FILE", "");
    opt.token = env_or("DELTA_EDGE_TOKEN", "");
    opt.driver = env_or("DELTA_DRIVER", "mock");
    opt.estop_file = env_or("DELTA_ESTOP_FILE", "");
    opt.insecure = env_or("DELTA_INSECURE", "0") == "1";
    opt.max_retries = parse_int(env_or("DELTA_MAX_RETRIES", "0"), "DELTA_MAX_RETRIES");
    for (int i = 1; i < argc; ++i) {
      const std::string a = argv[i];
      const auto next = [&]() -> std::string {
        if (i + 1 >= argc) throw std::runtime_error(a + " bir değer bekliyor");
        return argv[++i];
      };
      if (a == "-h" || a == "--help") {
        print_help();
        return 0;
      } else if (a == "--version") {
        std::cout << "delta_edge " DELTA_EDGE_VERSION " (protokol v" << delta_edge::kProtocolVersion
                  << ")\n";
        return 0;
      } else if (a == "--url") {
        opt.url = next();
      } else if (a == "--robot-config") {
        opt.robot_yaml = next();
      } else if (a == "--edge-config") {
        opt.edge_yaml = next();
      } else if (a == "--max-retries") {
        opt.max_retries = parse_int(next(), "--max-retries");
      } else {
        throw std::runtime_error("bilinmeyen seçenek: " + a + " (--help)");
      }
    }
  } catch (const std::exception& e) {
    log_line(std::string("hata: ") + e.what());
    return kExitUsage;
  }

  delta_edge::EdgeLimits limits;
  try {
    limits = delta_edge::load_limits(opt.robot_yaml, opt.edge_yaml);
  } catch (const std::exception& e) {
    log_line(std::string("yapılandırma hatası: ") + e.what());
    return kExitUsage;
  }

  if (opt.url.empty()) {
    log_line("hata: sunucu adresi yok (DELTA_SERVER_URL ya da --url, ör. wss://server:8443/edge)");
    return kExitUsage;
  }
  std::string url_error;
  const auto url = delta_edge::parse_server_url(opt.url, &url_error);
  if (!url) {
    log_line("hata: geçersiz sunucu adresi '" + opt.url + "': " + url_error);
    return kExitUsage;
  }

  std::unique_ptr<delta_edge::Driver> driver;
  if (opt.driver == "mock") {
    driver = std::make_unique<delta_edge::MockDriver>(mono_now);
  } else if (opt.driver == "ax12") {
    log_line("hata: DELTA_DRIVER=ax12 henüz yok (F5); şimdilik yalnız mock");
    return kExitUsage;
  } else {
    log_line("hata: bilinmeyen DELTA_DRIVER='" + opt.driver + "' (mock|ax12)");
    return kExitUsage;
  }
  FileEstop estop(opt.estop_file);

  App app(opt, *url, limits, *driver, estop);
  const std::string tls_error = app.configure_tls();
  if (!tls_error.empty()) {
    log_line("hata: " + tls_error);
    return kExitUsage;
  }
  log_line("başladı: sürücü=" + opt.driver + ", döngü " + std::to_string(limits.tick_hz) +
           " Hz, T_stop=" + std::to_string(limits.t_stop_ms) +
           " ms, T_off=" + std::to_string(limits.t_off_ms) + " ms");
  return app.run();
}
