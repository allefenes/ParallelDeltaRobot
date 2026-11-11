# CAD (F0.5)

Robotun parametrik 3B modeli. Bütün parçalar FreeCAD 1.1 Python betikleriyle üretilir; ölçüler yalnız [config/robot.yaml](../config/robot.yaml) dosyasından okunur. Kaynağı "varsayim" olan değerler orada işaretlidir; ölçüm ya da kullanıcı bilgisiyle güncellenince model tek komutla yeniden üretilir.

## Çalıştırma

FreeCAD konteynerde olmadığı için betikler Windows'ta yerel FreeCAD ile çalışır (`DeltaRobotV2/` içinden, Git Bash):

```bash
./tools/cad.sh build
```

```bash
./tools/cad.sh render
```

`build` başsız çalışır (~1 dk; montaj pozu ve `check_poses` için çakışma kontrolü dahil). `render` FreeCAD arayüzünü birkaç saniye açar; montaj görsellerini (`docs/img/cad/`) ve parça önizlemelerini (`docs/img/cad/parcalar/`) 8 bit RGB PNG olarak kaydeder ve kapanır. Bir seferde tek FreeCAD süreci çalıştırılır.

## Dosyalar

| Dosya                      | Görev                                                                                |
| -------------------------- | ------------------------------------------------------------------------------------ |
| `lib/params.py`            | `config/robot.yaml` okuyucu                                                          |
| `lib/kinematics.py`        | Montaj pozu için hafif ters kinematik (F1'de C++ çekirdekle çapraz kontrol edilecek) |
| `lib/parts.py`             | Her parçanın geometrisi, kendi yerel çerçevesinde                                    |
| `build.py`                 | Bağları kurar, poza yerleştirir, kontrol eder, dışa aktarır                          |
| `render.py`                | Montajı malzemeye göre renklendirip görselleri üretir                                |
| `out/delta_v2.FCStd`       | Montaj; her bağ ayrı `App::Part`, her parçanın `Malzeme` özelliği var                |
| `out/delta_v2_<poz>.FCStd` | `check_poses` montajları (ör. 1. kol −70°); yalnız kontrol ve görsel için            |
| `out/meshes/*.stl`         | Bağ mesh'leri, bağın yerel çerçevesinde (URDF / RViz / Gazebo / web ikizi)           |
| `out/mass_properties.json` | Bağ başına kütle (kg), kütle merkezi (m), atalet tensörü (kg·m²)                     |
| `out/checks.md`            | Kinematik ölçü, rot başı açısı, çakışma ve mekanik bulgular                          |

Görseller: [docs/img/cad/](../docs/img/cad/)

## Simülasyon bağları ve çerçeveleri

Robot çerçevesi: orijin üç motor ekseninin düzleminin merkezi, +Z yukarı, 1. kol +X, kollar üstten bakınca saat yönünün tersine 0/120/240°.

| Bağ             | Eklem               | Yerel çerçeve                                                                                                                           |
| --------------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `base`          | sabit               | robot çerçevesi                                                                                                                         |
| `bicep_i`       | döner, motor ekseni | orijin motor ekseni (A_i); X kısa kol yönü (θ=0'da radyal dışa), Y motor ekseni, Z yukarı. θ, Y etrafında; pozitif θ kolu aşağı indirir |
| `forearm_i_a/b` | iki uçta küresel    | orijin üst rot başı küre merkezi; X alt küre merkezine; Y rot başı deliği ekseni                                                        |
| `platform`      | 3 DOF öteleme       | orijin P (alt eklem merkezlerinin düzlemi); eksenler robot çerçevesine paralel                                                          |

Kapalı zincir: her `forearm` iki ucunda küresel eklemle bağlıdır; URDF ağaç yapısında bu, F3'te tek uçtan bağlanıp diğer uç kısıtla kapatılarak modellenir.

## Kütle varsayımları

Yoğunluklar `materials` bölümünden gelir. Kütlesi katalogda bilinen parçalarda (AX-12A 54.6 g, 608ZZ 12 g, rot başı ~12 g, elektromıknatıs ~35 g) katı modelin hacmi bu kütleye ölçeklenir. %20 doluluklu PLA için etkin yoğunluk 0.56 g/cm³ alındı (varsayım).
