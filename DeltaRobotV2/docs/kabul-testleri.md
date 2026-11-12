# Donanım kabul testleri

F5'te gerçek robotla koşulacak testler. Sonuçlar datasheet'in "ölçüm" alanlarını doldurur ve [güvenlik gereksinimleri](guvenlik-gereksinimleri.md) tablosundaki D katmanını kapatır. Her test: hazırlık, adımlar, geçme ölçütü, kaydedilecek değer.

| No  | Test                  | Ölçüm / ölçüt                                                                                                                                                                     | Datasheet alanı         |
| --- | --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| H1  | Acil stop (G12)       | Buton basılıyken servolar enerjisiz; bırakınca Pi durumu sunucuya bildirir                                                                                                        | Güvenlik                |
| H2  | Bekçi (G6, G7)        | Hareket ortasında ağ kesilir; duruş süresi ≤ T_stop, tork kapanma ≤ T_off, mıknatıs güvenli durumda                                                                               | Güvenlik                |
| H3  | Son kapı (G1, G5, G8) | Sunucudan bilerek sınır dışı yörünge: hiç başlamaz, `fault` gelir                                                                                                                 | Güvenlik                |
| H4  | Sıfır kalibrasyonu    | Üç motorun sıfır ofseti; 10 tekrar, standart sapma                                                                                                                                | Kalibrasyon             |
| H5  | Tekrarlanabilirlik    | 5 noktaya 30'ar gidiş, kadranlı saat / kamera ile; ISO 9283 benzeri                                                                                                               | Tekrarlanabilirlik (mm) |
| H6  | Mutlak doğruluk       | Tabla ızgarasında 9 nokta, komut – ölçüm farkı                                                                                                                                    | Doğruluk (mm)           |
| H7  | Boşluk (backlash)     | Her eksende yön değiştirme farkı                                                                                                                                                  | Boşluk (°, mm)          |
| H8  | Hız ve çevrim süresi  | 25/100/25 mm küçültülmüş pick-and-place çevrimi                                                                                                                                   | Çevrim süresi (s)       |
| H9  | Taşıma kapasitesi     | Mıknatıs tutma kuvveti ve artan yükle hız düşümü                                                                                                                                  | Faydalı yük (g)         |
| H10 | Isınma                | 30 dk tic-tac-toe döngüsü; servo sıcaklıkları                                                                                                                                     | Görev döngüsü           |
| H11 | Elle hareket          | Enerjisiz uç işlevci çalışma alanında takılmadan gezer (V1 nitel özelliği)                                                                                                        | Nitel                   |
| H12 | Tic-tac-toe           | 20 tam oyun; yerleştirme hatası, kaçırılan taş sayısı                                                                                                                             | Senaryo metrikleri      |
| H13 | Donanım bekçisi (G13) | `delta_edge` süreci SIGKILL ile öldürülür ve ayrıca Pi'nin güç kablosu çekilir: servo gücünün kesilme süresi osiloskopla ölçülür, ≤ 0.5 s; servolar enerjisiz, elle oynatılabilir | Güvenlik                |

Durum: **askıda** (F5 donanım yarısı, kullanıcı kararı 2026-11-12). Yazılım tarafı hazır: AX-12A arka ucu ve `delta_servo_tool` sahte servo hattıyla test edildi (kenar testleri), ilk enerji vermeden önce aşağıdaki varsayımlar doğrulanır.

## Ön doğrulamalar (AX-12A arka ucu, H1'den önce)

| No  | Doğrulama                    | Ölçüt                                                                     | Varsayılan (doğrulanmadı)                   |
| --- | ---------------------------- | ------------------------------------------------------------------------- | ------------------------------------------- |
| S1  | Seri aygıt ve hız            | `delta_servo_tool scan 0 10` üç servoyu 1 Mbps'te bulur                   | `/dev/ttyAMA0` (PL011, `disable-bt`)        |
| S2  | Yön denetimi (TX/RX)         | Yankı yok ya da `local_echo` ayarı doğru; 1000 okumada zaman aşımı yok    | Donanımda (U2D2 / otomatik yön tamponu)     |
| S3  | Hat zamanlaması              | 3 servo okuma + SYNC_WRITE döngüsü 10 ms'den kısa                         | `return_delay_us` 100, `reply_timeout_ms` 5 |
| S4  | Sıfır ve yön                 | Kol yatayken okunan tik `zero_tick`; aşağı inince tik artıyor (`sign` +1) | `zero_tick` 376, `sign` +1 (üç kol)         |
| S5  | Tork kapalıyken hedef yazımı | Tork kapalıyken hedef gönderilmez; servo kendiliğinden tork almaz         | Sürücü bu durumda yazmaz                    |
| S6  | Limit dışında başlangıç      | Kol pencere dışındayken açılış `ok=false`, tork açılmaz (güvenli taraf)   | Servo açı limiti hatası                     |
| S7  | Yük ölçeği ve işareti        | Elle yüklenen kolun yük işareti ve büyüklüğü telemetride doğru            | %0.1 / birim, bit 10 = CW                   |
| S8  | Mıknatıs çıkışı              | Pi kapalıyken ve servis çökünce mıknatıs kapalı (çekme direnci)           | GPIO pini açık karar                        |
