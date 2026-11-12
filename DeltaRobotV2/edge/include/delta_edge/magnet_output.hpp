// Elektromıknatıs çıkışı. Gerçek Pi: GPIO + MOSFET (F5). Şimdilik iki gerçekleme:
//   NullMagnetOutput  hiçbir şey sürmez, yalnız son değeri tutar (varsayılan)
//   FileMagnetOutput  her değişimde dosyaya "1" / "0" yazar; ör. sysfs GPIO değer dosyası
//                     ya da sanal Pi'de dış gözlem için sıradan bir dosya
// Güvenli durum KAPALI (G7): yazma başarısız olursa çağıran bunu bilemez; bu yüzden GPIO
// donanımında çekme direnci mıknatısı kapalı tutmalıdır (F5 donanım notu).
#pragma once

#include <string>
#include <utility>

namespace delta_edge {

class MagnetOutput {
 public:
  virtual ~MagnetOutput() = default;
  virtual void set(bool on) = 0;
};

class NullMagnetOutput : public MagnetOutput {
 public:
  void set(bool on) override { on_ = on; }
  bool on() const { return on_; }

 private:
  bool on_{false};
};

class FileMagnetOutput : public MagnetOutput {
 public:
  explicit FileMagnetOutput(std::string path) : path_(std::move(path)) {}
  void set(bool on) override;
  bool last_write_ok() const { return ok_; }

 private:
  std::string path_;
  bool ok_{true};
};

}  // namespace delta_edge
