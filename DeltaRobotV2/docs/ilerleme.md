# İlerleme

Faz ilerlemesi sayılabilir birimlerle tutulur; her çalışma adımında güncellenir.

Son güncelleme: 2026-11-12

## Özet

| Faz          | Durum                                                      | Sayaç                                                |
| ------------ | ---------------------------------------------------------- | ---------------------------------------------------- |
| F0 İskele    | Tamamlandı                                                 | 6 / 6 teslim                                         |
| F0.5 CAD     | Revizyon 2 tamamlandı, **montaj görselleri onay bekliyor** | 19 / 19 parça çizildi, 102 / 102 bileşen montajlandı |
| F1 Kinematik | Başlamadı (F0.5 onayı bekleniyor)                          | —                                                    |

Kalan süre (F0.5): onay gelirse 0; düzeltme istenirse tur başına ~1 saat.

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

| Adım                                                      | Sayaç       |
| --------------------------------------------------------- | ----------- |
| Parça çizildi                                             | 19 / 19     |
| Ölçü doğrulandı (kinematik: R65 / 64 / 201 / R35 / 30 mm) | 19 / 19     |
| Montajlandı (bileşen)                                     | 102 / 102   |
| Çakışma kontrolü (2 poz: montaj, 1. kol −69.6°)           | 2 / 2 temiz |
| Renklendirildi                                            | 102 / 102   |
| Mesh + kütle/atalet dışa aktarıldı (simülasyon bağı)      | 11 / 11     |
| Montaj görseli                                            | 9 / 9       |
| Parça önizleme görseli (19 parça, 9 görselde)             | 9 / 9       |
| Kullanıcı onayı                                           | 0 / 1       |

### Parça listesi (19 benzersiz, 102 adet)

| #   | Parça                      | Adet | Ana ölçüler                                                                             | Varsayım       | Önizleme                                                |
| --- | -------------------------- | ---- | --------------------------------------------------------------------------------------- | -------------- | ------------------------------------------------------- |
| 1   | POM taban                  | 1    | 5 mm; R160 yuvarlak uç + 320 mm genişlik                                                | Dış ölçüler    | [01](img/cad/parcalar/01_pom_taban.png)                 |
| 2   | Sütun (D kesit)            | 1    | 7075, 5 mm; yarım silindir R50 + düz kapak levhası, 267 mm                              | Yarıçap, konum | [02](img/cad/parcalar/02_sutun_tavan.png)               |
| 3   | Tavan                      | 1    | 7075, 5 mm; robot tarafı R45, boyun 70 mm, sütun ucu R50; 3 delik Ø5.5 / R18            | Ölçüler        | [02](img/cad/parcalar/02_sutun_tavan.png)               |
| 4   | Motor gövdesi üst plakası  | 1    | PLA, R90 × 5 mm; 3 dikdörtgen kol açıklığı 52 × 48 mm; 3 delik R18                      | Ölçüler        | [03](img/cad/parcalar/03_motor_govdesi_ust_plaka.png)   |
| 5   | Motor pedi                 | 3    | PLA, 42 × 24 × 2 mm                                                                     | Tümü           | [03](img/cad/parcalar/03_motor_govdesi_ust_plaka.png)   |
| 6   | Rulman yatağı (alt + askı) | 6    | PLA; 30 × 10 mm, Ø22 yuva, iç askı duvarı                                               | Tümü           | [04](img/cad/parcalar/04_rulman_yatagi_kapak.png)       |
| 7   | Rulman kapağı              | 6    | PLA; 30 × 10 × 13 mm                                                                    | Tümü           | [04](img/cad/parcalar/04_rulman_yatagi_kapak.png)       |
| 8   | AX-12A                     | 3    | 32 × 50 × 40 mm zarf, göbek Ø20                                                         | Göbek konumu   | [05](img/cad/parcalar/05_motor_rulman_mil.png)          |
| 9   | 608ZZ rulman               | 6    | 8 × 22 × 7 mm                                                                           | —              | [05](img/cad/parcalar/05_motor_rulman_mil.png)          |
| 10  | Artı kesitli çıkış mili    | 3    | PLA %100; Ø8 yatak boyunları, 8 × 3 mm artı kesit                                       | Ölçüler        | [05](img/cad/parcalar/05_motor_rulman_mil.png)          |
| 11  | Kısa kol                   | 3    | 7075, 2 mm; merkezden merkeze 64; R14 → Ø10                                             | Dış hat        | [06](img/cad/parcalar/06_kisa_kol.png)                  |
| 12  | Pim                        | 6    | M5 × 48 mm                                                                              | —              | [07](img/cad/parcalar/07_eklem_pim_burc_somun_kure.png) |
| 13  | Burç                       | 18   | Ø9 × 5 mm, Ø5 delik, konik uç                                                           | Malzeme, koni  | [07](img/cad/parcalar/07_eklem_pim_burc_somun_kure.png) |
| 14  | M5 fiber somun             | 12   | AA 8, 5 mm                                                                              | —              | [07](img/cad/parcalar/07_eklem_pim_burc_somun_kure.png) |
| 15  | Rot başı küresi            | 12   | Ø11.11 × 8 mm                                                                           | Katalog        | [07](img/cad/parcalar/07_eklem_pim_burc_somun_kure.png) |
| 16  | Rot başı gövdesi (dişi M5) | 12   | Ø18 × 6 mm baş, Ø9 şaft, merkezden uca 27 mm                                            | Katalog        | [08](img/cad/parcalar/08_uzun_kol_rot_basi.png)         |
| 17  | M5 saplama                 | 6    | 167 mm                                                                                  | —              | [08](img/cad/parcalar/08_uzun_kol_rot_basi.png)         |
| 18  | Uç platform                | 1    | PLA %20, R35 × 5 mm; P orta düzlemde; 3 kulak; rot başı kesikleri; mıknatıs cebi 2.5 mm | Kulak ve cep   | [09](img/cad/parcalar/09_platform_miknatis.png)         |
| 19  | Elektromıknatıs            | 1    | Ø20 × 15 mm; P'den uca 15.0 mm                                                          | Çap, kütle     | [09](img/cad/parcalar/09_platform_miknatis.png)         |

### Montaj görselleri

[iso](img/cad/iso.png), [ön](img/cad/on.png), [yan](img/cad/yan.png), [üst](img/cad/ust.png), [mekanizma](img/cad/mekanizma.png), [eklem](img/cad/eklem.png), [1. kol yukarıda (önden)](img/cad/kol1_yukari.png), [1. kol yukarıda (iso)](img/cad/kol1_yukari_iso.png), [1. kol yukarıda (yakın)](img/cad/kol1_yukari_yakin.png)

### Revizyon 2 (kullanıcı düzeltmeleri)

| Düzeltme                                                                    | Durum |
| --------------------------------------------------------------------------- | ----- |
| Sütunun açık yüzü kapalı (D kesit)                                          | ✔    |
| Üst plakada dikdörtgen kol açıklıkları; 1. kol −69.6°'ye çakışmasız çıkıyor | ✔    |
| P'den mıknatıs ucuna 15 mm (sabit kısıt)                                    | ✔    |
| Tavanın robot tarafı küçültüldü (R100 → R45)                                | ✔    |
| Bağlantı delikleri merkeze yakın (R75 → R18), tavan ve üst plakada          | ✔    |
| Rot başı küresi ayrı parça (gövde küre etrafında eğilir)                    | ✔    |
| Görseller 8 bit RGB (telefonda açılır)                                      | ✔    |
