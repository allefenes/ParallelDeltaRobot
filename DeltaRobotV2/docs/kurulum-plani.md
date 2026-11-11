# Üretim ve kurulum planı

Robot yeniden üretilip kurulacaksa izlenecek sıra. Yaşayan bir belgedir: her faz kendi adımlarını ekler. Ölçüler ve malzemeler için kaynak [robot-girdileri.md](robot-girdileri.md); orada "Varsayım" ya da "Açık" işaretli değerler üretimden önce kesinleştirilmelidir. Parça adetleri, kütleleri ve tedarik bilgisi: [malzeme listesi (BOM)](../hardware/bom.md). Sistem mimarisi: [mimari.md](mimari.md).

Durum etiketleri: **Hazır** (adımlar yazılı), **Taslak** (içerik kısmen belli), **Bekliyor** (ilgili faz tamamlanınca yazılacak).

## 0. Ön koşullar — Taslak

- [ ] Motor seçimi kesinleşti (V1: 3× Dynamixel AX-12A; yeniden kurulumda değişebilir)
- [ ] Gövde malzemesi kesinleşti (V1: 7075 kaynaklı; 7075 kaynağa pek uygun değil, 6061/5083 değerlendirilecek)
- [ ] F0.5 CAD modelinden üretim çizimleri ve STL'ler çıkarıldı
- [ ] Malzeme listesindeki (hardware/bom.md) "TBD" tedarikçi ve fiyatlar dolduruldu

## 1. Parça üretimi — Taslak

| Parça                                | Yöntem                         | Malzeme           | Not                                                                                                         |
| ------------------------------------ | ------------------------------ | ----------------- | ----------------------------------------------------------------------------------------------------------- |
| Kısa kol ×3                          | Lazer kesim                    | 2 mm 7075 Al      | Motor ucunda artı delik, eklem ucunda Ø5                                                                    |
| Tavan                                | Lazer kesim                    | 5 mm Al           | Anahtar deliği biçimi; robot ucu küçük (R45), merkeze yakın 3 delik (R18)                                   |
| Sütun                                | Lazer kesim + kıvırma + kaynak | 5 mm Al           | D kesit: yarım silindir + düz kapak levhası                                                                 |
| Taban                                | CNC / lazer                    | 5 mm POM          |                                                                                                             |
| Motor gövdesi (tek parça) ve 6 kapak | 3B baskı                       | PLA               | Plaka R84.7, her kolda 3 mm açıklık; motor kutuları ve rulman yatakları plakayla tek parça                  |
| Artı kesitli çıkış milleri ×3        | 3B baskı                       | PLA, %100 doluluk | Tüm boyu artı kesit; uçları Ø8 dairede                                                                      |
| Uç platform                          | 3B baskı                       | PLA, %20 doluluk  | Dairesel R28 × 5 mm, 3 kulak (eksen r = 35); pimler orta düzlemde; 3 süs deliği; altta 2.5 mm mıknatıs cebi |
| Burçlar ×24                          | 3B baskı ya da torna           | PLA (varsayım)    | Boydan boya konik, Ø5 delik; 6 × 10 mm + 6 × 5 mm iç burç, 12 × 5 mm dış burç                               |
| Uzun kollar ×6                       | M5 saplama kesimi              | Çelik             | 167 mm; her rot başına 10 mm girer, merkezden merkeze 201 mm                                                |
| Pimler ×6                            | M5 saplama kesimi              | Çelik             | ~60 mm (istif 58 mm)                                                                                        |

Hazır alınacaklar: 12× dişi M5 rot başı, 6× 608ZZ rulman, 12× M5 fiber somun, 12× M3 × 20 vida (kapaklar), 3× M5 cıvata (gövde-tavan), elektromıknatıs (15 mm), 12 V güç kaynağı, Raspberry Pi 4B, haberleşme adaptörü, kamera.

## 2. Mekanik montaj — Taslak (F0.5)

Sıra F0.5 montaj modelinden ([cad/](../cad/README.md)) çıkarıldı; ölçüm yapılmış bir robotla doğrulanmadı.

1. POM tabana sütunu bağla; sütunun üstündeki tavanın yatay olduğunu kontrol et.
2. Motor gövdesini hazırla (tek parça baskı; çıkış eksenleri teğet, göbek delikleri kutuların dış duvarında).
3. Motorları gövdedeki kutularına alttan yerleştir (kutu motorun dönmesini engeller). Her motor için rulman yatağının alt yarısına iki 608ZZ'yi koy; artı kesitli mili göbeğe bağlayıp rulmanlardan geçir.
4. Kısa kolu, iki rulmanın arasında mile artı deliğinden geçir; kapakları 2'şer vidayla sık. Kısa kol levhası üst plakadaki 3 mm açıklıktan geçer; kol −70°'ye kadar kalkabilmeli (mekanik sınır ≈ −71.6°).
5. Motor gövdesini 3 cıvatayla tavanın altına bağla.
6. Uzun kolları hazırla: 167 mm saplamanın iki ucuna dişi rot başlarını 10 mm vidala; altı kolun merkezden merkeze boyunu 201 mm'ye eşitle.
7. Kısa kol uçlarına eklem istifini kur: somun, dış burç (5 mm), rot başı, iç burç (10 mm), kısa kol, iç burç, rot başı, dış burç, somun. Burçların dar uçları rot başına bakar.
8. Platform kulaklarına aynı istifi kur (iç burçlar 5 mm); elektromıknatısı platformun altındaki cebe oturt. P'den (pim eksenlerinin düzlemi) mıknatıs ucuna 15 mm olmalı.
9. Motorlar enerjisizken platformu elle bütün çalışma alanında gezdir; takılma ya da sürtünme olmamalı.

Bilinen ilkeler:

- Uzun kolların merkezden merkeze boyu (201 mm) altı kolda aynı olmalı; paralelkenarın iki saplaması eşit boyda ayarlanır.
- Motor çıkışını rulmanlı mil taşır; kısa kol mile artı delikle geçer, servoya radyal yük binmez.
- Montaj sonunda motorlar enerjisizken uç işlevci elle zorlanmadan her yöne hareket etmelidir (V1 davranışı).

## 3. Kablolama ve güç — Taslak (F3/F5)

- 12 V güç kaynağı, akımı üç motorun en büyük akımından yüksek (≥5 A, varsayım); servolar ve elektromıknatıs bu hattan.
- **Fiziksel acil stop (ağdan bağımsız):** Mantar buton, servo ve mıknatıs güç hattını doğrudan keser (kontaktör ya da buton kontağı). Butonun ikinci kontağı Pi'nin bir GPIO girişine bağlanır; Pi durumu sunucuya bildirir. Yazılım ya da ağ arızası butonun işlevini etkileyemez.
- Raspberry Pi beslemesi: 12 V → 5 V/3 A DC-DC dönüştürücü ya da ayrı adaptör (açık). Acil stop Pi'nin beslemesini kesmez; Pi telemetriyi ve bağlantıyı korur.
- Pi ↔ servo: yarım-dupleks TTL seri hat (Dynamixel arayüzü: U2D2 ya da 74LS241 tabanlı devre; açık).
- Elektromıknatıs: Pi GPIO'dan MOSFET ile anahtarlanır, serbest dönüş diyotu ile; varsayılan (Pi kapalı / bekçi tetik) durumu tanımlıdır (F3'te kararlaştırılır).

## 4. Servo yapılandırması — Bekliyor (F3)

Motor kimlikleri (1, 2, 3), haberleşme hızı, servo içindeki açı limitleri (yazılım limitleriyle aynı), sıfır konumu.

## 5. Robot bilgisayarı (Raspberry Pi kenarı) — Taslak (F3/F5)

Pi yalnız kenar görevini yapar; ROS2 yığını sunucudadır ([mimari.md](mimari.md)).

1. İşletim sistemi: Ubuntu 24.04 Server (arm64) ya da Raspberry Pi OS Lite; SSH anahtarla, parola girişi kapalı.
2. `delta_edge` servisini kur (C++17, depodaki `edge/`); systemd birimi olarak açılışta başlar, çökerse yeniden başlar.
3. Robot kimliği: sunucunun verdiği belirteç / istemci sertifikası `/etc/delta_edge/` altında, yalnız servis kullanıcısı okuyabilir.
4. **Bağlantıyı Pi açar:** `delta_edge`, sunucuya TLS'li WebSocket ile dışarı doğru bağlanır; yönlendiricide gelen port açılmaz. Bağlantı koparsa üstel bekleme ile yeniden dener.
5. Sınırlar `config/robot.yaml`'ın Pi'deki kopyasından okunur; sunucuyla sürümü eşleşmezse servis hareket kabul etmez.
6. Kamera: WebRTC yayını Pi'den başlatılır (F4/F5).

## 6. Kalibrasyon — Bekliyor (F3/F4.5)

Motor sıfır ofsetleri, tabla hücre koordinatları, kamera.

## 7. İlk enerji verme ve güvenlik kontrolleri — Taslak (F3/F5)

Sırayla, kollar serbestken:

1. Acil stop basılıyken enerji ver; servoların enerjisiz olduğunu doğrula. Bırak; Pi'nin durumu sunucuya bildirdiğini gör.
2. Bekçi: hareket yokken ve hareketin ortasında sunucu bağlantısını kes; robotun kontrollü durup konumu tuttuğunu, süre aşımında torkun kapandığını ve mıknatısın güvenli duruma geçtiğini doğrula.
3. Son kapı: sunucudan bilerek sınır dışı bir yörünge (açı, hız, ivme) gönder; Pi'nin hiç başlatmadığını ve `fault` bildirdiğini doğrula.
4. Sıcaklık, yük ve gerilim sınırlarını düşük ayarlayıp tetiklendiklerini doğrula; sonra gerçek değerlere geri al.

## 8. Sunucu kurulumu — Bekliyor (F4)

`compose.yaml` ile web, API, sandbox, ROS2 yığını ve kenar uç noktasının (TLS) kendi sunucuda kurulması; sonra buluta taşınabilir.
