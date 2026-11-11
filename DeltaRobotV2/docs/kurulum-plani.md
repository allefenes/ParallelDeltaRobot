# Üretim ve kurulum planı

Robot yeniden üretilip kurulacaksa izlenecek sıra. Yaşayan bir belgedir: her faz kendi adımlarını ekler. Ölçüler ve malzemeler için kaynak [robot-girdileri.md](robot-girdileri.md); orada "Varsayım" ya da "Açık" işaretli değerler üretimden önce kesinleştirilmelidir.

Durum etiketleri: **Hazır** (adımlar yazılı), **Taslak** (içerik kısmen belli), **Bekliyor** (ilgili faz tamamlanınca yazılacak).

## 0. Ön koşullar — Taslak

- [ ] Motor seçimi kesinleşti (V1: 3× Dynamixel AX-12A; yeniden kurulumda değişebilir)
- [ ] Gövde malzemesi kesinleşti (V1: 7075 kaynaklı; 7075 kaynağa pek uygun değil, 6061/5083 değerlendirilecek)
- [ ] F0.5 CAD modelinden üretim çizimleri ve STL'ler çıkarıldı
- [ ] Malzeme listesi (BOM) hazır — F0.5/F2'de eklenecek

## 1. Parça üretimi — Taslak

| Parça                         | Yöntem                         | Malzeme           | Not                                                            |
| ----------------------------- | ------------------------------ | ----------------- | -------------------------------------------------------------- |
| Kısa kol ×3                   | Lazer kesim                    | 2 mm 7075 Al      | Motor ucunda artı delik, eklem ucunda Ø5                       |
| Tavan                         | Lazer kesim                    | 5 mm Al           | Anahtar deliği biçimi, motor gövdesi için 3 delik              |
| Sütun                         | Lazer kesim + kıvırma + kaynak | 5 mm Al           | Yarım silindir                                                 |
| Taban                         | CNC / lazer                    | 5 mm POM          |                                                                |
| Motor gövdesi ve kapaklar     | 3B baskı                       | PLA               | Baskı ayarları F0.5'te                                         |
| Artı kesitli çıkış milleri ×3 | 3B baskı                       | PLA, %100 doluluk | Ø8 rulman yatağı                                               |
| Uç platform                   | 3B baskı                       | PLA, %20 doluluk  | R35, 5 mm, 3 kulak                                             |
| Burçlar ×18                   | 3B baskı ya da torna           | PLA (varsayım)    | 5 mm, Ø5 delik, konik dış yüz; 12 kısa kol + 6 platform tarafı |
| Uzun kollar ×6                | M5 saplama kesimi              | Çelik             | 167 mm; her rot başına 10 mm girer, merkezden merkeze 201 mm   |
| Pimler ×6                     | M5 saplama kesimi              | Çelik             | ~50 mm                                                         |

Hazır alınacaklar: 12× dişi M5 rot başı, 6× 608ZZ rulman, M5 fiber somunlar, elektromıknatıs (15 mm), 12 V güç kaynağı, Raspberry Pi 4B, haberleşme adaptörü, kamera.

## 2. Mekanik montaj — Taslak (F0.5)

Sıra F0.5 montaj modelinden ([cad/](../cad/README.md)) çıkarıldı; ölçüm yapılmış bir robotla doğrulanmadı.

1. POM tabana sütunu bağla; sütunun üstündeki tavanın yatay olduğunu kontrol et.
2. Motor gövdesi üst plakasına üç AX-12A'yı bağla (çıkış eksenleri teğet, göbekler aynı dönüş yönünde).
3. Her motor için rulman yatağının alt yarısına iki 608ZZ'yi yerleştir; artı kesitli mili göbek flanşına bağlayıp rulmanlardan geçir.
4. Kısa kolu, iki rulmanın arasında mile artı deliğinden geçir; kapakları 2'şer vidayla sık.
5. Motor gövdesini 3 cıvatayla tavanın altına bağla.
6. Uzun kolları hazırla: 167 mm saplamanın iki ucuna dişi rot başlarını 10 mm vidala; altı kolun merkezden merkeze boyunu 201 mm'ye eşitle.
7. Kısa kol uçlarına eklem istifini kur: somun, rot başı, 2 burç, kısa kol, 2 burç, rot başı, somun.
8. Platform kulaklarına aynı istifi kur (her yanda 1 burç); elektromıknatısı platformun altına bağla.
9. Motorlar enerjisizken platformu elle bütün çalışma alanında gezdir; takılma ya da sürtünme olmamalı.

Bilinen ilkeler:

- Uzun kolların merkezden merkeze boyu (201 mm) altı kolda aynı olmalı; paralelkenarın iki saplaması eşit boyda ayarlanır.
- Motor çıkışını rulmanlı mil taşır; kısa kol mile artı delikle geçer, servoya radyal yük binmez.
- Montaj sonunda motorlar enerjisizken uç işlevci elle zorlanmadan her yöne hareket etmelidir (V1 davranışı).

## 3. Kablolama ve güç — Bekliyor (F3/F5)

- 12 V güç kaynağı, akımı üç motorun en büyük akımından yüksek (≥5 A, varsayım)
- Raspberry Pi beslemesi, elektromıknatıs sürücüsü, haberleşme adaptörü: Açık

## 4. Servo yapılandırması — Bekliyor (F3)

Motor kimlikleri (1, 2, 3), haberleşme hızı, açı limitleri ve sıfır konumu.

## 5. Robot bilgisayarı: işletim sistemi ve ROS2 — Bekliyor (F3)

Ubuntu 24.04 + ROS2 Jazzy kurulumu, servislerin konteyner olarak başlatılması.

## 6. Kalibrasyon — Bekliyor (F3/F4.5)

Motor sıfır ofsetleri, tabla hücre koordinatları, kamera.

## 7. İlk enerji verme ve güvenlik kontrolleri — Bekliyor (F3)

Süpervizör limit testleri, acil stop, bağlantı kopunca güvenli duruş, sıcaklık bekçisi.

## 8. Sunucu kurulumu — Bekliyor (F4)

`compose.yaml` ile web, API ve sandbox servislerinin kendi sunucuda kurulması.
