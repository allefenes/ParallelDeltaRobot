# web/ — deneyim arayüzü (F6)

Derleme adımı olmayan, üyeliksiz tek sayfa: ziyaretçi açılışta anonim simülasyon oturumu alır (`POST /api/v1/session`, belirteç bellekte/sessionStorage'da, 401'de sessizce yenilenir) ve sunucudaki dijital ikizi izler ve sürer. **Otomatik** sekmesi: robot kendi kendine kaydırmalı tic-tac-toe oynar (Başlat/Durdur/Sıfırla, durum, sıra, sonuç, hamle listesi). **Manuel** sekmesi: motor açısı kaydırıcıları (FK önizleme, `/move_joints`) ve XYZ girişleri (IK önizleme, `/move`); iki grup hareketten sonra canlı pozu izler. Sözleşme [`docs/api.md`](../docs/api.md) ("F6 deneyim arayüzü").

## Dosyalar

| Yol                     | İçerik                                                                                  |
| ----------------------- | --------------------------------------------------------------------------------------- |
| `index.html`            | Sayfa iskeleti (ikiz + iki sekme), import map (three.js 0.160.0, jsDelivr)              |
| `css/style.css`         | Düzen (masaüstünde ikiz + panel, 900 px altı tek sütun), açık/koyu tema                 |
| `js/main.js`            | Oturum, telemetri WS, tabla yoklama (~4 Hz), otomatik ve manuel mod, Dur                |
| `js/api.js`             | REST (Bearer) ve WS (`?token=`) yardımcıları, anonim oturum ve 401 yenileme             |
| `js/i18n.js`            | `/i18n/<dil>.json` kataloğu (`?lang=en`); eksik anahtar anahtarın kendisi görünür       |
| `js/twin.js`            | Dijital ikiz: CAD mesh'leri, tabla + taşlar + hücre adları; `window.__twinPose` kancası |
| `examples/baslangic.py` | F4 kod editörü örneği (bu sayfa göstermez; istemci belgesi için korunur)                |
| `dev/mock_server.py`    | Sahte API (standart kütüphane): F6 oturumları, FK/IK + 1. kapı, otomatik oyun           |
| `tests/`                | JS çalıştırmadan denetimler (i18n, sabit CDN, sayfa yapısı, sahte API)                  |

Hücre adları: sütun A–C soldan sağa (−X → +X), satır 1–3 +Y'den −Y'ye; `idx = satır·3 + sütun` → A1 = 0, B2 = 4, C3 = 8. X 1. satırda, O 3. satırda başlar.

Uçtan uca testler: [`tests/ui/`](../tests/ui/run.sh) (Playwright, konteynerde; varsayılan sahte API, `UI_BASE_URL` ile gerçek API).

Tüm görünür metinler `i18n/locales/tr.json`'daki (çevirisi `en.json`) `web.*` ve `robot.state.*` anahtarlarından gelir.

## Dijital ikiz

Bağ çerçeveleri `cad/README.md` ve `delta_server/frames.py` ile aynıdır: `bicep_i` = Rz(a_i)·Ry(θ_i) A_i'de; `forearm_i_a/b` üst küre merkezi B_i ± 15·t_i'den alt küre C_i ± 15·t_i'ye; `platform` P'de. Mesh yüklenemezse aynı çerçevede basit kutu/çubuk/disk çizilir. Mavi silindir `GET /robot` çalışma alanıdır; kırmızı küre mıknatıs açık demektir.

## Sahte API ile deneme

```bash
# DeltaRobotV2/ kökünden (Git Bash)
MSYS_NO_PATHCONV=1 docker run --rm --name deltarobotv2-webmock -p 127.0.0.1:8765:8765 \
  -v "$(cygpath -w "$PWD"):/workspace" -w /workspace deltarobotv2-dev:latest \
  python3 web/dev/mock_server.py --host 0.0.0.0 --port 8765
```

Tarayıcıda `http://localhost:8765/` (`#otomatik` / `#manuel`). Seçenekler: `--speed` (hareket hızı çarpanı), `--sessions-per-ip`, `--max-sessions`, `--idle-timeout`, `--max-moves`. Sahte sunucu kullanıcı kodunu çalıştırmaz; F4 işlerini küçük bir AST yorumlayıcısıyla taklit eder.

Testler: `MSYS_NO_PATHCONV=1 docker compose run --rm dev python3 -m pytest -p no:cacheprovider web/tests`

Ekran görüntüleri (Playwright, 1280×800): [`screenshots/otomatik.png`](screenshots/otomatik.png), [`screenshots/manuel.png`](screenshots/manuel.png)
