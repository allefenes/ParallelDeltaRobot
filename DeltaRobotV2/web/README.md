# web/ — tarayıcı arayüzü (F4)

Derleme adımı olmayan tek sayfa uygulama. API bu klasörü `/` altında statik sunar; sözleşme [`docs/api.md`](../docs/api.md).

## Dosyalar

| Yol                     | İçerik                                                                         |
| ----------------------- | ------------------------------------------------------------------------------ |
| `index.html`            | Sayfa iskeleti, import map (three.js 0.160.0), CodeMirror 5.65.16 (jsDelivr)   |
| `css/style.css`         | Düzen (1280 px'de üç sütun, telefonda tek sütun), açık/koyu tema               |
| `js/main.js`            | Giriş, telemetri WS, elle sürme, kod editörü + iş konsolu                      |
| `js/api.js`             | REST (Bearer) ve WS (`?token=`) yardımcıları; belirteç `localStorage`'da       |
| `js/i18n.js`            | `/i18n/tr.json` kataloğu; eksik anahtar anahtarın kendisi olarak görünür       |
| `js/twin.js`            | Dijital ikiz: CAD mesh'leri telemetrideki açılar ve P ile pozlanır             |
| `examples/baslangic.py` | Editördeki başlangıç örneği (`delta_robot` istemcisi)                          |
| `dev/mock_server.py`    | Sahte API (yalnız standart kütüphane): statik dosyalar + REST + WS             |
| `tests/`                | JS çalıştırmadan denetimler (i18n anahtarları, sabit CDN sürümleri, sahte API) |

Tüm görünür metinler `i18n/locales/tr.json`'daki `web.*` ve `robot.state.*` anahtarlarından gelir.

## Dijital ikiz

Bağ çerçeveleri `cad/README.md` ve `delta_server/frames.py` ile aynıdır: `bicep_i` = Rz(a_i)·Ry(θ_i) A_i'de; `forearm_i_a/b` üst küre merkezi B_i ± 15·t_i'den alt küre C_i ± 15·t_i'ye; `platform` P'de. Mesh yüklenemezse aynı çerçevede basit kutu/çubuk/disk çizilir. Mavi silindir `GET /robot` çalışma alanıdır; kırmızı küre mıknatıs açık demektir.

## Sahte API ile deneme

```bash
# DeltaRobotV2/ kökünden (Git Bash)
MSYS_NO_PATHCONV=1 docker run --rm --name deltarobotv2-webmock -p 127.0.0.1:8765:8765 \
  -v "$(cygpath -w "$PWD"):/workspace" -w /workspace deltarobotv2-dev:latest \
  python3 web/dev/mock_server.py --host 0.0.0.0 --port 8765
```

Tarayıcıda `http://localhost:8765/`, belirteç `dev-token`. Sahte sunucu kullanıcı kodunu çalıştırmaz; başlangıç örneğindeki kalıpları küçük bir AST yorumlayıcısıyla taklit eder.

Testler: `MSYS_NO_PATHCONV=1 docker compose run --rm dev python3 -m pytest -p no:cacheprovider web/tests`

Ekran görüntüsü: [`screenshots/ui.png`](screenshots/ui.png)
