# CAD kontrol raporu

## Montaj pozu P = (0.0, 0.0, -190.0) mm, θ = [10.59, 10.59, 10.59]°

### Kinematik ölçüler

- Kol 1: taban yarıçapı 65.000, kısa kol 64.000, platform yarıçapı 35.000, saplama aralığı 30.000 mm
- Kol 2: taban yarıçapı 65.000, kısa kol 64.000, platform yarıçapı 35.000, saplama aralığı 30.000 mm
- Kol 3: taban yarıçapı 65.000, kısa kol 64.000, platform yarıçapı 35.000, saplama aralığı 30.000 mm

### Uzun kollar

| Kol | Çubuk | Merkezden merkeze (mm) | Rot başı yanal açısı (°) |
|---|---|---|---|
| 1 | a | 201.0000 (istif hatası 4.3e-14) | 0.00 |
| 1 | b | 201.0000 (istif hatası 4.3e-14) | 0.00 |
| 2 | a | 201.0000 (istif hatası 5.9e-14) | 0.00 |
| 2 | b | 201.0000 (istif hatası 5.9e-14) | 0.00 |
| 3 | a | 201.0000 (istif hatası 2.8e-14) | 0.00 |
| 3 | b | 201.0000 (istif hatası 6.4e-14) | 0.00 |

### Çakışma (> 0.5 mm³)

- Çakışma yok.

### Eklem istifi

- Kısa kol ucu: saplama aralığı 30.00 mm (hedef 30), pim boyu 58.0 mm, iç burç 10 mm, dış burç 5 mm
- Platform kulağı: saplama aralığı 30.00 mm (hedef 30), pim boyu 58.0 mm, iç burç 5 mm, dış burç 5 mm
- Rot başı eğilme boşluğu: gövde yan yüzünün iç yarıçapı 4.68 mm > burcun en geniş yarıçapı 4.50 mm, gövde burca değmez; eğilme sınırı rot başının kendi sınırıdır (13°, kinematik limit 14°).

### Radyuslar

- POM taban: dikdörtgen uç köşeleri: R20, 2 kenar
- kısa kol: artı delik iç köşeleri: R0.8, 4 kenar
- motor kutusu: dış kenarlar: R2, 8 kenar
- platform: kulak kökleri ve kesik köşeleri: R1.5, 12/24 kenar (tek tek)
- tavan: boyun geçişleri: R8, 4 kenar
- çıkış mili: artı kesit iç köşeleri: R0.5, 4 kenar
- üst plaka: açıklık köşeleri: R3, 15 kenar

### Uç işlevci

- P'den mıknatıs ucuna 15.00 mm (kısıt: ee_offset = 15.0 mm). P plakanın orta düzleminde; mıknatıs cebi alt yüzden 2.5 mm derin (varsayım).
- Montaj pozunda mıknatıs ucu z = -205.0 mm, zemin z = -240.0 mm.

## Kontrol pozu `kol1_yukari`: P = (52.0, 0.0, -141.0) mm, θ = [-69.64, -13.78, -13.78]°

### Kinematik ölçüler

- Kol 1: taban yarıçapı 65.000, kısa kol 64.000, platform yarıçapı 35.000, saplama aralığı 30.000 mm
- Kol 2: taban yarıçapı 65.000, kısa kol 64.000, platform yarıçapı 35.000, saplama aralığı 30.000 mm
- Kol 3: taban yarıçapı 65.000, kısa kol 64.000, platform yarıçapı 35.000, saplama aralığı 30.000 mm

### Uzun kollar

| Kol | Çubuk | Merkezden merkeze (mm) | Rot başı yanal açısı (°) |
|---|---|---|---|
| 1 | a | 201.0000 (istif hatası 4.0e-14) | 0.00 |
| 1 | b | 201.0000 (istif hatası 4.0e-14) | 0.00 |
| 2 | a | 201.0000 (istif hatası 2.6e-14) | 12.95 |
| 2 | b | 201.0000 (istif hatası 3.0e-14) | 12.95 |
| 3 | a | 201.0000 (istif hatası 3.3e-14) | 12.95 |
| 3 | b | 201.0000 (istif hatası 3.6e-14) | 12.95 |

### Çakışma (> 0.5 mm³)

- Çakışma yok.

## Kütleler

| Bağ | Kütle (g) |
|---|---|
| base | 2599.6 |
| bicep_1 | 30.7 |
| bicep_2 | 30.7 |
| bicep_3 | 30.7 |
| forearm_1_a | 35.0 |
| forearm_1_b | 35.0 |
| forearm_2_a | 35.0 |
| forearm_2_b | 35.0 |
| forearm_3_a | 35.0 |
| forearm_3_b | 35.0 |
| platform | 104.3 |

Hareketli toplam: 406.5 g
