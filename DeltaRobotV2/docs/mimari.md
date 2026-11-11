# Mimari

Bu belge hedef mimariyi anlatır; parçalar fazlar ilerledikçe hayata geçer ([yol-haritasi.md](yol-haritasi.md)).

```
[Tarayıcı: editör, 3B ikiz, kamera]      [VS Code + Python istemcisi]
                 \                              /
                  HTTPS / WebSocket (token ile)
                               |
        [Sunucu: web + API + iş kuyruğu + sandbox + rezervasyon]
                               |   robot dışarıya bağlanır, port açılmaz
                     [Robot bilgisayarı: ROS2 Jazzy]
                       ├─ güvenlik süpervizörü   <- her komut buradan geçer
                       ├─ yörünge yürütücü + durum makinesi
                       └─ donanım arayüzü: AX-12A | mock / dijital ikiz
```

## İlkeler

1. **Tek kapı.** Donanıma giden her komut güvenlik süpervizöründen geçer: motor limitleri, küresel mafsal limiti (14°), çalışma alanı zarfı, hız ve ivme sınırları, sıcaklık ve yük bekçisi, acil stop, bağlantı kopunca güvenli duruş. Hiçbir katman bu kontrolü atlayamaz.
2. **Donanımın tek sahibi.** Seri hattı yalnız donanım arayüzü kullanır; diğer her şey ROS2 arayüzlerinden konuşur.
3. **Kullanıcı kodu robotta çalışmaz.** Web editöründeki kod sunucuda ağsız, kaynak sınırlı bir konteynerde; VS Code'daki kod kullanıcının kendi bilgisayarında çalışır. İkisi de yalnız komut API'si üzerinden konuşur. Komutlar veridir (hedef konum, eklem açıları, zamanlı yörünge), doğrudan motor erişimi yoktur.
4. **Tek kinematik kaynağı.** İleri/ters kinematik, Jacobian ve limitler `core/` altındaki C++ kütüphanededir. ROS2 düğümleri, Python istemcisi (pybind11) ve web ikizi aynı hesabı kullanır; testler bu kütüphaneyi V1 Python koduyla çapraz doğrular.
5. **Motordan bağımsız donanım katmanı.** AX-12A bir arka uçtur; yeniden kurulumda motor değişirse yalnız arka uç ve motor parametreleri değişir.
6. **Taşınabilir dağıtım.** Her servis konteynerdir ve `compose.yaml` ile kalkar. Önce kendi sunucumuz, sonra bulut; buluta özgü bağımlılık yok.
7. **Çok dilli arayüz.** Metinler koda gömülmez; `i18n/locales/` katalogları kullanılır. Kaynak dil Türkçe, eksik çeviri Türkçeye düşer.

## Kullanıcıya açılan kontrol seviyeleri

| Seviye | Örnek | Not |
|---|---|---|
| Yüksek | `move_to(x, y, z)`, `pick()`, `place()` | Yeni başlayanlar için |
| Orta | eklem açıları, zamanlı yörüngeler | Kinematik derslerinin ödevleri |
| Alt | kullanıcı kendi ters kinematiğini yazar, açı gönderir | Süpervizör yine her komutu denetler |

## Teknoloji seçimleri

| Konu | Seçim |
|---|---|
| Robot tarafı | Ubuntu 24.04 + ROS2 Jazzy, C++17 |
| Çekirdek | Saf CMake C++ kütüphane (ROS bağımsız), GoogleTest |
| Kullanıcı dili | Python |
| Geliştirme | Docker Desktop (WSL 2), Compose |
| CAD | FreeCAD 1.1 Python betikleri |
