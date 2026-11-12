// Kenar durum makinesi durumları. Geçişler edge.cpp'de; özet tablo README.md'de.
#pragma once

namespace delta_edge {

enum class State {
  kIdle,       // tork açık, tutma hedefinde bekliyor, yörünge kabul eder
  kRunning,    // yörünge oynatılıyor
  kHolding,    // dur-tut (hold komutu ya da kalp atışı T_stop); devam için torque on
  kFault,      // sağlık sınırı aşıldı (G9); konum tutulur, reset ile çıkılır
  kTorqueOff,  // tork ve mıknatıs kapalı (açılış, T_off, torque off)
  kEstop,      // acil stop girişi; mandallı: giriş bırakılıp reset gelene kadar
};

const char* state_name(State s);

// Servolara hedef gönderilen (tork açık) durumlar.
bool torque_enabled(State s);

}  // namespace delta_edge
