# F6 tasarımı: simülasyon kiralama sitesi

Kullanıcı kararı (2026-11-12): site şimdilik yalnız **simülasyon hizmetini** satar: dijital ikiz üzerinde uzaktan kinematik laboratuvarı (web editörü ya da VS Code + pip istemcisi → sandbox → simülasyon). Fiziksel robot olmadığı için canlı robot kiralama sitede **"Yakında"** olarak gösterilir, açıklama ve bekleme listesi formuyla. Dağıtım yalnız yerel konteyner; gerçek sunucu, alan adı ve TLS kullanıcının sunucu kararından sonra.

## 1. Ürün

| Bölüm                             | İçerik                                                                                                                                                         |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Simülasyon laboratuvarı (satılan) | Web editörü veya VS Code'dan Python; komutlar gerçek robotla aynı API ve aynı güvenlik kapılarından (G1–G5, G14) geçer; 3B ikiz, telemetri, tic-tac-toe görevi |
| Canlı robot (yakında)             | Açıklama: aynı kod gerçek robotta çalışacak; bekleme listesi (e-posta, isteğe bağlı kurum/kullanım amacı); KVKK açık rızası ayrı onay kutusu                   |
| Belgeler                          | Başlangıç, istemci kurulumu, API başvurusu (docs/api.md'den), güvenlik kapıları ve ret nedenleri, tic-tac-toe öğreticisi                                       |

## 2. Mimari

```
tarayıcı ──HTTPS──> site (FastAPI + Jinja2 şablonları, oturum çerezi)  ──> db (PostgreSQL)
                         │  hesap, plan, kota, kullanım, ödeme olayları
pip istemcisi ─HTTPS─> api (F4) ── belirteç doğrulama + kota sorgusu ──> site /internal (iç ağ)
                         │
                         └── iş -> sim işçisi havuzu (kullanıcı başına yalıtılmış simülasyon)
```

- **Simülasyon işçileri:** Kiralama simülasyonda tek robot kısıtı yoktur; her iş kendi simülasyonunu alır. `SimBackend` (API içinde, süreç içi): `delta_core_py` kinematiği + ROS yığınındaki saf modüller (`planning.py`, `safety.py` 1. kapı, `board_game.py` ikizi). Böylece kullanıcı aynı ret nedenlerini görür, ROS yığını kullanıcı başına çoğaltılmaz. Eşzamanlı iş sayısı işçi havuzuyla sınırlı (yapılandırılabilir). Tam ROS + sanal Pi yığını tek kopya olarak "gerçeğe en yakın" demo ve canlı robot hazırlığı için kalır.
- **Kimlik:** e-posta + parola (argon2id), doğrulama e-postası (yerelde dosyaya yazılır), parola sıfırlama; oturum çerezi (HttpOnly, Secure, SameSite=Lax) + CSRF belirteci. Kullanıcı başına API belirteçleri (adlandırılmış, iptal edilebilir, veritabanında yalnız özet/hash). F4 API'si belirteci site üzerinden doğrular (`Tokens` arayüzünün veritabanı gerçeklemesi).
- **Roller:** `user`, `admin`. Yönetici görünümü: kullanıcılar, planlar, kullanım (gün/kullanıcı), ödeme olayları, bekleme listesi; salt okuma + plan atama.
- **Ödeme soyutlaması:** `PaymentProvider` arayüzü: `create_checkout(user, plan) -> redirect_url`, `verify_webhook(headers, body) -> Event`, `cancel_subscription(...)`. Gerçeklemeler: `FakeProvider` (test modu, yerel ödeme sayfası taklidi) ve iskelet `IyzicoProvider`, `PayTRProvider` (sandbox uç noktaları, imza doğrulama; anahtarlar ortamdan; varsayılan kapalı). Sağlayıcı yapılandırmayla seçilir; hiçbiri koda gömülmez. Not: Stripe Türkiye'deki satıcıları kabul etmiyor.
- **Webhook güvenliği:** imza doğrulama, olay kimliğiyle tekrar (idempotency) koruması, zaman damgası penceresi, tutar/plan eşleşmesi; ödeme durumu yalnız webhook ile değişir (dönüş sayfası durumu değiştirmez).
- **Dağıtım:** compose profili `site`: `site`, `db`, mevcut `api` + `runner` (sim modu). Yerel TLS (F4 sertifikaları). Gerçek alan adı yok.

## 3. Fiyatlandırma önerisi (karar kullanıcıda)

Ölçü birimi: **simülasyon dakikası** = sandbox işinin duvar saati süresi (yuvarlama saniye düzeyinde, aylık toplam). Web editöründe elle sürme ve telemetri izleme ücretsiz; maliyet sandbox işlemcisinde.

| Plan           | Aylık sim. dakikası         | Eşzamanlı iş  | İş başına en uzun | Fiyat (yer tutucu)          |
| -------------- | --------------------------- | ------------- | ----------------- | --------------------------- |
| Ücretsiz       | 60                          | 1             | 2 dk              | 0                           |
| Öğrenci / Hobi | 600                         | 1             | 5 dk              | `{FIYAT_OGRENCI}` ₺/ay      |
| Pro            | 3 000                       | 3             | 10 dk             | `{FIYAT_PRO}` ₺/ay          |
| Sınıf / Kurum  | koltuk başına 600           | koltuk sayısı | 5 dk              | `{FIYAT_KURUM}` ₺/koltuk/ay |
| Ek paket       | +500 dakika (ay sonu biter) | —             | —                 | `{FIYAT_PAKET}` ₺           |

Gerekçe: Simülasyon tek robot gibi özel ve saatlik değil, paylaşılabilir; maliyeti işlemci zamanıdır. Saatlik slot yerine kota + abonelik, öğrenci/sınıf kullanımı için öngörülebilir fiyat verir. Canlı robot geldiğinde ayrı, saatlik ve özel (rezervasyonlu) ürün olur.

## 4. Kotalar ve ölçüm

- Her iş başlarken kota denetlenir (kalan dakika, eşzamanlı iş, iş başına süre üst sınırı plan değerinden; sandbox duvar saati sınırı ≤ plan sınırı).
- İş bitince kullanım kaydı: kullanıcı, iş, başlangıç, süre, sonuç. Ay sınırı Europe/Istanbul saatine göre.
- Kota aşımı: yeni iş `402 {"error": "quota_exceeded"}`; çalışan iş süresi dolunca durdurulur.
- Hız sınırlama: oturum açma, kayıt, parola sıfırlama, bekleme listesi ve API uç noktalarına IP + hesap başına.

## 5. Sayfalar (Türkçe, i18n ile İngilizceye hazır)

Ana sayfa, Nasıl çalışır, Belgeler, Fiyatlar, Canlı robot: yakında (bekleme listesi), Giriş / Kayıt / Parola sıfırlama, Hesabım (plan, kullanım grafiği, API belirteçleri), Laboratuvar (F4 web arayüzü, oturumla), Yönetici, Hukuki: Kullanım Koşulları, KVKK Aydınlatma Metni, Gizlilik Politikası, Çerez Politikası. Hukuki sayfaların hepsi **"TASLAK: hukuki inceleme gerekli"** bandıyla yer tutucudur.

## 6. Test planı (risk tabanlı, F1–F4 ile aynı ilkeler)

| Alan              | Testler                                                                                                                                         |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Kimlik            | kayıt/giriş/çıkış, parola özeti, oturum süresi, CSRF, oturum sabitleme, e-posta doğrulama, parola sıfırlama belirteci tek kullanımlık ve süreli |
| Yetkilendirme     | kullanıcı başkasının işine/belirtecine/kullanımına erişemez (IDOR), yönetici uçları yalnız admin, iptal edilen belirteç API'de reddedilir       |
| Kota              | sınırda kabul/ret, eşzamanlı iş, ay devri, iş süresi kesme                                                                                      |
| Ödeme (test modu) | webhook imzası, tekrar olay, yanlış tutar/plan, bilinmeyen kullanıcı, sıra dışı olaylar; dönüş sayfası durumu değiştirmez                       |
| OWASP temel       | SQL enjeksiyonu (parametreli sorgu + fuzz), XSS (şablon kaçışı, CSP), açık yönlendirme, hız sınırı, güvenlik başlıkları, çerez bayrakları       |
| Uçtan uca         | kayıt → plan → belirteç → pip istemcisiyle simülasyon işi → kullanım kaydı → yönetici görünümü                                                  |

## 7. Kullanıcıdan beklenen kararlar

Fiyatlar, ödeme sağlayıcısı (iyzico / PayTR), sunucu ve alan adı, e-posta gönderim hizmeti, hukuki metinler, şirket/fatura bilgileri. Hepsi yapılandırma ya da yer tutucu ile bekletilir; geliştirme bunlara bağlı değildir.

## 8. Site ↔ API iç sözleşmesi (iç ağ, `X-Internal-Secret` başlığı = `DELTA_INTERNAL_SECRET`)

| Yöntem | Yol (site)                   | Gövde                                                                                         | Yanıt                                                                                                                                                                        |
| ------ | ---------------------------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| POST   | `/internal/v1/tokens/verify` | `{"token": str}`                                                                              | `200 {"user_id": int, "name": str, "role": "user" \| "admin", "plan": {"id": str, "max_concurrent_jobs": int, "max_job_s": int, "remaining_s": int}}`; geçersiz/iptal: `401` |
| POST   | `/internal/v1/usage`         | `{"user_id": int, "job_id": str, "started_at": ISO-8601, "duration_s": float, "status": str}` | `200 {"ok": true, "remaining_s": int}`; aynı `job_id` ikinci kez: `200` (idempotent, ikinci kez sayılmaz)                                                                    |

- API, belirteç doğrulama sonucunu en çok 30 s önbelleğe alır; iptal edilen belirteç en geç 30 s içinde reddedilir.
- API iş başlatmadan önce `remaining_s > 0`, eşzamanlı iş sayısı < `max_concurrent_jobs` denetler; sandbox duvar saati sınırı `min(max_job_s, remaining_s, koşucu sınırı)`.
- API kota aşımında `402 {"error": "quota_exceeded", "message": ...}` döner (F4 sözleşmesine eklenir).
- Site çalışmıyorsa API yeni işi reddeder (`503 robot_unavailable` değil, `503 {"error": "auth_unavailable"}`); güvenli tarafta kalır.
- `DELTA_API_MODE=sim` iken her iş kendi `SimBackend` örneğini alır (kontrol kilidi yok, işler paralel); `robot` modunda F4 davranışı (tek robot, kilit) aynen kalır.
