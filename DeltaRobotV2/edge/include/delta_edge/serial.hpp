// Bayt akışı soyutlaması (seri hat). Gerçek aygıtı yalnız posix_serial.cpp açar (G10);
// sürücü ve protokol katmanı yalnız bu arayüzü görür, testler FakeServoBus verir.
#pragma once

#include <cstddef>
#include <cstdint>

namespace delta_edge {

class SerialPort {
 public:
  virtual ~SerialPort() = default;
  // Tüm baytları yazar ve hatta çıkmalarını bekler (yarım dupleks: yanıt ancak sonra gelir).
  // Başarısızsa false.
  virtual bool write(const std::uint8_t* data, std::size_t n) = 0;
  // En çok `max` bayt okur; hiç bayt yoksa en çok `timeout_ms` bekler. 0 = zaman aşımı.
  virtual std::size_t read(std::uint8_t* buf, std::size_t max, int timeout_ms) = 0;
  // Alınmış ama okunmamış baytları atar (eski yanıt kırıntıları).
  virtual void flush_input() = 0;
};

}  // namespace delta_edge
