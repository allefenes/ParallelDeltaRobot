# İlerleme

Faz ilerlemesi sayılabilir birimlerle tutulur; her çalışma adımında güncellenir.

Son güncelleme: 2026-11-12

## Özet

| Faz             | Durum                                                      | Sayaç                                                          |
| --------------- | ---------------------------------------------------------- | -------------------------------------------------------------- |
| F0 İskele       | Tamamlandı                                                 | 6 / 6 teslim                                                   |
| F0.5 CAD        | Revizyon 3 tamamlandı, **montaj görselleri onay bekliyor** | 19 / 19 parça çizildi, 111 / 111 bileşen montajlandı           |
| F1 Kinematik    | Başlamadı (F0.5 onayı bekleniyor)                          | —                                                              |
| Malzeme listesi | Başladı; her fazda güncellenir                             | 28 kalem (19'u CAD'den), [hardware/bom.md](../hardware/bom.md) |

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

| Adım                                                      | Sayaç                                         |
| --------------------------------------------------------- | --------------------------------------------- |
| Parça çizildi                                             | 19 / 19                                       |
| Ölçü doğrulandı (kinematik: R65 / 64 / 201 / R35 / 30 mm) | 19 / 19                                       |
| Montajlandı (bileşen)                                     | 111 / 111                                     |
| Çakışma kontrolü (2 poz: montaj, 1. kol −69.6°)           | 2 / 2 temiz                                   |
| Radyus (7 parça grubu)                                    | 7 / 7 uygulandı (platformda 24 kenarın 12'si) |
| Renklendirildi                                            | 111 / 111                                     |
| Mesh + kütle/atalet dışa aktarıldı (simülasyon bağı)      | 11 / 11                                       |
| Montaj görseli                                            | 11 / 11                                       |
| Parça önizleme görseli (19 parça, 9 görselde)             | 9 / 9                                         |
| Kullanıcı onayı                                           | 0 / 1                                         |

### Parça listesi (19 benzersiz, 111 adet)

| #   | Parça                      | Adet | Ana ölçüler                                                                                                                                       | Varsayım             | Önizleme                                                |
| --- | -------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | ------------------------------------------------------- |
| 1   | POM taban                  | 1    | 5 mm; R160 yuvarlak uç + 320 mm genişlik; köşeler R20                                                                                             | Dış ölçüler          | [01](img/cad/parcalar/01_pom_taban.png)                 |
| 2   | Sütun (D kesit)            | 1    | 7075, 5 mm; yarım silindir R50 + düz kapak levhası, 267 mm                                                                                        | Yarıçap, konum       | [02](img/cad/parcalar/02_sutun_tavan.png)               |
| 3   | Tavan                      | 1    | 7075, 5 mm; robot ucu R45, boyun 70 mm (geçişler R8), sütun ucu R50; 3 delik Ø5.5 / R18                                                           | Ölçüler              | [02](img/cad/parcalar/02_sutun_tavan.png)               |
| 4   | Motor gövdesi (tek parça)  | 1    | PLA; R96 × 5 mm üst plaka, 3 dikdörtgen kol açıklığı (köşeler R3), 3 motor kutusu (2.5 mm et, altı açık, kenarlar R2), 6 rulman yatağı alt yarısı | Ölçüler              | [03](img/cad/parcalar/03_motor_govdesi.png)             |
| 5   | Rulman kapağı              | 6    | PLA; 32 × 10 × 13 mm                                                                                                                              | Ölçüler              | [04](img/cad/parcalar/04_rulman_kapagi_vida.png)        |
| 6   | Kapak vidası               | 12   | M3 × 21 mm                                                                                                                                        | Ölçü                 | [04](img/cad/parcalar/04_rulman_kapagi_vida.png)        |
| 7   | AX-12A                     | 3    | 32 × 50 × 40 mm zarf, göbek Ø20                                                                                                                   | Göbek konumu         | [05](img/cad/parcalar/05_motor_rulman_mil.png)          |
| 8   | 608ZZ rulman               | 6    | 8 × 22 × 7 mm                                                                                                                                     | —                    | [05](img/cad/parcalar/05_motor_rulman_mil.png)          |
| 9   | Çıkış mili                 | 3    | PLA %100; tüm boyu artı kesit (uçlar Ø8 dairede, kol 3 mm, iç köşeler R0.5), Ø16 flanş                                                            | Kol genişliği        | [05](img/cad/parcalar/05_motor_rulman_mil.png)          |
| 10  | Kısa kol                   | 3    | 7075, 2 mm; merkezden merkeze 64; R14 → Ø10; artı delik iç köşeleri R0.8                                                                          | Dış hat              | [06](img/cad/parcalar/06_kisa_kol.png)                  |
| 11  | Pim                        | 6    | M5 × 58 mm                                                                                                                                        | —                    | [07](img/cad/parcalar/07_eklem_pim_burc_somun_kure.png) |
| 12  | İç burç (konik)            | 12   | Ø9 → Ø6.5; kısa kol tarafı 10 mm, platform tarafı 5 mm                                                                                            | Malzeme, çaplar      | [07](img/cad/parcalar/07_eklem_pim_burc_somun_kure.png) |
| 13  | Dış burç (konik)           | 12   | Ø6.5 → Ø9, 5 mm                                                                                                                                   | Malzeme, çaplar      | [07](img/cad/parcalar/07_eklem_pim_burc_somun_kure.png) |
| 14  | M5 fiber somun             | 12   | AA 8, 5 mm                                                                                                                                        | —                    | [07](img/cad/parcalar/07_eklem_pim_burc_somun_kure.png) |
| 15  | Rot başı küresi            | 12   | Ø11.11 × 8 mm                                                                                                                                     | Katalog              | [07](img/cad/parcalar/07_eklem_pim_burc_somun_kure.png) |
| 16  | Rot başı gövdesi (dişi M5) | 12   | Ø18 × 6 mm baş, Ø9 şaft, merkezden uca 27 mm                                                                                                      | Katalog              | [08](img/cad/parcalar/08_uzun_kol_rot_basi.png)         |
| 17  | M5 saplama                 | 6    | 167 mm                                                                                                                                            | —                    | [08](img/cad/parcalar/08_uzun_kol_rot_basi.png)         |
| 18  | Uç platform                | 1    | PLA %20, R35 × 5 mm; P orta düzlemde; 3 kulak; rot başı kesikleri; 3 süs deliği Ø8; mıknatıs cebi 2.5 mm                                          | Kulak, cep, delikler | [09](img/cad/parcalar/09_platform_miknatis.png)         |
| 19  | Elektromıknatıs            | 1    | Ø20 × 15 mm; P'den uca 15.0 mm                                                                                                                    | Çap, kütle           | [09](img/cad/parcalar/09_platform_miknatis.png)         |

### Montaj görselleri

[iso](img/cad/iso.png), [ön](img/cad/on.png), [yan](img/cad/yan.png), [üst](img/cad/ust.png), [mekanizma](img/cad/mekanizma.png), [eklem](img/cad/eklem.png), [motor kutuları (alttan)](img/cad/motor_kutulari_alttan.png), [motor kutusu (yakın)](img/cad/motor_kutusu_yakin.png), [1. kol yukarıda (önden)](img/cad/kol1_yukari.png), [1. kol yukarıda (iso)](img/cad/kol1_yukari_iso.png), [1. kol yukarıda (yakın)](img/cad/kol1_yukari_yakin.png)

### Kullanıcı düzeltmeleri (revizyon 2 + 3)

| #   | Düzeltme                                                                                             | Durum          |
| --- | ---------------------------------------------------------------------------------------------------- | -------------- |
| 1   | Sütunun açık yüzü kapalı (D kesit)                                                                   | ✔             |
| 2   | Üst plakada dikdörtgen kol açıklıkları; 1. kol −69.6°'ye çakışmasız çıkıyor                          | ✔             |
| 3   | P'den mıknatıs ucuna 15 mm (sabit kısıt)                                                             | ✔             |
| 4   | Tavanın robot tarafı küçük (R100 → R45)                                                              | ✔             |
| 5   | Bağlantı delikleri merkeze yakın (R18), tavan ve üst plakada                                         | ✔             |
| 6   | Üst plaka boyutu: motor kutuları R95'e uzandığı için R96 (küçültülemedi, kutuları örtmesi gerekiyor) | ✔ (gerekçeli) |
| 7   | Platformda 3 süs deliği (Ø8, kulaklar arasında)                                                      | ✔             |
| 8   | Motorlar kendi kutularında; gövde tek parça; yataklar ve 2 vidalı kapaklar                           | ✔             |
| 9   | Radyuslar (7 parça grubu; ayrıntı `cad/out/checks.md`)                                               | ✔             |
| 10  | Eklem sırası somun-burç-mafsal-burç-kol-…; burçlar boydan boya konik; aralık 30 mm korundu           | ✔             |
| 11  | Çıkış mili tüm boyu artı kesit                                                                       | ✔             |
