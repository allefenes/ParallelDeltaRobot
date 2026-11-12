# Yol haritası

Her faz bir sonrakine geçmeden önce proje sahibinin onayını alır. Fiziksel robot şu an yok (V1 robotu okula hibe edildi); F5'e kadar her şey dijital ikiz üzerinde çalışır. Mimari: beyin sunucuda, robot başında ince ama güvenli bir Raspberry Pi kenarı ([mimari.md](mimari.md)). Sanal Pi, gerçek Pi ile aynı kenar protokolünü konuştuğu için F5'te yalnız donanım katmanı değişir.

Bütün fazlarda [hardware/bom.md](../hardware/bom.md) (malzeme listesi) ve [kurulum-plani.md](kurulum-plani.md) güncel tutulur.

## F0 — İskele

- `DeltaRobotV2/` klasör yapısı, README ve belgeler
- Docker geliştirme imajı: Ubuntu 24.04, ROS2 Jazzy, CMake, GoogleTest, pytest
- `compose.yaml` iskeleti
- i18n iskeleti: `tr.json` kaynak, `en.json` çeviri, anahtar ve yer tutucu denetimi
- `tools/ci.sh`: yerelde ve CI'da aynı denetimler
- GitHub Actions iş akışı taslağı

## F0.5 — CAD

- Tüm parçalar FreeCAD Python betikleriyle, parametrik: POM taban, 7075 sütun ve tavan, PLA motor gövdesi ve kapakları, 3× AX-12A, 608ZZ rulmanlar ve artı kesitli miller, kısa kollar, dişi M5 rot başları, 30 mm aralıklı saplama çiftleri, konik burçlar, pimler, somunlar, R35 uç platform, elektromıknatıs
- Her hareketli parça ayrı gövde; koordinat sistemi gerçek eklem merkezinde ve ekseninde
- Malzeme yoğunluklarından kütle ve atalet
- Mesh dışa aktarımı (URDF, RViz/Gazebo, web ikizi için)
- Tanımlı bir pozda montaj ve kinematikle ölçü kontrolü (64 / 201 mm, R65, R35)
- Malzemeye göre renklendirme; izometrik, ön, yan, üst ve eklem yakın çekim görselleri
- **F1, görseller onaylanmadan başlamaz**

## F1 — Kinematik çekirdek

- `core/` altında C++ kütüphane: ileri/ters kinematik, Jacobian, çalışma alanı, limit kontrolü
- GoogleTest testleri; V1 Python koduyla sayısal çapraz doğrulama
- pybind11 ile Python bağlaması

## F2 — Datasheet

- Çalışma alanı, çözünürlük haritası, hız, kuvvet/yük, tekil noktalar, çevrim süresi
- Motor parametrelerine göre yeniden üretilebilir (motor değişirse tek komutla güncellenir)
- Her değerin kaynağı: hesap / simülasyon / ölçüm

## F3 — ROS2, kenar protokolü ve dijital ikiz (tamamlandı)

Sunucu:

- ROS2 yığını; 1. güvenlik kapısı (tam süpervizör: çalışma alanı, çarpışma, görev mantığı, hız/ivme profili)
- Yörünge planlama (zaman damgalı tam yörünge), durum makinesi
- Kenar köprüsü düğümü: ROS2 yörüngesi -> kenar protokolü, telemetri -> ROS2 konuları
- Dijital ikiz (URDF + CAD mesh, RViz); tabla, taşlar ve elektromıknatıs F4.5'te eklenir

Kenar (`edge/`, C++17, ROS'suz):

- Kenar protokolü tanımı ve sürümlemesi (WebSocket + TLS, Pi dışarı bağlanır)
- `delta_edge`: yörünge tamponu ve yerel saatle 50–100 Hz oynatma, 2. (son) güvenlik kapısı, bekçi (kalp atışı), telemetri
- Motordan bağımsız sürücü arayüzü; AX-12A arka ucu (Protocol 1.0) ve mock arka ucu
- Sanal Pi: `delta_edge` + mock/ikiz arka ucu bir konteynerde; sunucu gerçek robottan ayırt edemez
- Testler: kapı sınırları, bekçi senaryoları (hareket ortasında bağlantı kopması), yörünge zamanlaması

## F4 — Uzaktan erişim

- Komut API'si (token ile), `pip` ile kurulan Python istemcisi (VS Code'dan kullanım)
- Web: kod editörü, 3B ikiz, telemetri, TR arayüz
- Web editöründeki kod için sandbox (ağsız, kaynak sınırlı konteyner)
- Kamera akışının web'e bağlanması (WebRTC; F5'e kadar ikizden sanal görüntü)
- Sunucu dağıtımı (`compose.yaml`): web, API, ROS2 yığını, kenar uç noktası

## F4.5 — Tic-tac-toe

- Tabla modeli, hücre koordinatları, kalibrasyon
- Görev tanımı, başarı kontrolü, robotun kendi kendine sıfırlaması

## F5 — Yeniden kurulum

- Motor seçimi, havalandırmalı kutu, kamera, elektromıknatıs sürücüsü
- Raspberry Pi kurulumu: `delta_edge` servisi (systemd), TLS kimliği, dışarı bağlantı
- Fiziksel acil stop: güç yolunu keser ve Pi'ye bildirir (ağdan bağımsız)
- Kamera: Pi'den doğrudan WebRTC yayını
- Gerçek donanımla bekçi ve kapı testleri; datasheet'in ölçüm alanları

## F6 — Kiralama

- Hesaplar, saatlik rezervasyon, ödeme, izleme, otomatik toparlanma, görev döngüsü yönetimi
