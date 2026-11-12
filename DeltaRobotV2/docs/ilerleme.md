# İlerleme

Faz ilerlemesi sayılabilir birimlerle tutulur; her çalışma adımında güncellenir.

Son güncelleme: 2026-11-12

## Özet

| Faz                         | Durum                                                          | Sayaç                                                                                                                                                                    |
| --------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| F0 İskele                   | Tamamlandı                                                     | 6 / 6 teslim                                                                                                                                                             |
| F0.5 CAD                    | Tamamlandı (revizyon 6 onaylandı, `95358ba`)                   | 20 / 20 parça çizildi, 123 / 123 bileşen montajlandı                                                                                                                     |
| F1 Kinematik                | Tamamlandı                                                     | 8 / 8 teslim; 532 test geçti; 4 / 12 güvenlik gereksinimi kanıtlandı (çekirdek)                                                                                          |
| F2 Datasheet                | Tamamlandı                                                     | 1 / 1 etkileşimli HTML; 6 grafik, 10 bölüm; 25 / 25 test                                                                                                                 |
| F3 ROS2 + kenar + uçtan uca | Tamamlandı                                                     | Kenar 111 / 111; ROS 79 birim + 3 launch; uçtan uca 16 / 16; mutasyon 130 / 131; fuzz ~175 bin girdi, bulgu yok; 10 / 13 gereksinim tüm yazılım katmanlarında kanıtlandı |
| F4 Uzaktan erişim           | Kod tamam; uçtan uca koşu Docker yeniden başlatmasını bekliyor | API 45, istemci 99, web 16, sandbox birim 81, G11 55 / 59 (düzeltme sonrası yeniden koşu bekliyor), ROS 97 + 3; G14 eklendi                                              |
| F4.5 Tic-tac-toe (sim)      | Kod tamam; gerçek yığında senaryo koşusu bekliyor              | Tabla ikizi + kurallar 15 test; API üzerinden tam oyun regresyonu ✔                                                                                                     |
| Malzeme listesi             | Her fazda güncellenir                                          | 32 kalem (G13 donanım bekçisi dahil), [hardware/bom.md](../hardware/bom.md)                                                                                              |

Sıradaki: Docker Desktop yeniden başlatılınca G11 yeniden koşusu ve F4/F4.5 uçtan uca koşusu; ardından F5 yazılım yarısı (tahmin ~3–4 saat) ve askıya alma, F6 simülasyon kiralama sitesi (tahmin ~10–14 saat). Son güncelleme: 2026-11-12, F4/F4.5 kodu tamam.

## F0 İskele

| Teslim                                                   | Durum |
| -------------------------------------------------------- | ----- |
| Klasör yapısı ve belgeler                                | ✔    |
| Docker geliştirme imajı (ROS2 Jazzy)                     | ✔    |
| Compose iskeleti                                         | ✔    |
| i18n iskeleti + denetim (5 test)                         | ✔    |
| C++ çekirdek iskeleti (1 test)                           | ✔    |
| CI (GitHub Actions, kökte) + biçim denetimi + pre-commit | ✔    |

## F0.5 CAD

### Adımlar

| Adım                                                      | Sayaç                                         |
| --------------------------------------------------------- | --------------------------------------------- |
| Parça çizildi                                             | 20 / 20                                       |
| Ölçü doğrulandı (kinematik: R65 / 64 / 201 / R35 / 30 mm) | 20 / 20                                       |
| Montajlandı (bileşen)                                     | 123 / 123                                     |
| Çakışma kontrolü (2 poz: montaj, 1. kol −69.6°)           | 2 / 2 temiz                                   |
| Radyus (7 parça grubu)                                    | 7 / 7 uygulandı (platformda 24 kenarın 12'si) |
| Renklendirildi                                            | 123 / 123                                     |
| Mesh + kütle/atalet dışa aktarıldı (simülasyon bağı)      | 11 / 11                                       |
| Montaj görseli                                            | 11 / 11                                       |
| Parça önizleme görseli (20 parça, 9 görselde)             | 9 / 9                                         |
| Kullanıcı onayı                                           | 1 / 1                                         |

### Parça listesi (20 benzersiz, 123 adet)

| #   | Parça                      | Adet | Ana ölçüler                                                                                                                                                          | Varsayım           | Önizleme                                                |
| --- | -------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ------------------------------------------------------- |
| 1   | POM taban                  | 1    | 5 mm; R160 yuvarlak uç + 320 mm genişlik; köşeler R20                                                                                                                | Dış ölçüler        | [01](img/cad/parcalar/01_pom_taban.png)                 |
| 2   | Sütun (D kesit)            | 1    | 7075, 5 mm; yarım silindir R50 + düz kapak levhası, 267 mm                                                                                                           | Yarıçap, konum     | [02](img/cad/parcalar/02_sutun_tavan.png)               |
| 3   | Tavan                      | 1    | 7075, 5 mm; robot ucu R45, boyun 70 mm (geçişler R8), sütun ucu R50; 3 delik Ø5.5 / R18                                                                              | Ölçüler            | [02](img/cad/parcalar/02_sutun_tavan.png)               |
| 4   | Motor gövdesi (tek parça)  | 1    | PLA; R85.2 × 5 mm üst plaka (rulman yatağı dış köşesi + 1 mm), 3 × 3 mm kol açıklığı, 3 motor kutusu (2.5 mm et, altı açık, kenarlar R2), 6 rulman yatağı üst yarısı | Pay, kutular       | [03](img/cad/parcalar/03_motor_govdesi.png)             |
| 5   | Rulman yatağı alt kapağı   | 6    | PLA; 32 × 10 × 13 mm; alttan takılır                                                                                                                                 | Ölçüler            | [04](img/cad/parcalar/04_rulman_kapagi_vida_insert.png) |
| 6   | Kapak vidası               | 12   | M3 × 21 mm, alttan, başı aşağıda                                                                                                                                     | Ölçü, diş/insert   | [04](img/cad/parcalar/04_rulman_kapagi_vida_insert.png) |
| 6b  | Isıyla gömülen insert      | 12   | M3 pirinç, Ø4.6 × 5.7 mm; yatak üst yarılarında                                                                                                                      | Ölçü               | [04](img/cad/parcalar/04_rulman_kapagi_vida_insert.png) |
| 7   | AX-12A                     | 3    | 32 × 50 × 40 mm zarf, göbek Ø20                                                                                                                                      | Göbek konumu       | [05](img/cad/parcalar/05_motor_rulman_mil.png)          |
| 8   | 608ZZ rulman               | 6    | 8 × 22 × 7 mm                                                                                                                                                        | —                  | [05](img/cad/parcalar/05_motor_rulman_mil.png)          |
| 9   | Çıkış mili                 | 3    | PLA %100; tüm boyu artı kesit (uçlar Ø8 dairede, kol 3 mm, iç köşeler R0.5), Ø16 flanş                                                                               | Kol genişliği      | [05](img/cad/parcalar/05_motor_rulman_mil.png)          |
| 10  | Kısa kol                   | 3    | 7075, 2 mm; merkezden merkeze 64; R14 → Ø10; artı delik iç köşeleri R0.8                                                                                             | Dış hat            | [06](img/cad/parcalar/06_kisa_kol.png)                  |
| 11  | Pim                        | 6    | M5 × 58 mm                                                                                                                                                           | —                  | [07](img/cad/parcalar/07_eklem_pim_burc_somun_kure.png) |
| 12  | İç burç (konik)            | 12   | Ø9 → Ø6.5; kısa kol tarafı 10 mm, platform tarafı 5 mm                                                                                                               | Malzeme, çaplar    | [07](img/cad/parcalar/07_eklem_pim_burc_somun_kure.png) |
| 13  | Dış burç (konik)           | 12   | Ø6.5 → Ø9, 5 mm                                                                                                                                                      | Malzeme, çaplar    | [07](img/cad/parcalar/07_eklem_pim_burc_somun_kure.png) |
| 14  | M5 fiber somun             | 12   | AA 8, 5 mm                                                                                                                                                           | —                  | [07](img/cad/parcalar/07_eklem_pim_burc_somun_kure.png) |
| 15  | Rot başı küresi            | 12   | Ø11.11 × 8 mm                                                                                                                                                        | Katalog            | [07](img/cad/parcalar/07_eklem_pim_burc_somun_kure.png) |
| 16  | Rot başı gövdesi (dişi M5) | 12   | Ø18 × 6 mm baş, Ø9 şaft, merkezden uca 27 mm                                                                                                                         | Katalog            | [08](img/cad/parcalar/08_uzun_kol_rot_basi.png)         |
| 17  | M5 saplama                 | 6    | 167 mm                                                                                                                                                               | —                  | [08](img/cad/parcalar/08_uzun_kol_rot_basi.png)         |
| 18  | Uç platform                | 1    | PLA %20; dairesel R28 × 5 mm; kulak eksenleri r = 35 (kulaklar taşar, kökler R1.5); 3 süs deliği Ø8; mıknatıs cebi 2.5 mm                                            | Disk yarıçapı, cep | [09](img/cad/parcalar/09_platform_miknatis.png)         |
| 19  | Elektromıknatıs            | 1    | Ø20 × 15 mm; P'den uca 15.0 mm                                                                                                                                       | Çap, kütle         | [09](img/cad/parcalar/09_platform_miknatis.png)         |

### Montaj görselleri

[iso](img/cad/iso.png), [ön](img/cad/on.png), [yan](img/cad/yan.png), [üst](img/cad/ust.png), [mekanizma](img/cad/mekanizma.png), [eklem](img/cad/eklem.png), [motor kutuları (alttan)](img/cad/motor_kutulari_alttan.png), [motor kutusu (yakın)](img/cad/motor_kutusu_yakin.png), [1. kol yukarıda (önden)](img/cad/kol1_yukari.png), [1. kol yukarıda (iso)](img/cad/kol1_yukari_iso.png), [1. kol yukarıda (yakın)](img/cad/kol1_yukari_yakin.png)

### Kullanıcı düzeltmeleri (revizyon 2 + 3)

| #   | Düzeltme                                                                                                                                | Durum |
| --- | --------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| 1   | Sütunun açık yüzü kapalı (D kesit)                                                                                                      | ✔    |
| 2   | Üst plakada dikdörtgen kol açıklıkları; 1. kol −69.6°'ye çakışmasız çıkıyor                                                             | ✔    |
| 3   | P'den mıknatıs ucuna 15 mm (sabit kısıt)                                                                                                | ✔    |
| 4   | Tavanın robot tarafı küçük (R100 → R45)                                                                                                 | ✔    |
| 5   | Bağlantı delikleri merkeze yakın (R18), tavan ve üst plakada                                                                            | ✔    |
| 6   | Üst plaka boyutu: rulman yataklarını taşıyan en küçük yarıçap R85.2 (yatak köşesi R84.2 + 1 mm); motor kutuları plakadan ~10 mm taşıyor | ✔    |
| 7   | Platformda 3 süs deliği (Ø8, kulaklar arasında)                                                                                         | ✔    |
| 8   | Motorlar kendi kutularında; gövde tek parça; yataklar ve 2 vidalı kapaklar                                                              | ✔    |
| 9   | Radyuslar (7 parça grubu; ayrıntı `cad/out/checks.md`)                                                                                  | ✔    |
| 10  | Eklem sırası somun-burç-mafsal-burç-kol-…; burçlar boydan boya konik; aralık 30 mm korundu                                              | ✔    |
| 11  | Çıkış mili tüm boyu artı kesit                                                                                                          | ✔    |
| 12  | Üst plakada 3 mm kol açıklıkları; rulman yatakları plakaya bağlı                                                                        | ✔    |
| 13  | Platform dairesel (R28, kulaklar taşar)                                                                                                 | ✔    |
| 14  | Üst plaka en küçük yarıçapta (6. madde)                                                                                                 | ✔    |
| 15  | Rulman yatağının üst yarısı plakayla tek parça; alt kapak ve vidalar alttan                                                             | ✔    |
| 16  | Yatak üst yarılarında M3 ısıyla gömülen insertler; BOM ve kurulum planına eklendi                                                       | ✔    |

## F1 Kinematik çekirdek

| Teslim                                                           | Durum |
| ---------------------------------------------------------------- | ----- |
| İleri / ters kinematik (C++17)                                   | ✔    |
| Jacobian, koşul sayısı, rot başı açısı                           | ✔    |
| Limit kontrolü (motor −70…+150°, rot başı 13°, NaN/sonsuz reddi) | ✔    |
| `config/robot.yaml` okuyucu                                      | ✔    |
| Python bağlaması (`delta_core_py`)                               | ✔    |
| Özellik tabanlı testler (Hypothesis)                             | ✔    |
| V1 çapraz doğrulaması (346 IK + 140 FK vaka)                     | ✔    |
| Kapsama ölçümü ve CI artefaktı                                   | ✔    |

### Test özeti

| Bileşen                              | Test (geçen / toplam) | Satır % | Dal % | Not                                   |
| ------------------------------------ | --------------------- | ------- | ----- | ------------------------------------- |
| delta_core (C++, GoogleTest)         | 22 / 22               | 100.0   | 69.4  | gcovr                                 |
| delta_core (Python, Hypothesis + V1) | 495 / 495             | —       | —     | Özellik testleri ~2000 rastgele örnek |
| Araçlar (bom, i18n)                  | 15 / 15               | 97.4    | —     | pytest-cov                            |
| **Toplam**                           | **532 / 532**         |         |       | Genel taban %80 sağlandı              |

- Güvenlik gereksinimleri: **4 / 12 gereksinim testle kanıtlandı** (G1–G4, çekirdek katmanı) — [guvenlik-gereksinimleri.md](guvenlik-gereksinimleri.md)
- Mutasyon testi: kritik modüller (sunucu kapısı, Pi kapısı, bekçi) F3'te yazılınca uygulanacak.
- Hypothesis bulgusu: θ ≈ 90° (kol düşey) bölgesinde sistem tekile yakın; FK → IK sayısal hassasiyeti düşüyor (0.05°). Özellik testi tekil olmayan bölgeyle sınırlandı; datasheet bu bölgeyi gösterecek.
- Varsayım: rot başı yanal açı limiti 13° (V1: 14°), modellenen rot başının katalog sınırı.

## F2 Datasheet

[docs/datasheet/datasheet.html](datasheet/datasheet.html) — tek dosya, etkileşimli (Plotly, Mermaid; sabit sürümlü CDN). `tools/datasheet/build_datasheet.py` ile robot.yaml, çekirdek kinematik, CAD kütleleri ve BOM'dan üretilir; motor parametreleri değişince yeniden üretilir.

| Bölüm                                                               | İçerik                                                                                                                    | Durum   |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------- |
| Özet                                                                | 14 temel değer, etiketli (H/S/K/V/Ö)                                                                                      | ✔      |
| Çalışma alanı                                                       | 3B nokta bulutu, XY dilimleri (z kaydırıcılı), XZ/YZ kesitleri (V1 tarzı), r(z) ve kullanılabilir silindir, ret nedenleri | ✔      |
| Performans haritaları                                               | Çözünürlük, garanti hız, garanti kuvvet, koşul sayısı; 2 yükseklik                                                        | ✔      |
| Görev (tabla)                                                       | Taş alma yüksekliğinde erişim ve en büyük 3×3 tabla                                                                       | ✔      |
| Geometri ve limitler, motor ve elektrik, kütle ve atalet, BOM özeti | Tablolar                                                                                                                  | ✔      |
| Yazılım / ROS2 ağı                                                  | İskelet (planlanan mimari); F3'te çalışan sistemden üretilecek                                                            | İskelet |
| Varsayımlar                                                         | robot.yaml'daki tüm "varsayim" değerleri                                                                                  | ✔      |

Öne çıkan değerler (hesap): çalışma alanı 871 cm³; kullanılabilir silindir Ø82 × 110 mm; tabla yüksekliğinde en büyük kare 60 mm (hücre 20 mm); merkezde tek adım çözünürlüğü ~0.5 mm, en kötü durum ~1 mm; garanti hız ~253 mm/s; garanti kuvvet ~3.9 N; düşey taşıma ~1.5 kg.

**Bulgu:** Çalışma alanını çoğunlukla rot başının yanal açı sınırı (13°) belirliyor; tic-tac-toe tablası bu yüzden küçük (60 mm). Gerçek rot başı modeli bilinince yeniden hesaplanır.

### F2 test özeti

| Bileşen                                | Test (geçen / toplam) | Satır % |
| -------------------------------------- | --------------------- | ------- |
| Datasheet hesapları + üretici          | 10 / 10               | 96–99   |
| Araçlar toplamı (bom, i18n, datasheet) | 25 / 25               | 97.5    |

## F3 ROS2, Pi kenarı, uçtan uca sistem

Bilgisayarın gece yeniden başlamasından sonra diskteki iş denetlendi: hiçbir şey kaybolmadı; 2 derleme hatası ve 2 hatalı test düzeltilip `0616a7d` olarak kaydedildi.

| Teslim                                                                                                                            | Durum                          |
| --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| Pi kenar servisi `delta_edge` (C++17, ROS'suz): protokol v1, son kapı, oynatıcı, bekçi, durum makinesi, MockDriver, TLS istemcisi | ✔                             |
| G13 donanım bekçisi için yaşam darbesi (döngü her tick'te çıkışı ters çevirir; sanal Pi'de dosyaya, F5'te GPIO'ya)                | ✔                             |
| AX-12A sürücü arka ucu                                                                                                            | İskelet; F5'te gerçek servoyla |
| Sanal Pi konteyneri (`docker/edge`, gerçek Pi ile aynı ikili)                                                                     | ✔                             |
| ROS2 paketleri: `delta_interfaces`, `delta_description` (CAD mesh'li URDF), `delta_server`                                        | ✔                             |
| Sunucu düğümleri: planlayıcı, 1. kapı süpervizörü, durum yayıncısı, `edge_bridge` (TLS WebSocket, Pi bağlanır)                    | ✔                             |
| Compose `sim` profili: yerel TLS sertifikası (adlandırılmış birim), sunucu, sanal Pi                                              | ✔                             |
| Uçtan uca test + hata enjeksiyonu (`tools/e2e.sh`)                                                                                | 16 / 16                        |
| RViz ekran görüntüleri (başsız, CAD mesh'leri)                                                                                    | 4 / 4                          |
| ROS ağı diyagramı (çalışan Compose sisteminden: 5 düğüm, 9 konu, 4 servis)                                                        | ✔                             |
| Datasheet "Yazılım mimarisi / ROS2 ağı" bölümü (gerçek diyagram + arayüz tablosu)                                                 | ✔                             |
| Fuzz (protokol ayrıştırıcı) ve mutasyon testi (kapı, bekçi, protokol)                                                             | ✔                             |
| CI: kenar testleri + kapsama `tools/ci.sh`'ta; ROS testleri `tools/ros_test.sh` ile ayrı adım                                     | ✔                             |

### F3 test özeti

| Bileşen                                | Test (geçen / toplam) | Satır % | Not                                                                  |
| -------------------------------------- | --------------------- | ------- | -------------------------------------------------------------------- |
| delta_edge (GoogleTest)                | 111 / 111             | 99.0    | Test adları gereksinim numarasıyla; dal %63                          |
| delta_server + description (pytest)    | 79 / 79               | 93      | kenar protokolü testleri dahil                                       |
| launch_testing (ROS yığını)            | 3 / 3                 | —       | geçerli hareket; G2 reddi                                            |
| Uçtan uca (Compose)                    | 16 / 16               | —       | HOLD 200 ms, TORQUE_OFF 1023 ms (T_stop 200, T_off 1000)             |
| Mutasyon testi (kapı, bekçi, protokol) | 130 / 131 öldürüldü   | —       | %99.2; kalan 1 mutant eşdeğer                                        |
| Fuzz (libFuzzer + ASan/UBSan)          | ~175 bin girdi        | —       | çökme / tanımsız davranış yok; 24 tohumluk derlem regresyon testinde |

Uçtan uca senaryolar: TLS bağlantısı; yörünge yürütme; 1. kapı reddi (G1/G2); 1. kapıyı atlayan limit dışı yörüngede son kapı reddi (G1/G8); hareket ortasında kalp atışı kaybı → HOLD, TORQUE_OFF (G6/G7); 80±40 ms gecikme + %10 paket kaybında yürütme; bağlantı kara deliği ve açık kurtarma; sunucu çökmesi (kenar kendi başına HOLD → TORQUE_OFF); Pi çökmesi (SIGKILL) sonrası güvenli açılış; düzgün kapanış (SIGTERM) tork + mıknatıs kapatır.

**Bulgu ve karar:** Pi çökerse (SIGKILL / donma / elektrik kesintisi) yazılım torku kapatamaz; gerçek servolar son hedefte torklu kalır. Karar: G13 donanım bekçisi; yaşam darbesi kesilince 74HC123 monostable servo gücünü ≤ 0.5 s (varsayım) içinde keser. Mimari, BOM (47–49), kurulum planı ve kabul testi H13 güncellendi.

**Güvenlik gereksinimleri:** 10 / 13 tüm yazılım katmanlarında kanıtlandı (G1–G10); G13'ün yazılım tarafı kanıtlandı, donanım tarafı F5'te; G11 (sandbox) F4'te; G12 (acil stop) F5'te. Ayrıntı: [guvenlik-gereksinimleri.md](guvenlik-gereksinimleri.md).

## F4 Uzaktan erişim

Sözleşme: [api.md](api.md). Bilgisayarın ikinci çökmesinden (11:07) sonra diskteki iş denetlendi: kayıp yok; 14 dosyadaki CRLF satır sonları LF'ye çevrildi, `6324f1d` ara kayıt.

| Teslim                                                                                                          | Durum                                                        |
| --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Komut API'si (`api/`, FastAPI): REST + WebSocket, belirteç, kontrol kilidi, iş kuyruğu; ROS2 ve sahte arka uç   | ✔                                                           |
| Python istemcisi (`client/`, pip paketi `delta-robot-client`): HTTPS + sandbox stdio taşıması                   | ✔                                                           |
| Web arayüzü (`web/`, Türkçe): kod editörü, 3B ikiz (CAD mesh'leri), telemetri, elle sürme, DUR                  | ✔                                                           |
| Sandbox (`sandbox/`): koşucu + ağsız, salt okunur, kaynak sınırlı kullanıcı kodu konteyneri                     | ✔                                                           |
| Compose `sim` profili: api (server ağ ad alanında, https://localhost:8000) + runner; ROS keşfi yalnız localhost | ✔                                                           |
| Kenar telemetrisinde mıknatıs durumu; edge_bridge magnet/stop servisleri                                        | ✔                                                           |
| Uçtan uca test (`tools/e2e_f4.sh`, gerçek istemciyle 18 senaryo + F4.5 oyunu)                                   | Docker yeniden başlatmasını bekliyor                         |
| Kamera (WebRTC)                                                                                                 | F5'e ertelendi; web'de "Kamera F5'te; şimdilik dijital ikiz" |

### F4 test özeti

| Bileşen                                          | Test (geçen / toplam)         | Satır % | Not                                                                |
| ------------------------------------------------ | ----------------------------- | ------- | ------------------------------------------------------------------ |
| API (pytest, sahte arka uç + sahte koşucu)       | 45 / 45                       | 93      | Kimlik, kilit, iş akışı, tabla, tam oyun regresyonu                |
| Python istemcisi                                 | 99 / 99                       | 100     | Python 3.10 (en düşük sürümler) ve 3.12                            |
| Web (JS çalıştırmadan denetimler + sahte sunucu) | 16 / 16                       | —       | Tarayıcıda elle doğrulandı (1280 px ve 375 px)                     |
| Sandbox birim                                    | 81 / 81                       | —       | Docker'sız; G11 tıkanma regresyonu dahil                           |
| Sandbox G11 (gerçek konteyner)                   | 55 / 59 (+14 temizlik hatası) | —       | Hatalar aşağıdaki bulgudan; düzeltme sonrası yeniden koşu bekliyor |
| ROS2 (pytest + launch_testing)                   | 97 + 3                        | —       | G14 ve tabla ikizi dahil                                           |
| Kenar (C++)                                      | 112 / 112                     | 99.0    | Telemetride mıknatıs                                               |

**G11 bulgusu (düzeltildi):** RPC seli testinde kullanıcı kodu stdin'i okumayınca koşucunun stdout okuyucusu yanıt yazarken bekledi; docker istemcisi ve Docker daemon'ının akış kopyası tıkandı, konteyner `kill`/`rm -f` ile bile silinemez kaldı (`deltarobotv2-job-job-g11-f811554d`; Docker Desktop yeniden başlatılınca temizlenecek). Düzeltme: stdin'e bloklamadan yazma (256 KB sınır), bekleyen istek sınırını aşan sel işi durdurur, durdurmada stdin kapanır + SIGKILL + `rm -f`. Docker'sız regresyon testi eski kodda takılıyor, yenide 1 s'de geçiyor.

**G14 (yeni gereksinim):** API sözleşmesi yazılırken bulundu: çalışma alanının kinematik alt sınırı mıknatıs ucunu zemine indirebiliyordu ve 1. kapıda zemin denetimi yoktu. Süpervizöre eklendi (3 test); API çalışma alanını P ≥ −221 mm olarak bildirir.

## F4.5 Tic-tac-toe (simülasyon)

| Teslim                                                                                                                       | Durum                               |
| ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| Tabla tasarımı: 3 × 3, hücre 20 mm (F2'deki 60 mm kare), taş Ø16 × 8 mm; `robot.yaml task.board`                             | ✔                                  |
| Oyun: kaydırmalı tic-tac-toe (Üç Taş ailesi). Çalışma alanı tablayı doldurduğu için taş deposu yok; taşlar baştan tabladadır | ✔                                  |
| Taş ikizi (`board_game.py`, `board_twin` düğümü): mıknatısla al/bırak, yerleştirme hatası, düşürme, kaçırma metrikleri       | ✔                                  |
| API `GET /board`, `POST /board/reset`; istemci `board()`, `reset_board()`, `cell_xy()`, `pick_place()`                       | ✔                                  |
| Web ikizinde tabla ve taşlar, tabla durumu, sıfırlama düğmesi                                                                | ✔                                  |
| Senaryo regresyonu: iki minimaks oyuncu; API üzerinden (sahte arka uç) ✔, gerçek yığında `tools/e2e_f4.sh`                  | kısmen                              |
| Datasheet "Senaryo metrikleri (simülasyon)" bölümü                                                                           | ✔ (veri uçtan uca koşudan gelecek) |

## Kullanıcıdan beklenen kararlar

| Konu                                                                | Neden gerekli                                              | Şimdilik                        |
| ------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------- |
| Docker Desktop yeniden başlatması                                   | Takılı G11 konteyneri; G11 ve uçtan uca koşular buna bağlı | Kök oturum kullanıcıya soruyor  |
| Fiyatlandırma (F6)                                                  | Simülasyon kiralama planları                               | Öneri belgede; yer tutucular    |
| Ödeme sağlayıcısı (F6): iyzico ya da PayTR                          | Stripe Türk satıcı kabul etmiyor                           | Soyutlama + test modu           |
| Alan adı ve sunucu (F6)                                             | Gerçek dağıtım                                             | Yalnız yerel konteyner          |
| Hukuki metinler (F6): Kullanım Koşulları, KVKK aydınlatma, Gizlilik | Hukuk incelemesi                                           | "Taslak" işaretli yer tutucular |
