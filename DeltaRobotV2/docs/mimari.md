# Mimari

Bu belge hedef mimariyi anlatır; parçalar fazlar ilerledikçe hayata geçer ([yol-haritasi.md](yol-haritasi.md)).

**Temel karar (kullanıcı, 2026-11-12): ince ama güvenli Raspberry Pi kenarı, geri kalan her şey sunucuda.** Beyin sunucudadır; robot başındaki Pi yalnız hazır yörüngeyi kendi saatiyle oynatır, son güvenlik kapısını uygular ve bağlantı koparsa robotu güvenli duruma alır.

```
[Tarayıcı: editör, 3B ikiz, kamera]          [VS Code + Python istemcisi]
                 \                                   /
                  HTTPS / WebSocket (token ile)
                                 |
┌──────────────────────── SUNUCU (beyin) ─────────────────────────┐
│ web + API + rezervasyon/kiralama + iş kuyruğu                    │
│ kullanıcı kodu sandbox'ı (ağsız, kaynak sınırlı konteyner)       │
│ ROS2 Jazzy yığını:                                               │
│   1. kapı: tam süpervizör (çalışma alanı, çarpışma, görev mantığı)│
│   kinematik (delta_core), yörünge planlama, dijital ikiz          │
│   kenar köprüsü: zaman damgalı yörünge -> kenar protokolü         │
│ log ve telemetri arşivi                                          │
└───────────────────────────────┬─────────────────────────────────┘
        kenar protokolü (WebSocket + TLS); bağlantıyı Pi açar,
        robot tarafında gelen port yok
                                │
┌──────────────── RASPBERRY PI (ince, güvenli kenar) ─────────────┐
│ delta_edge (C++ servis, ROS'suz):                                │
│   yörünge tamponu: tüm yörüngeyi alır, yerel saatle 50–100 Hz    │
│   2. (son) kapı: eklem/hız/ivme/sıcaklık/yük/gerilim + kırpma    │
│   bekçi: kalp atışı koparsa dur-tut, gerekirse tork kapat,       │
│          elektromıknatısı tanımlı güvenli duruma al              │
│   geri bildirim: açı, sıcaklık, yük, gerilim -> sunucu           │
│   motor sürücüsü: AX-12A arka ucu (motordan bağımsız arayüz)     │
│ kamera: WebRTC ile doğrudan yayın                                │
└───────────────────────────────┬─────────────────────────────────┘
                 seri hat (yarım-dupleks)   fiziksel acil stop
                                │           (ağdan bağımsız, güç
                           3× servo         yolunda / Pi girişinde)
```

## Sorumluluk dağılımı

| Görev                                                                     | Sunucu              | Pi (`delta_edge`)   |
| ------------------------------------------------------------------------- | ------------------- | ------------------- |
| Web, API, kiralama, sandbox, iş kuyruğu                                   | ✔                  |                     |
| Kinematik, yörünge planlama, dijital ikiz                                 | ✔                  |                     |
| 1. kapı: çalışma alanı, çarpışma, görev mantığı, hız profili              | ✔                  |                     |
| Yörüngeyi yerel saatle oynatma (50–100 Hz)                                |                     | ✔                  |
| 2. kapı: eklem, hız, ivme, sıcaklık, yük, gerilim sınırları, değer kırpma |                     | ✔                  |
| Bekçi (kalp atışı) ve güvenli duruş                                       |                     | ✔                  |
| Fiziksel acil stop                                                        |                     | ✔ (donanım)        |
| Telemetri yayını                                                          | arşivler            | yayınlar            |
| Kamera                                                                    | aktarır (gerekirse) | WebRTC ile yayınlar |
| Log, telemetri arşivi                                                     | ✔                  |                     |

## İlkeler

1. **İki katmanlı güvenlik.** Sunucudaki tam süpervizör ilk kapıdır: çalışma alanı, küresel mafsal limiti (14°), çarpışma, görev mantığı, hız/ivme profili. Pi'deki hafif kapı son kapıdır: sunucu ne gönderirse göndersin, eklem/hız/ivme/sıcaklık/yük/gerilim sınırlarını aşan ya da sınır dışı değer içeren hiçbir komut servolara ulaşmaz. İki kapı aynı `config/robot.yaml` sınırlarını kullanır.
2. **İnternet üzerinden nokta nokta sürüş yok.** Sunucu, zaman damgalı tam yörüngeyi gönderir; Pi onu kendi saatiyle oynatır. Ağ gecikmesi ve titremesi hareketi etkilemez, yalnız yörüngenin başlamasını geciktirir.
3. **Bekçi.** Pi, sunucudan belirli aralıkla kalp atışı bekler. Kesilirse hareketin ortasında bile kontrollü durur ve konumu tutar; süre uzarsa torku kapatır ve elektromıknatısı tanımlı güvenli duruma alır.
4. **Ağdan bağımsız acil stop.** Fiziksel buton güç yolunu keser ve Pi'ye ayrıca bildirir; yazılım ya da ağ arızası onu etkilemez.
5. **Bağlantıyı Pi açar.** Pi, sunucuya TLS'li WebSocket ile dışarı doğru bağlanır; robotun bulunduğu ağda gelen port açılmaz.
6. **Simülasyon ile gerçek ayırt edilemez.** Mock ve dijital ikiz arka uçları aynı kenar protokolünü konuşan bir "sanal Pi" olarak çalışır; sunucu karşısında simülasyon mu gerçek robot mu olduğunu bilmez. F5'e kadar tüm zincir sanal Pi ile test edilir.
7. **Donanımın tek sahibi.** Seri hattı yalnız `delta_edge` kullanır.
8. **Kullanıcı kodu robotta çalışmaz.** Web editöründeki kod sunucuda ağsız, kaynak sınırlı bir konteynerde; VS Code'daki kod kullanıcının kendi bilgisayarında çalışır. İkisi de yalnız komut API'si üzerinden konuşur. Komutlar veridir (hedef konum, eklem açıları, zamanlı yörünge), doğrudan motor erişimi yoktur.
9. **Tek kinematik kaynağı.** İleri/ters kinematik, Jacobian ve limitler `core/` altındaki C++ kütüphanededir; sunucu, Python istemcisi (pybind11), web ikizi ve gerektiğinde Pi aynı kodu kullanır.
10. **Motordan bağımsız donanım katmanı.** AX-12A, `delta_edge` içindeki bir arka uçtur; yeniden kurulumda motor değişirse yalnız arka uç ve motor parametreleri değişir.
11. **Taşınabilir dağıtım.** Sunucu servisleri konteynerdir ve `compose.yaml` ile kalkar. Önce kendi sunucumuz, sonra bulut; buluta özgü bağımlılık yok.
12. **Çok dilli arayüz.** Metinler koda gömülmez; `i18n/locales/` katalogları kullanılır. Kaynak dil Türkçe, eksik çeviri Türkçeye düşer.

## Pi'de neden ROS2 değil, küçük bir C++ servisi?

| Seçenek                                               | Artı                                                                                                                                                 | Eksi                                                                                                     |
| ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **Pi'de ROS'suz C++ servis (`delta_edge`) — seçilen** | Küçük, gerçek zamana yakın döngü kolay; bağımlılık ve açılış süresi az; güvenlik kodu tek dosyada denetlenebilir; protokol açıkça tanımlı ve sürümlü | ROS araçları (rosbag, rviz) Pi'de doğrudan yok; köprü sunucuda yazılır                                   |
| Pi'de ROS2 + internet üzerinden DDS                   | ROS araçları her yerde                                                                                                                               | DDS keşfi ve QoS internette/NAT arkasında güvenilmez; güvenlik ve bağlantı yönetimi zor                  |
| Pi'de ROS2 + `rmw_zenoh`                              | DDS sorunlarını çözer, ROS uçtan uca                                                                                                                 | Pi'de tam ROS2 yığını; güvenlik kapısı ROS düğümleri arasında dağılır; kenarın "ince" olma hedefine ters |

Karar: Pi'de `delta_edge` (C++17, `delta_core` ile aynı depoda). ROS2 yığını sunucuda kalır; sunucudaki **kenar köprüsü** düğümü ROS2 yörünge mesajlarını kenar protokolüne çevirir ve telemetriyi ROS2 konularına yayımlar. ROS2'nin ileride ağ üzerinden uzanması gerekirse `rmw_zenoh` kullanılır, DDS kullanılmaz.

## Kenar protokolü (taslak, F3'te kesinleşir)

- Taşıma: WebSocket + TLS, istemci sertifikası ya da robot başına belirteç; bağlantıyı Pi açar.
- Mesajlar (sürüm alanlı JSON, gerekirse CBOR): `trajectory` (kimlik, başlangıç zamanı, örnekleme periyodu, eklem açıları dizisi), `heartbeat`, `stop`, `hold`, `torque`, `magnet`, `telemetry` (açı, sıcaklık, yük, gerilim, durum), `fault` (hangi sınır, hangi değer).
- Saat: Pi yerel monoton saatle oynatır; sunucu saatiyle eşleme yalnız kayıt içindir.
- Reddedilen yörünge: Pi, kapıyı geçmeyen yörüngeyi hiç başlatmaz ve nedenini `fault` ile bildirir.

## Kullanıcıya açılan kontrol seviyeleri

| Seviye | Örnek                                                 | Not                               |
| ------ | ----------------------------------------------------- | --------------------------------- |
| Yüksek | `move_to(x, y, z)`, `pick()`, `place()`               | Yeni başlayanlar için             |
| Orta   | eklem açıları, zamanlı yörüngeler                     | Kinematik derslerinin ödevleri    |
| Alt    | kullanıcı kendi ters kinematiğini yazar, açı gönderir | İki kapı yine her komutu denetler |

Her seviyede kullanıcı komutu sunucuda zaman damgalı bir yörüngeye dönüşür ve Pi'ye öyle gider.

## Teknoloji seçimleri

| Konu             | Seçim                                                                                  |
| ---------------- | -------------------------------------------------------------------------------------- |
| Sunucu           | Ubuntu 24.04 + ROS2 Jazzy (konteyner), C++17 / Python                                  |
| Robot kenarı     | Raspberry Pi (Ubuntu 24.04 ya da Raspberry Pi OS), `delta_edge` C++17 servisi, systemd |
| Kenar bağlantısı | WebSocket + TLS, Pi dışarı bağlanır                                                    |
| Kamera           | WebRTC, doğrudan Pi'den                                                                |
| Çekirdek         | Saf CMake C++ kütüphane (ROS bağımsız), GoogleTest                                     |
| Kullanıcı dili   | Python                                                                                 |
| Geliştirme       | Docker Desktop (WSL 2), Compose                                                        |
| CAD              | FreeCAD 1.1 Python betikleri                                                           |
