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

| Bileşen                                            | Bilgi                                                                                                                                                                                              | Kaynak                                        |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| Robot tipi                                         | 3 DOF öteleme deltası; her kolda paralelkenar (2 saplama), platform yönelimi sabit                                                                                                                 | Kullanıcı                                     |
| Kısa kol                                           | 2 mm 7075 alüminyum, lazer kesim, düz ve sivrilen plaka. Motor ucunda artı şeklinde delik; tork artı kesitli milden alınır (göbeğe vidalı değil). Eklem ucunda Ø10 göbek, Ø5 delik                 | Kullanıcı (çizim)                             |
| Kısa kol dış hattı                                 | Çizimden yaklaşık                                                                                                                                                                                  | Varsayım                                      |
| Uzun kollar                                        | M5 saplama, kol başına 2 adet                                                                                                                                                                      | Kullanıcı                                     |
| Eklemler                                           | Dişi M5 rot başı, saplamaya vidalı                                                                                                                                                                 | Kullanıcı                                     |
| Eklem istifi (pim boyunca)                         | fiber somun, dış burç, rot başı, iç burç, kısa kol, iç burç, rot başı, dış burç, fiber somun                                                                                                       | Kullanıcı                                     |
| Burç                                               | Boydan boya konik (kesik koni), Ø5 delik; dar ucu rot başına bakar                                                                                                                                 | Kullanıcı                                     |
| Burç uzunlukları ve çapları                        | İç burç 10 mm (kısa kol) / 5 mm (platform), dış burç 5 mm; Ø9 → Ø6.5                                                                                                                               | Türetilmiş (30 mm aralık) / Varsayım (çaplar) |
| Paralelkenar saplama aralığı                       | 30 mm = kol 2 + 2×10 iç burç + 8 küre (değişmez, kullanıcı)                                                                                                                                        | Kullanıcı / Türetilmiş                        |
| Pim                                                | Kesilmiş M5 saplama, 58 mm (~60 mm kesilir)                                                                                                                                                        | Türetilmiş                                    |
| Uç platform                                        | Dairesel, R35 (Ø70), 5 mm kalınlık, PLA %20 doluluk; üstte 3 kulak, kenardan biraz taşar; kulaklarda aynı 30 mm istif                                                                              | Kullanıcı                                     |
| Uç işlevci                                         | Elektromıknatıs, 15 mm yükseklik                                                                                                                                                                   | Kullanıcı                                     |
| Elektromıknatıs modeli, tutma kuvveti, sürme şekli | Bilinmiyor                                                                                                                                                                                         | Açık                                          |
| Gövde                                              | Ters L, 7075 alüminyum, rijit. Sütun: 5 mm levha kıvrılıp kaynaklanmış yarım silindir. Tavan: 5 mm levha, anahtar deliği biçimi, sütuna kaynaklı; yuvarlak ucundaki 3 delik motor gövdesini bağlar | Kullanıcı (çizim)                             |
| Taban                                              | 5 mm POM levha, bir ucu yuvarlatılmış dikdörtgen; L buna monte                                                                                                                                     | Kullanıcı (çizim)                             |
| Gövde, tavan ve taban kaba ölçüleri                | Geometriden tutarlı tahmin                                                                                                                                                                         | Varsayım                                      |
| Motor gövdesi                                      | PLA baskı, tek parça: üst plaka + her motor için kutu (motor dönmesin) + rulman yataklarının alt yarısı; üstte 2 vidalı kapaklar                                                                   | Kullanıcı                                     |
| Rulman                                             | 608ZZ (8×22×7), motor başına 2                                                                                                                                                                     | Kullanıcı ("stres çarkı rulmanı")             |
| Çıkış mili                                         | PLA %100, tüm boyu artı kesitli (kısa kol üzerinden kayarak takılır); uçları Ø8 dairede, 608ZZ'ye oturur                                                                                           | Kullanıcı                                     |
| Nitel özellik                                      | Motorlar enerjisizken uç işlevci elle çok rahat hareket ettirilebiliyordu (düşük sürtünme, iyi yataklama)                                                                                          | Kullanıcı                                     |

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

| Konu                                 | Seçilen                                                                                                                                                                                                                          | Neden                                                                 |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Platform                             | Dairesel disk R28 (rot başı gövdelerinin en yakın noktası r = 30); kulak eksenleri r = 35, kulaklar diskten taşar; 12 mm kulak, 5 mm iç + 5 mm dış burç; pimler disk orta düzleminde                                             | Kullanıcı: dairesel, kulaklar taşar; disk yarıçapı varsayım           |
| Mıknatıs cebi                        | Plakanın alt yüzünden 2.5 mm derin; mıknatısın üst yüzü P düzleminde                                                                                                                                                             | P'den mıknatıs ucuna 15 mm (kullanıcı)                                |
| Burç malzemesi                       | PLA %100                                                                                                                                                                                                                         | Bilinmiyor                                                            |
| Motor yerleşimi                      | Çıkış ekseni teğet, gövde radyal içe, göbek ekseni gövde ucundan 11 mm                                                                                                                                                           | AX-12A zarfı; yataklar ve kısa kol kol düzleminde ortalanır           |
| Rulman yatakları                     | Mil ekseninden ±9 mm, 32 mm geniş. Üst yarı üst plakayla tek parça (kullanıcı); alt yarı ayrı kapak, alttan takılır, 2 × M3 vida alttan girer, başları aşağıda (kullanıcı). Vidaların baskıya diş açması ya da insert: varsayım  | Kullanıcı / Varsayım                                                  |
| Motor gövdesi üst plakası ve kutular | Plaka R84.7 = rulman yatağının dış köşesi (R82.2) + 2.5 mm pay (kullanıcı kuralı); her kolun üstünde 3 mm dikdörtgen açıklık (kullanıcı); motor kutuları 2.5 mm et, altı açık; kutu köşeleri R95'e uzanır, plakadan ~10 mm taşar | Kullanıcı: plaka ölçü kuralı ve 3 mm açıklık; pay ve kutular varsayım |
| Bağlantı delikleri                   | 3 × Ø5.5, R18 (kollar arasında, 60/180/300°), tavan ve üst plakada aynı                                                                                                                                                          | Kullanıcı: merkeze yakın, motorların içinde                           |
| Gövde                                | Sütun D kesitli (yarım silindir R50 + düz kapak), merkezi robot merkezinden 210 mm (−X); tavan robot ucu R45, boyun 70 mm; POM R160 + 320 mm genişlik                                                                            | Çizimlerle tutarlı tahmin                                             |
| Elektromıknatıs                      | Ø20 × 15 mm, ~35 g                                                                                                                                                                                                               | Yükseklik kullanıcıdan, diğerleri tipik                               |
| PLA %20 etkin yoğunluk               | 0.56 g/cm³                                                                                                                                                                                                                       | İnce parçada duvar/kabuk baskın                                       |

## CAD'den çıkan bulgular

Ayrıntı: [cad/out/checks.md](../cad/out/checks.md)

- Montaj kinematik ölçüleri birebir sağlıyor: taban R65, kısa kol 64, uzun kol 201, platform R35, saplama aralığı 30 mm.
- İki pozda çakışma yok: montaj pozu (P = 0, 0, −190) ve 1. kolun yazılım limitine yakın kontrol pozu (θ1 = −69.6°).
- **Kısa kolun yukarı mekanik sınırı ≈ −71.6°** (P = (52, 0, z) poz ailesinde ikiye bölme taraması): kol yukarı kalktığında uzun kol saplamaları üst plakanın kenarına değer. Yazılım limiti −70° çakışmasız. Kol ucunun eklem istifi plaka kenarının dışından dolaşır; 3 mm açıklıktan yalnız kısa kol levhası geçer.
- P'den mıknatıs ucuna 15.00 mm (kısıt olarak denetleniyor).
- Hareketli kütle (CAD): **~405 g**.
- Radyuslar: tavan geçişleri R8, POM köşeleri R20, üst plaka açıklıkları R3, motor kutuları R2, platform kulak kökleri R1.5, kısa kol artı deliği R0.8, mil artı kesiti R0.5.
- Süs delikleri: platformda kulaklar arasında 3 × Ø8 (R17).

## V1'e göre koordinat farkı

V2 çerçevesinde +Z yukarıdır; V1'de +Z aşağıydı. Motor açısı θ'nın işareti aynıdır (pozitif θ kolu indirir). Eksen çevrildiği için kol numaralandırması aynalanır: V1'in 2. ve 3. kolu V2'de yer değiştirir. F1'de V1 ile karşılaştırma bu eşlemeyle yapılır.
