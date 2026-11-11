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

## CAD'de eklenen varsayımlar (F0.5)

Model kurulurken veri olmayan yerler için seçilen değerler. Hepsi `config/robot.yaml`'da `varsayim` etiketlidir.

| Konu                      | Seçilen                                                                                                                                               | Neden                                                         |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Platform kulağı           | 12 mm kalınlık, her yanda 1 burç; pim ekseni plakanın orta düzleminde, kenarda (r = 35)                                                               | 30 mm saplama aralığı (12 + 2×5 + 8) ve P → uç = 15 mm        |
| Platform kesikleri        | Her kulağın iki yanında rot başı / burç / somun için dikdörtgen kesik                                                                                 | Ø18 rot başı gövdesi plakaya değmesin                         |
| Mıknatıs cebi             | Plakanın alt yüzünden 2.5 mm derin; mıknatısın üst yüzü P düzleminde                                                                                  | P'den mıknatıs ucuna 15 mm (kullanıcı)                        |
| Burç malzemesi            | PLA %100                                                                                                                                              | Bilinmiyor                                                    |
| Motor yerleşimi           | Çıkış ekseni teğet, gövde radyal içe, göbek ekseni gövde ucundan 11 mm                                                                                | AX-12A zarfı; yataklar ve kısa kol kol düzleminde ortalanır   |
| Rulman yatakları          | Mil ekseninden ±9 mm; alt yarı yalnız iç askı duvarıyla üst plakaya bağlı; üstte kapak                                                                | Dış taraf, kol yukarı kalkarken uzun kolların geçişi için boş |
| Motor gövdesi üst plakası | R90 × 5 mm; her kolun üstünde 52 × 48 mm dikdörtgen açıklık                                                                                           | Kullanıcı: dikdörtgen açıklık; ölçüler varsayım               |
| Bağlantı delikleri        | 3 × Ø5.5, R18 (kollar arasında, 60/180/300°), tavan ve üst plakada aynı                                                                               | Kullanıcı: merkeze yakın, motorların içinde                   |
| Gövde                     | Sütun D kesitli (yarım silindir R50 + düz kapak), merkezi robot merkezinden 210 mm (−X); tavan robot ucu R45, boyun 70 mm; POM R160 + 320 mm genişlik | Çizimlerle tutarlı tahmin                                     |
| Elektromıknatıs           | Ø20 × 15 mm, ~35 g                                                                                                                                    | Yükseklik kullanıcıdan, diğerleri tipik                       |
| PLA %20 etkin yoğunluk    | 0.56 g/cm³                                                                                                                                            | İnce parçada duvar/kabuk baskın                               |

## CAD'den çıkan bulgular

Ayrıntı: [cad/out/checks.md](../cad/out/checks.md)

- Montaj kinematik ölçüleri birebir sağlıyor: taban R65, kısa kol 64, uzun kol 201, platform R35, saplama aralığı 30 mm.
- İki pozda çakışma yok: montaj pozu (P = 0, 0, −190) ve 1. kolun yazılım limitinde olduğu kontrol pozu (θ1 = −69.6°). Üst plakadaki açıklıklar sayesinde kol −70°'ye kadar çıkabiliyor; o pozda diğer kolların rot başı açısı 12.95° (katalog sınırı 13°).
- P'den mıknatıs ucuna 15.00 mm (kısıt olarak denetleniyor).
- Hareketli kütle (CAD): **~398 g** (3 kısa kol bağı 88 g, 6 uzun kol 210 g, platform + mıknatıs 100 g; rot başı küreleri pimle birlikte kısa kol ve platform bağlarında).

## V1'e göre koordinat farkı

V2 çerçevesinde +Z yukarıdır; V1'de +Z aşağıydı. Motor açısı θ'nın işareti aynıdır (pozitif θ kolu indirir). Eksen çevrildiği için kol numaralandırması aynalanır: V1'in 2. ve 3. kolu V2'de yer değiştirir. F1'de V1 ile karşılaştırma bu eşlemeyle yapılır.
