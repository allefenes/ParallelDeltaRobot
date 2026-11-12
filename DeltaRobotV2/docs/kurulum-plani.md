# Üretim ve kurulum planı

Robot yeniden üretilip kurulacaksa izlenecek sıra. Yaşayan bir belgedir: her faz kendi adımlarını ekler. Ölçüler ve malzemeler için kaynak [robot-girdileri.md](robot-girdileri.md); orada "Varsayım" ya da "Açık" işaretli değerler üretimden önce kesinleştirilmelidir. Parça adetleri, kütleleri ve tedarik bilgisi: [malzeme listesi (BOM)](../hardware/bom.md). Sistem mimarisi: [mimari.md](mimari.md).

Durum etiketleri: **Hazır** (adımlar yazılı), **Taslak** (içerik kısmen belli), **Bekliyor** (ilgili faz tamamlanınca yazılacak).

## 0. Ön koşullar — Taslak

- [ ] Motor seçimi kesinleşti (V1: 3× Dynamixel AX-12A; yeniden kurulumda değişebilir)
- [ ] Gövde malzemesi kesinleşti (V1: 7075 kaynaklı; 7075 kaynağa pek uygun değil, 6061/5083 değerlendirilecek)
- [ ] F0.5 CAD modelinden üretim çizimleri ve STL'ler çıkarıldı
- [ ] Malzeme listesindeki (hardware/bom.md) "TBD" tedarikçi ve fiyatlar dolduruldu

## 1. Parça üretimi — Taslak

| Parça                                    | Yöntem                         | Malzeme           | Not                                                                                                                         |
| ---------------------------------------- | ------------------------------ | ----------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Kısa kol ×3                              | Lazer kesim                    | 2 mm 7075 Al      | Motor ucunda artı delik, eklem ucunda Ø5                                                                                    |
| Tavan                                    | Lazer kesim                    | 5 mm Al           | Anahtar deliği biçimi; robot ucu küçük (R45), merkeze yakın 3 delik (R18)                                                   |
| Sütun                                    | Lazer kesim + kıvırma + kaynak | 5 mm Al           | D kesit: yarım silindir + düz kapak levhası                                                                                 |
| Taban                                    | CNC / lazer                    | 5 mm POM          |                                                                                                                             |
| Motor gövdesi (tek parça) ve 6 alt kapak | 3B baskı                       | PLA               | Plaka R84.7, her kolda 3 mm açıklık; motor kutuları ve yatak üst yarıları plakayla tek parça; alt kapaklar alttan vidalanır |
| Artı kesitli çıkış milleri ×3            | 3B baskı                       | PLA, %100 doluluk | Tüm boyu artı kesit; uçları Ø8 dairede                                                                                      |
| Uç platform                              | 3B baskı                       | PLA, %20 doluluk  | Dairesel R28 × 5 mm, 3 kulak (eksen r = 35); pimler orta düzlemde; 3 süs deliği; altta 2.5 mm mıknatıs cebi                 |
| Burçlar ×24                              | 3B baskı ya da torna           | PLA (varsayım)    | Boydan boya konik, Ø5 delik; 6 × 10 mm + 6 × 5 mm iç burç, 12 × 5 mm dış burç                                               |
| Uzun kollar ×6                           | M5 saplama kesimi              | Çelik             | 167 mm; her rot başına 10 mm girer, merkezden merkeze 201 mm                                                                |
| Pimler ×6                                | M5 saplama kesimi              | Çelik             | ~60 mm (istif 58 mm)                                                                                                        |

Hazır alınacaklar: 12× dişi M5 rot başı, 12× M3 ısıyla gömülen insert (Ø4.6 × 5.7), 6× 608ZZ rulman, 12× M5 fiber somun, 12× M3 × 20 vida (kapaklar), 3× M5 cıvata (gövde-tavan), elektromıknatıs (15 mm), 12 V güç kaynağı, Raspberry Pi 4B, haberleşme adaptörü, kamera.

## 2. Mekanik montaj — Taslak (F0.5)

Sıra F0.5 montaj modelinden ([cad/](../cad/README.md)) çıkarıldı; ölçüm yapılmış bir robotla doğrulanmadı.

1. POM tabana sütunu bağla; sütunun üstündeki tavanın yatay olduğunu kontrol et.
2. Motor gövdesini hazırla (tek parça baskı). Rulman yatağı üst yarılarındaki 12 cebe M3 ısıyla gömülen insertleri havyayla bastır: havya ~200–220 °C (PLA), insert dik ve yüzeyle aynı hizada; soğumadan oynatma. Bu adım montajdan önce yapılır.
3. Gövdeyi ters çevir. Motorları kutularına alttan yerleştir (kutu motorun dönmesini engeller). Artı kesitli mili göbeğe bağla; iki 608ZZ'yi mile geçirip gövdeyle tek parça olan yatak üst yarılarına alttan oturt.
4. Kısa kolu iki rulmanın arasında, artı deliğinden mile geçir (kol levhası üst plakadaki 3 mm açıklıkta kalır). Alt kapakları (yatakların alt yarısı) alttan tak ve her birini 2 × M3 vidayla alttan, başları aşağıda kalacak şekilde insertlere sık. Kol −70°'ye kadar kalkabilmeli (mekanik sınır ≈ −71.2°).
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
- **Donanım bekçisi (G13):** 12 V servo güç hattına acil stopla seri bir röle ya da lojik seviyeli N-MOSFET konur. Sürme ucu, yeniden tetiklenebilir monostable bir devreye (74HC123, RC ≈ 0.5 s; varsayım) bağlanır; tetik girişi Pi'nin bir GPIO çıkışıdır (`delta_edge` yaşam darbesi, döngü sağlıklıyken ~20 Hz). Darbe kesilirse çıkış düşer, servo gücü kesilir. Pi'nin kendi beslemesi bu hattan ayrıdır. Montajdan sonra kabul testi H13 ile süre ölçülür.
- Raspberry Pi beslemesi: 12 V → 5 V/3 A DC-DC dönüştürücü ya da ayrı adaptör (açık). Acil stop Pi'nin beslemesini kesmez; Pi telemetriyi ve bağlantıyı korur.
- Pi ↔ servo: yarım-dupleks TTL seri hat (Dynamixel arayüzü: U2D2 ya da 74LS241 tabanlı devre; açık).
- Elektromıknatıs: Pi GPIO'dan MOSFET ile anahtarlanır, serbest dönüş diyotu ile; varsayılan (Pi kapalı / bekçi tetik) durumu tanımlıdır (F3'te kararlaştırılır).

## 4. Servo yapılandırması — Hazır (F5 yazılım)

Araç: `delta_servo_tool` (depodaki `edge/`, Pi'de derlenir). Çıkış kodu 0 tamam, 1 haberleşme hatası, 2 kullanım hatası. Fabrika ayarlı AX-12A'ların hepsi kimlik 1, 1 Mbps'tir; bu yüzden **servolar hatta tek tek bağlanır**.

1. Yalnız 1. servoyu bağla: `delta_servo_tool --device /dev/ttyAMA0 --baud 1000000 scan 0 10` → kimlik 1 görünmeli.
2. 2. ve 3. servoyu sırayla tek başına bağlayıp kimlik ver: `delta_servo_tool set-id 1 2`, `delta_servo_tool set-id 1 3`. Araç yeni kimlik zaten yanıt veriyorsa reddeder ve değişikliği ping ile doğrular.
3. Üçü birlikte: `scan 0 10` → 1, 2, 3.
4. Haberleşme hızı 1 Mbps kalır (`set-baud` yalnız Pi'nin açabildiği hızları kabul eder; servo erişilemez hâle getirilemez).
5. Açı limitleri ve hız: elle yazılmaz; `delta_edge` ilk bağlantıda servo içindeki CW/CCW limitlerini `robot.yaml` eklem penceresine yazar (yalnız farklıysa; EEPROM), dönüş gecikmesi ve durum dönüş seviyesini denetler.
6. Ayarlar: [`edge/config/motor_ax12.yaml`](../edge/config/motor_ax12.yaml) (kimlikler, hız, `zero_tick`, `sign`, ölçek). Başka motor için yeni bir `motor:` bölümü ve sürücü arka ucu eklenir; eklem limitleri her zaman `robot.yaml`'dan gelir.

## 5. Robot bilgisayarı (Raspberry Pi kenarı) — Hazır (F5 yazılım; donanımda doğrulanmadı)

Pi yalnız kenar görevini yapar; ROS2 yığını sunucudadır ([mimari.md](mimari.md)).

1. İşletim sistemi: Raspberry Pi OS Lite (64 bit) ya da Ubuntu 24.04 Server (arm64); SSH anahtarla, parola girişi kapalı.
2. Seri port (1 Mbps için PL011): `/boot/firmware/config.txt` içine `enable_uart=1` ve `dtoverlay=disable-bt`; seri konsol kapatılır (`raspi-config` → Interface → Serial: konsol hayır, donanım evet). Aygıt `/dev/ttyAMA0`. USB adaptör (U2D2) kullanılırsa `/dev/ttyUSB0`. Yön (TX/RX) donanımda çözülür; tek telli hatta gönderilen baytlar geri geliyorsa `local_echo: true`.
3. Derleme (Pi üzerinde): `sudo apt install build-essential cmake ninja-build libboost-dev libssl-dev nlohmann-json3-dev libyaml-cpp-dev` sonra `cmake -S edge -B build/edge -G Ninja -DCMAKE_BUILD_TYPE=Release -DDELTA_EDGE_BUILD_TESTS=OFF && cmake --build build/edge`. İkililer: `delta_edge`, `delta_servo_tool`.
4. Servis kullanıcısı `delta` (`dialout` ve `gpio` grupları), dosyalar `/opt/delta_edge/` (ikili, `edge.yaml`, `motor_ax12.yaml`, `robot.yaml`), kimlik `/etc/delta_edge/` (CA sertifikası, robot belirteci; yalnız `delta` okur).
5. systemd birimi (`/etc/systemd/system/delta-edge.service`): `ExecStart=/opt/delta_edge/delta_edge`, ortam `DELTA_DRIVER=ax12`, `DELTA_SERIAL_DEVICE=/dev/ttyAMA0`, `DELTA_MOTOR_CONFIG=/opt/delta_edge/motor_ax12.yaml`, `DELTA_SERVER_URL=wss://<sunucu>:8443/edge`, `DELTA_CA_FILE=/etc/delta_edge/ca.crt`; belirteç `EnvironmentFile=/etc/delta_edge/token.env` içinde `DELTA_EDGE_TOKEN=...` (izin 600); `Restart=always`, `RestartSec=1`. Servis çökerse donanım bekçisi (G13) servo gücünü keser; systemd yeniden başlatınca kenar güvenli açılışla (TORQUE_OFF) başlar.
6. **Bağlantıyı Pi açar:** `delta_edge`, sunucuya TLS'li WebSocket ile dışarı doğru bağlanır; yönlendiricide gelen port açılmaz. Bağlantı koparsa yeniden dener.
7. Sınırlar `robot.yaml`'ın Pi'deki kopyasından okunur; `motor_ax12.yaml` model ya da açı aralığı `robot.yaml` ile uyuşmazsa servis başlamaz.
8. Kamera: WebRTC yayını — askıda (F5 donanım yarısı).

## 6. Kalibrasyon — Kısmen hazır (F5 yazılım)

1. **Motor sıfırı:** tork kapalıyken her kolu yatay konuma getir (θ = 0; açıölçer ya da şablon), `delta_servo_tool read <kimlik>` ile konum tikini oku ve `motor_ax12.yaml` içindeki `zero_tick`'e yaz (varsayılan 376, doğrulanmadı). Kol aşağı inerken tik artıyorsa `sign: +1`, azalıyorsa `-1`. Kabul testi H4 ile 10 tekrar, standart sapma.
2. **Tabla:** tabla merkezi robot ekseninde, hücre 20 mm (`robot.yaml task.board`); gerçek tablada dört köşe hücreye gidilip mıknatıs ucunun hücre merkezine uzaklığı ölçülür — askıda (donanım).
3. **Kamera:** askıda.

## 7. İlk enerji verme ve güvenlik kontrolleri — Taslak (F3/F5)

Sırayla, kollar serbestken:

1. Acil stop basılıyken enerji ver; servoların enerjisiz olduğunu doğrula. Bırak; Pi'nin durumu sunucuya bildirdiğini gör.
2. Bekçi: hareket yokken ve hareketin ortasında sunucu bağlantısını kes; robotun kontrollü durup konumu tuttuğunu, süre aşımında torkun kapandığını ve mıknatısın güvenli duruma geçtiğini doğrula.
3. Son kapı: sunucudan bilerek sınır dışı bir yörünge (açı, hız, ivme) gönder; Pi'nin hiç başlatmadığını ve `fault` bildirdiğini doğrula.
4. Sıcaklık, yük ve gerilim sınırlarını düşük ayarlayıp tetiklendiklerini doğrula; sonra gerçek değerlere geri al.

## 8. Sunucu kurulumu — Hazır (yerel)

Yerelde tamamen konteynerde çalışır; gerçek sunucu ve alan adı kullanıcı kararından sonra.

- Deneyim arayüzü (F6, simülasyon): `docker compose --profile demo up -d --build` → https://localhost:8080
- Tam yığın (ROS2 + sanal Pi + API + sandbox koşucusu): `docker build -f docker/sandbox/Dockerfile -t deltarobotv2-sandbox .` sonra `docker compose --profile sim up -d --build` → https://localhost:8000; uçtan uca testler `./tools/e2e.sh`, `./tools/e2e_f4.sh`
- Gerçek Pi bağlanacaksa sunucunun 8443 portu (kenar uç noktası) dışarı açılır ve gerçek sertifika kullanılır.

## F5 durumu: askıda (kısmen tamamlandı)

Kullanıcı kararı (2026-11-12): elektronik ve mekanik geliştirmeler bekler. Yazılım yarısı bitti: AX-12A arka ucu (Protokol 1.0, sahte servo hattıyla test), motor yapılandırması, servo ayar aracı, bu belgedeki 4–6 ve 8. adımlar. Askıda: 0–3. adımlardaki üretim, montaj ve kablolama; donanım bekçisi ve mıknatıs sürücüsü devresi; kutu ve kamera; 7. adımdaki ilk enerji verme ve [kabul testleri](kabul-testleri.md) (H1–H13).
