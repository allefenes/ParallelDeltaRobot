# Güvenlik gereksinimleri ve izlenebilirlik

Her güvenlik gereksinimi en az bir otomatik testle kanıtlanır. Test plan risk tabanlıdır: kapsama yüzdesi bilgi amaçlıdır, asıl ölçüt bu tablodur. Gereksinim ancak ilgili katmanların hepsinde testi geçtiğinde "kanıtlandı" sayılır.

Katmanlar: **Ç** çekirdek (`core/`, F1), **S** sunucu 1. kapı (F3), **K** Pi kenarı son kapı (F3), **D** donanım kabul testi (F5, [kabul-testleri.md](kabul-testleri.md)).

| No  | Gereksinim                                                                                         | Katman  | Kanıtlayan testler                                                                                   | Durum        |
| --- | -------------------------------------------------------------------------------------------------- | ------- | ---------------------------------------------------------------------------------------------------- | ------------ |
| G1  | Motor açı limiti (−70° … +150°) dışındaki hiçbir açı servolara ulaşmaz                             | Ç, S, K | `Kinematics.MotorLimitRejected`, `test_limit_edges`, `test_check_point_agrees_with_limits`           | Ç ✔, S/K F3 |
| G2  | Rot başı yanal açısı 13°'yi aşan konum kabul edilmez                                               | Ç, S    | `Kinematics.RodTiltLimitRejected`, `test_check_point_agrees_with_limits`                             | Ç ✔, S F3   |
| G3  | Erişilemeyen hedef reddedilir, hareket başlamaz                                                    | Ç, S    | `Kinematics.UnreachablePointRejected`, `Kinematics.UnreachableReturnsEmpty`                          | Ç ✔, S F3   |
| G4  | NaN, sonsuz ya da bozuk veri motorlara ulaşmaz                                                     | Ç, K    | `Kinematics.NonFiniteInputRejected`, `test_non_finite_never_accepted`; F3: protokol ayrıştırıcı fuzz | Ç ✔, K F3   |
| G5  | Eklem hız ve ivme sınırları aşılamaz (aşan yörünge reddedilir)                                     | S, K    | F3                                                                                                   | F3           |
| G6  | Sunucu kalp atışı kesilirse robot hareketin ortasında bile en geç T_stop içinde durup konumu tutar | K       | F3 (hata enjeksiyonu)                                                                                | F3           |
| G7  | Kalp atışı T_off süresince gelmezse tork kapanır ve elektromıknatıs tanımlı güvenli duruma geçer   | K       | F3                                                                                                   | F3           |
| G8  | Kapıdan geçmeyen yörünge hiç başlamaz; neden sunucuya bildirilir                                   | K       | F3                                                                                                   | F3           |
| G9  | Sıcaklık, yük ya da gerilim sınırı aşılınca hareket durur                                          | K       | F3                                                                                                   | F3           |
| G10 | Seri hattı yalnız kenar servisi kullanır (tek sahip)                                               | K       | F3 (mimari test)                                                                                     | F3           |
| G11 | Kullanıcı kodu sandbox'ta ağa çıkamaz, kaynak sınırını aşamaz, dosya sistemine yazamaz             | S       | F4 (sandbox güvenlik testleri)                                                                       | F4           |
| G12 | Fiziksel acil stop, yazılımdan bağımsız olarak servo gücünü keser                                  | D       | F5 kabul testi                                                                                       | F5           |

**Durum:** 4 / 12 gereksinim çekirdek katmanında testle kanıtlandı (G1–G4); tam kanıt F3–F5'te tamamlanır.

Süre değerleri (T_stop, T_off) F3'te kenar servisiyle birlikte sabitlenir ve buraya yazılır.
