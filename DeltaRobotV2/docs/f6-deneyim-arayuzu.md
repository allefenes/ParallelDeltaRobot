# F6 tasarımı: tek sayfalık deneyim arayüzü

Kullanıcı kararı (2026-11-12, iki adımda):

1. Elektronik ve mekanik geliştirmeler şimdilik bekler; F5'in yazılım yarısı yapılıp askıya alınır.
2. Nihai sitede üyelik, ödeme, kiralama yoktur. Tek sayfalık bir **deneyim arayüzü** vardır: robot simülasyonda (dijital ikiz) çalışır; otomatik modda kendi kendine tic-tac-toe oynar, manuel modda ziyaretçi motor açılarını ve hedef konumu girerek robotu 3B ortamda sürer.

Önceki "simülasyon kiralama sitesi" tasarımı (hesaplar, planlar, kota, ödeme soyutlaması, hukuki sayfalar) bu kararla iptal edildi. O tasarımla yazılmaya başlanan `site/` kodu hiç kaydedilmedi ve çalışma ağacından kaldırıldı; API'deki site doğrulaması (`SiteAuth`), kota ve kullanım kaydı da kaldırıldı.

## Sayfa

- Büyük 3B görünüm: CAD mesh'leriyle robot, tic-tac-toe tablası ve taşlar; durum rozeti, mıknatıs göstergesi; "Canlı robot: yakında" tek satır.
- **Otomatik mod:** Başlat / Durdur / Sıfırla. Robot iki minimaks oyuncuyla (eşit hamleler arasından rastgele seçerek) kendi kendine oynar; taşları gerçekten al-taşı-bırak hareketiyle taşır. Sıra, kazanan, hamle listesi ve küçük tabla şeması gösterilir. Oyun kazananla ya da 20 hamle sınırıyla biter.
- **Manuel mod:** üç motor açısı kaydırıcısı (ileri kinematik önizlemesi: XYZ), XYZ girişleri (ters kinematik önizlemesi: açılar), "Git" ile yumuşak hareket (yörünge yürütücüsü, ışınlanma yok), iki yön canlı durumla eşlenir. Limit dışı hedefler aynı güvenlik kapılarıyla reddedilir (G1 motor, G2 rot başı, G3 erişim, G14 zemin) ve Türkçe nedenle gösterilir. Dur her zaman etkin.

## Arka uç

- `DELTA_API_MODE=sim`: API süreç içi simülasyon kullanır (`api/delta_api/sim_backend.py`): ROS yığınıyla aynı kinematik (`delta_core`), planlayıcı, 1. güvenlik kapısı (`safety.validate`) ve tabla ikizi (`board_game.py`). Pi'deki son kapı ve bekçi simülasyonda yoktur.
- Her ziyaretçi `POST /api/v1/session` ile anonim, yalıtılmış bir oturum alır (kendi robotu ve tablası).
- Kötüye kullanım korumaları: IP başına dakikada 10 oturum, en çok 50 eşzamanlı oturum, oturum başına saniyede 20 istek, 10 dakika boşta kalan oturum silinir (açık telemetri akışı varken silinmez). Değerler ortam değişkeniyle ayarlanır.
- Sözleşme: [api.md](api.md) "F6 deneyim arayüzü" bölümü.
- Dağıtım: `docker compose --profile demo up -d` → https://localhost:8080 (yerel, kendinden imzalı sertifika). Gerçek sunucu ve alan adı kullanıcı kararından sonra.
- Sandbox ve pip istemcisi arka uçta kalır (F4); bu sayfanın parçası değildir.

## Testler (risk tabanlı)

| Alan                                     | Testler                                                                                                                                    |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Oturum ve kötüye kullanım                | anonim oturum zorunlu, ziyaretçiler arası yalıtım, IP sınırı, kapasite, istek sınırı, boşta silme, ziyaretçiler arası iş erişimi (IDOR)    |
| Manuel mod                               | FK/IK önizleme gidiş-dönüş, ret kodları (G1, G2, G3, G14), eklem uzayı hareketinin zaman alması (ışınlanma yok), dur → HOLDING             |
| Otomatik mod                             | oyun sonuna kadar oynanır, taş ikizi kurallarla birebir uyar, al/bırak hatasız; oyun sürerken elle komut reddi; dur oyunu keser, sıfırlama |
| Arayüz uçtan uca (Playwright, konteyner) | kaydırıcı → robot pozu, IK girişi → açılar, limit reddi mesajı, otomatik oyunun bitmesi; iki modun ekran görüntüsü                         |
