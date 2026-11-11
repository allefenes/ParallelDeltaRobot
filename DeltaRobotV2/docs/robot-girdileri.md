# Robot girdileri

V2, V1 robotunun birebir aynısıdır. Bu belge, CAD (F0.5), kinematik (F1) ve datasheet (F2) için kullanılan bütün ölçüleri ve kaynaklarını tek yerde toplar. Fiziksel robot artık elimizde olmadığı için bazı değerler türetilmiş ya da varsayılmıştır; bunlar açıkça işaretlidir.

**Kaynak etiketleri**

- **JSON**: V1 `KilavuzDeltaRobotics/data/myRobot.json` (kanonik geometri)
- **Kullanıcı**: proje sahibinin anlatımı ve el çizimleri
- **Türetilmiş**: kullanıcı bilgisinden hesaplandı
- **Varsayım**: veri yok; makul değer seçildi, ölçümle doğrulanacak

## Kinematik geometri

Tüm uzunluklar eklem merkezinden eklem merkezine ölçülüdür (Kullanıcı).

| Parametre                       | Değer          | Kaynak           | Not                                |
| ------------------------------- | -------------- | ---------------- | ---------------------------------- |
| Taban yarıçapı (motor ekseni)   | 65 mm          | JSON `base`      |                                    |
| Kısa kol (bicep)                | 64 mm          | JSON `bicep`     | V1 kodundaki varsayılan 64.2 değil |
| Uzun kol (forearm)              | 201 mm         | JSON `forearm`   |                                    |
| Uç platform eklem yarıçapı      | 35 mm          | JSON `end`       | V1 kodundaki varsayılan 37.5 değil |
| Taban düzleminden zemine        | 240 mm         | JSON `btf`       |                                    |
| Uç işlevci ofseti               | 15 mm          | JSON `eeOffset`  | Elektromıknatıs yüksekliği         |
| Motor açı limitleri             | +150° / −70°   | JSON             |                                    |
| Küresel mafsal yanal açı limiti | 14°            | JSON `joint`     | Rot başı açısal sapma sınırı       |
| Motor adım açısı                | 0.29°          | JSON `turnAngle` | AX-12A: 300° / 1024                |
| Kol açıları                     | 0°, 120°, 240° | V1 kodu          |                                    |

## Mekanik

| Bileşen                                            | Bilgi                                                                                                                                                                                              | Kaynak                                                  |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| Robot tipi                                         | 3 DOF öteleme deltası; her kolda paralelkenar (2 saplama), platform yönelimi sabit                                                                                                                 | Kullanıcı                                               |
| Kısa kol                                           | 2 mm 7075 alüminyum, lazer kesim, düz ve sivrilen plaka. Motor ucunda artı şeklinde delik; tork artı kesitli milden alınır (göbeğe vidalı değil). Eklem ucunda Ø10 göbek, Ø5 delik                 | Kullanıcı (çizim)                                       |
| Kısa kol dış hattı                                 | Çizimden yaklaşık                                                                                                                                                                                  | Varsayım                                                |
| Uzun kollar                                        | M5 saplama, kol başına 2 adet                                                                                                                                                                      | Kullanıcı                                               |
| Eklemler                                           | Dişi M5 rot başı, saplamaya vidalı                                                                                                                                                                 | Kullanıcı                                               |
| Eklem istifi (pim boyunca)                         | fiber somun, rot başı, 2 burç, kısa kol, 2 burç, rot başı, fiber somun                                                                                                                             | Kullanıcı                                               |
| Burç                                               | Silindirik, 5 mm boy, Ø5 delik, rot başına bakan yüzü konik                                                                                                                                        | Kullanıcı                                               |
| Burç koni açısı ve dış çapı                        | Rot başı ≥14° eğilebilecek şekilde                                                                                                                                                                 | Varsayım                                                |
| Paralelkenar saplama aralığı                       | 30 mm = 2 + 2×10 + 2×4                                                                                                                                                                             | Türetilmiş (rot başı küre genişliği ~8 mm varsayımıyla) |
| Pim                                                | Kesilmiş M5 saplama, ~50 mm                                                                                                                                                                        | Türetilmiş                                              |
| Uç platform                                        | Dairesel, R35 (Ø70), 5 mm kalınlık, PLA %20 doluluk; üstte 3 kulak, kenardan biraz taşar; kulaklarda aynı 30 mm istif                                                                              | Kullanıcı                                               |
| Uç işlevci                                         | Elektromıknatıs, 15 mm yükseklik                                                                                                                                                                   | Kullanıcı                                               |
| Elektromıknatıs modeli, tutma kuvveti, sürme şekli | Bilinmiyor                                                                                                                                                                                         | Açık                                                    |
| Gövde                                              | Ters L, 7075 alüminyum, rijit. Sütun: 5 mm levha kıvrılıp kaynaklanmış yarım silindir. Tavan: 5 mm levha, anahtar deliği biçimi, sütuna kaynaklı; yuvarlak ucundaki 3 delik motor gövdesini bağlar | Kullanıcı (çizim)                                       |
| Taban                                              | 5 mm POM levha, bir ucu yuvarlatılmış dikdörtgen; L buna monte                                                                                                                                     | Kullanıcı (çizim)                                       |
| Gövde, tavan ve taban kaba ölçüleri                | Geometriden tutarlı tahmin                                                                                                                                                                         | Varsayım                                                |
| Motor gövdesi                                      | PLA baskı dairesel yapı; 3× AX-12A içinde; her motor önünde 2 rulman ve 2 vidalı üst kapak                                                                                                         | Kullanıcı                                               |
| Rulman                                             | 608ZZ (8×22×7), motor başına 2                                                                                                                                                                     | Kullanıcı ("stres çarkı rulmanı")                       |
| Çıkış mili                                         | PLA %100 doluluk, artı kesitli, rulman yatağı Ø8                                                                                                                                                   | Kullanıcı / Türetilmiş                                  |
| Nitel özellik                                      | Motorlar enerjisizken uç işlevci elle çok rahat hareket ettirilebiliyordu (düşük sürtünme, iyi yataklama)                                                                                          | Kullanıcı                                               |

**Yeniden kurulum notu:** 7075 alüminyum ergitme kaynağına pek uygun değildir. Mevcut yapı olduğu gibi belgelenir; yeniden kurulumda 6061 ya da 5083 değerlendirilmelidir.

## Elektronik

| Bileşen                          | Bilgi                                                            | Kaynak    |
| -------------------------------- | ---------------------------------------------------------------- | --------- |
| Motorlar                         | 3× Dynamixel AX-12A, Protocol 1.0                                | V1 kodu   |
| Ana bilgisayar                   | Raspberry Pi 4B (8 GB)                                           | V1 README |
| Güç kaynağı                      | 12 V LED tipi anahtarlamalı; üç motorun maksimum akımından fazla | Kullanıcı |
| Güç kaynağı akımı                | ≥5 A                                                             | Varsayım  |
| Raspberry Pi beslemesi           | Bilinmiyor                                                       | Açık      |
| Pi ↔ AX-12A haberleşme adaptörü | Bilinmiyor (V1 README bir devreden söz ediyor, repoda yok)       | Açık      |
| Kamera                           | Var (V1 kodu)                                                    | V1 kodu   |

## Yaklaşık hareketli kütle

F0.5'teki CAD modeli kesin değeri verecek. Kaba tahmin:

| Parça                | Adet    | Tahmin         |
| -------------------- | ------- | -------------- |
| Kısa kol             | 3       | ~30 g          |
| M5 saplama (~175 mm) | 6       | ~130 g         |
| Dişi M5 rot başı     | 12      | ~120 g         |
| Pim ve somunlar      | 6 eklem | ~20 g          |
| Uç platform          | 1       | ~10 g          |
| Elektromıknatıs      | 1       | ~30–40 g       |
| **Toplam**           |         | **~340–350 g** |
