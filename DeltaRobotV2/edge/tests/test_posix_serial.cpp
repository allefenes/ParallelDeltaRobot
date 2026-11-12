// POSIX seri hat: sözde terminal (pty) üzerinde gerçek termios/flock yolu. Donanım gerekmez.
#include <fcntl.h>
#include <gtest/gtest.h>
#include <poll.h>
#include <stdlib.h>
#include <unistd.h>

#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <string>

#include "delta_edge/posix_serial.hpp"

namespace delta_edge {
namespace {

// pty ana ucu; yan uç (slave) yolu `path`.
struct Pty {
  int master{-1};
  std::string path;
  Pty() {
    master = ::posix_openpt(O_RDWR | O_NOCTTY);
    if (master < 0 || ::grantpt(master) != 0 || ::unlockpt(master) != 0)
      throw std::runtime_error("pty açılamadı");
    path = ::ptsname(master);
  }
  ~Pty() { ::close(master); }
  std::string read_master(int timeout_ms = 500) {
    std::string out;
    pollfd p{master, POLLIN, 0};
    while (::poll(&p, 1, timeout_ms) > 0) {
      char buf[64];
      const ssize_t n = ::read(master, buf, sizeof buf);
      if (n <= 0) break;
      out.append(buf, static_cast<std::size_t>(n));
      timeout_ms = 20;
    }
    return out;
  }
};

TEST(PosixSerial, G10_DeviceOpenedExclusively) {
  Pty pty;
  auto port = open_posix_serial({pty.path, 1000000});
  ASSERT_TRUE(port);
  // İkinci sahip (aynı ya da başka süreç) reddedilir: flock root'u da durdurur.
  EXPECT_THROW(open_posix_serial({pty.path, 1000000}), std::runtime_error);
  port.reset();
  // Kapatınca kilit bırakılır.
  EXPECT_NO_THROW(open_posix_serial({pty.path, 57600}));
}

TEST(PosixSerial, WriteReadAndTimeout) {
  Pty pty;
  auto port = open_posix_serial({pty.path, 1000000});
  const std::uint8_t ping[] = {0xFF, 0xFF, 0x01, 0x02, 0x01, 0xFB};
  ASSERT_TRUE(port->write(ping, sizeof ping));
  EXPECT_EQ(pty.read_master(), std::string(reinterpret_cast<const char*>(ping), sizeof ping));

  const std::uint8_t reply[] = {0xFF, 0xFF, 0x01, 0x02, 0x00, 0xFC};
  ASSERT_EQ(::write(pty.master, reply, sizeof reply), static_cast<ssize_t>(sizeof reply));
  std::uint8_t buf[16];
  std::size_t got = 0;
  while (got < sizeof reply) {
    const std::size_t n = port->read(buf + got, sizeof buf - got, 500);
    ASSERT_GT(n, 0u);
    got += n;
  }
  EXPECT_EQ(std::string(reinterpret_cast<char*>(buf), got),
            std::string(reinterpret_cast<const char*>(reply), sizeof reply));

  // Veri yok: süre kadar bekler ve 0 döner (ham kip: 0xFF ya da \n dönüştürülmez).
  const auto t0 = std::chrono::steady_clock::now();
  EXPECT_EQ(port->read(buf, sizeof buf, 30), 0u);
  EXPECT_GE(std::chrono::steady_clock::now() - t0, std::chrono::milliseconds(25));
  EXPECT_EQ(port->read(buf, 0, 30), 0u);
  EXPECT_EQ(port->read(buf, sizeof buf, -1), 0u);
}

TEST(PosixSerial, RawModeKeepsControlBytes) {
  Pty pty;
  auto port = open_posix_serial({pty.path, 1000000});
  const std::uint8_t bytes[] = {0x0D, 0x0A, 0x03, 0x11, 0x13, 0x7F, 0x00};
  ASSERT_EQ(::write(pty.master, bytes, sizeof bytes), static_cast<ssize_t>(sizeof bytes));
  std::uint8_t buf[16];
  std::size_t got = 0;
  for (int k = 0; k < 10 && got < sizeof bytes; ++k) got += port->read(buf + got, 16 - got, 100);
  ASSERT_EQ(got, sizeof bytes);
  for (std::size_t i = 0; i < sizeof bytes; ++i) EXPECT_EQ(buf[i], bytes[i]) << i;
}

TEST(PosixSerial, FlushInputDiscardsPendingBytes) {
  Pty pty;
  auto port = open_posix_serial({pty.path, 1000000});
  const std::uint8_t junk[] = {1, 2, 3};
  ASSERT_EQ(::write(pty.master, junk, sizeof junk), 3);
  ::usleep(20000);
  port->flush_input();
  std::uint8_t buf[8];
  EXPECT_EQ(port->read(buf, sizeof buf, 30), 0u);
}

TEST(PosixSerial, RejectsBadBaudMissingDeviceAndNonTty) {
  Pty pty;
  EXPECT_THROW(open_posix_serial({pty.path, 117647}), std::runtime_error);
  EXPECT_THROW(open_posix_serial({"/yok/aygit", 1000000}), std::runtime_error);
  const auto file = std::filesystem::temp_directory_path() / "delta_edge_not_a_tty";
  std::ofstream(file) << "x";
  try {
    open_posix_serial({file.string(), 1000000});
    FAIL() << "tty olmayan dosya kabul edildi";
  } catch (const std::runtime_error& e) {
    EXPECT_NE(std::string(e.what()).find("seri aygıt değil"), std::string::npos) << e.what();
  }
}

TEST(PosixSerial, DefaultsAndSupportedBauds) {
  EXPECT_STREQ(default_serial_device(), "/dev/ttyAMA0");
  for (int b : {9600, 57600, 115200, 500000, 1000000, 2000000, 4000000})
    EXPECT_TRUE(posix_baud_supported(b)) << b;
  for (int b : {0, 117647, 250000, 3000001}) EXPECT_FALSE(posix_baud_supported(b)) << b;
  // Boş aygıt varsayılana düşer; konteynerde o aygıt yoktur (Pi'de denetim atlanır).
  if (!std::filesystem::exists(default_serial_device())) {
    EXPECT_THROW(open_posix_serial({"", 1000000}), std::runtime_error);
  }
}

TEST(PosixSerial, WriteFailsAfterPeerHangup) {
  auto pty = std::make_unique<Pty>();
  auto port = open_posix_serial({pty->path, 1000000});
  pty.reset();  // ana uç kapandı: yazma hata verir (EIO)
  const std::uint8_t b[] = {0xFF};
  EXPECT_FALSE(port->write(b, 1));
  std::uint8_t buf[4];
  EXPECT_EQ(port->read(buf, sizeof buf, 10), 0u);
}

}  // namespace
}  // namespace delta_edge
