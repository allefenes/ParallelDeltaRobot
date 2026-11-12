// POSIX seri hat: termios ham kip, özel kilit (flock + TIOCEXCL), poll ile zaman aşımı.
//
// Varsayılan aygıt /dev/ttyAMA0: Raspberry Pi'de GPIO14/15'e bağlı PL011 UART. 1 Mbps için mini
// UART (ttyS0) uygun değildir (hızı çekirdek saatine bağlı). Pi 3/4'te `dtoverlay=disable-bt`,
// seri konsol kapalı (`enable_uart=1`, cmdline.txt'de console=serial0 yok) olmalı. USB adaptör
// (ör. U2D2) kullanılırsa DELTA_SERIAL_DEVICE=/dev/ttyUSB0. F5 kabul testinde doğrulanır.
#include "delta_edge/posix_serial.hpp"

#include <fcntl.h>
#include <poll.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <termios.h>
#include <unistd.h>

#include <cerrno>
#include <cstring>
#include <stdexcept>

namespace delta_edge {
namespace {

struct BaudEntry {
  int baud;
  speed_t code;
};

constexpr BaudEntry kBauds[] = {{9600, B9600},       {19200, B19200},     {38400, B38400},
                                {57600, B57600},     {115200, B115200},   {230400, B230400},
                                {460800, B460800},   {500000, B500000},   {576000, B576000},
                                {921600, B921600},   {1000000, B1000000}, {1152000, B1152000},
                                {1500000, B1500000}, {2000000, B2000000}, {2500000, B2500000},
                                {3000000, B3000000}, {3500000, B3500000}, {4000000, B4000000}};

bool baud_code(int baud, speed_t* out) {
  for (const auto& e : kBauds) {
    if (e.baud == baud) {
      *out = e.code;
      return true;
    }
  }
  return false;
}

std::string sys_error(const std::string& what) { return what + ": " + std::strerror(errno); }

class PosixSerial : public SerialPort {
 public:
  explicit PosixSerial(int fd) : fd_(fd) {}
  ~PosixSerial() override {
    ::ioctl(fd_, TIOCNXCL);
    ::flock(fd_, LOCK_UN);
    ::close(fd_);
  }
  PosixSerial(const PosixSerial&) = delete;
  PosixSerial& operator=(const PosixSerial&) = delete;

  bool write(const std::uint8_t* data, std::size_t n) override {
    std::size_t done = 0;
    while (done < n) {
      const ssize_t w = ::write(fd_, data + done, n - done);
      if (w > 0) {
        done += static_cast<std::size_t>(w);
        continue;
      }
      if (w < 0 && errno == EINTR) continue;
      if (w < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
        pollfd p{fd_, POLLOUT, 0};
        if (::poll(&p, 1, kWriteTimeoutMs) > 0) continue;
      }
      return false;
    }
    // Baytlar hatta çıkmadan dönülmez: yarım dupleks hatta yanıt ancak bundan sonra gelir.
    while (::tcdrain(fd_) != 0) {
      if (errno != EINTR) return false;
    }
    return true;
  }

  std::size_t read(std::uint8_t* buf, std::size_t max, int timeout_ms) override {
    if (max == 0) return 0;
    pollfd p{fd_, POLLIN, 0};
    int r;
    do {
      r = ::poll(&p, 1, timeout_ms < 0 ? 0 : timeout_ms);
    } while (r < 0 && errno == EINTR);
    if (r <= 0 || !(p.revents & POLLIN)) return 0;
    const ssize_t n = ::read(fd_, buf, max);
    return n > 0 ? static_cast<std::size_t>(n) : 0;
  }

  void flush_input() override { ::tcflush(fd_, TCIFLUSH); }

 private:
  static constexpr int kWriteTimeoutMs = 100;
  int fd_;
};

}  // namespace

const char* default_serial_device() { return "/dev/ttyAMA0"; }

bool posix_baud_supported(int baud) {
  speed_t c;
  return baud_code(baud, &c);
}

std::unique_ptr<SerialPort> open_posix_serial(const PosixSerialOptions& opt) {
  const std::string dev = opt.device.empty() ? default_serial_device() : opt.device;
  speed_t speed;
  if (!baud_code(opt.baud, &speed))
    throw std::runtime_error("desteklenmeyen baud: " + std::to_string(opt.baud));
  const int fd = ::open(dev.c_str(), O_RDWR | O_NOCTTY | O_NONBLOCK | O_CLOEXEC);
  if (fd < 0) throw std::runtime_error(sys_error(dev + " açılamadı"));
  const auto fail = [&](const std::string& what) {
    const std::string msg = sys_error(dev + ": " + what);
    ::close(fd);
    throw std::runtime_error(msg);
  };
  // Tek sahip (G10): başka süreç portu tutuyorsa beklemeden reddet.
  if (::flock(fd, LOCK_EX | LOCK_NB) != 0) fail("kilitlenemedi (başka süreç kullanıyor)");
  termios tio{};
  if (::tcgetattr(fd, &tio) != 0) fail("seri aygıt değil");
  if (::ioctl(fd, TIOCEXCL) != 0) fail("TIOCEXCL başarısız");
  ::cfmakeraw(&tio);
  tio.c_cflag |= CLOCAL | CREAD;
  tio.c_cflag &= ~static_cast<tcflag_t>(CSTOPB | PARENB | CRTSCTS);
  tio.c_iflag &= ~static_cast<tcflag_t>(IXON | IXOFF | IXANY);
  tio.c_cc[VMIN] = 0;
  tio.c_cc[VTIME] = 0;
  if (::cfsetispeed(&tio, speed) != 0 || ::cfsetospeed(&tio, speed) != 0) fail("hız ayarlanamadı");
  if (::tcsetattr(fd, TCSANOW, &tio) != 0) fail("tcsetattr başarısız");
  ::tcflush(fd, TCIOFLUSH);
  return std::make_unique<PosixSerial>(fd);
}

}  // namespace delta_edge
