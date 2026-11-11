# i18n

Arayüz metinleri `locales/<dil>.json` dosyalarında düz anahtar → metin olarak tutulur.

- `tr.json` kaynak dildir; her anahtar önce buraya eklenir.
- Diğer diller (`en.json`) yalnız `tr.json`'daki anahtarları içerebilir. Eksik çeviri hata değildir, arayüz Türkçeye düşer; denetim bunu uyarı olarak raporlar.
- Yer tutucular `{ad}` biçimindedir ve çevirilerde aynı adlarla bulunmalıdır.
- Anahtarlar küçük harf, nokta ile ayrılmış: `alan.alt_alan.ad`.

Denetim: `python3 tools/check_i18n.py` (CI'da otomatik çalışır).
