# Remote Acces Parallel Delta Robot Experiment Kit
![alt text](https://github.com/allefenes/ParallelDeltaRobot/blob/main/logo/logo.png)

## Delta Robotics V2 (geliştiriliyor)

V2, aynı robotun uzaktan erişilebilir yeni sürümüdür: kullanıcılar web sayfasından ya da VS Code'dan Python yazarak robotu (ya da dijital ikizini) güvenli bir çerçevede kontrol eder. C++ çekirdek, ROS2 Jazzy, Docker. Tüm V2 çalışması [`DeltaRobotV2/`](DeltaRobotV2/) klasöründedir; durum ve yol haritası için [DeltaRobotV2/README.md](DeltaRobotV2/README.md).

[![Claude Code ile geliştirildi](https://img.shields.io/badge/Claude%20Code%20ile-geli%C5%9Ftirildi-D97757?logo=claude&logoColor=white)](https://claude.com/claude-code) V2, [Claude Code](https://claude.com/claude-code) ile geliştirilmektedir.

V2 is the remotely accessible rewrite of the same robot; everything lives in [`DeltaRobotV2/`](DeltaRobotV2/).

## V1 değerlendirmesi ve V2'ye taşınan dersler

V1, son sınıf dersleriyle paralel olarak tek başına geliştirilmiş bir bitirme projesidir. V2'ye başlamadan önce kodu baştan sona gözden geçirdik.

**Güçlü yanlar**

- İleri ve ters kinematik doğru: gidiş-dönüş hatası ~1e-13 mm. Pasif mafsal açıları ve küresel mafsal limiti de hesaplanıyor.
- Kod, kontrolden çıkan tek dosyalık ilk sürümden (`LikeSoup/`) modüler, nesne yönelimli bir yapıya (`KilavuzDeltaRobotics/`) elle ayrıştırıldı; kinematik modeli arayüzden bağımsız.
- Uçtan uca çalışan bir hat: parametrik robot tanımı → kinematik → yörünge doğrulama ve simülasyon → senkron motor kontrolü ve telemetri → görüntü işleme.
- Sağlam mekanik: çıkış milleri rulmanla yataklanmış, servolar kol yükü taşımıyor; motorlar enerjisizken uç işlevci elle zahmetsizce hareket ediyor.

**Geliştirilmesi gerekenler → V2'deki karşılığı**

- Motora giden komut yolu limit kontrolünü atlayabiliyordu → V2'de her komut tek bir güvenlik süpervizöründen geçer.
- Servo hızı ve komut değerleri sınırlanmıyordu → süpervizörde hız/ivme sınırları ve değer kırpma.
- Seri port ve arayüz birden çok thread'den eşzamanlı kullanılıyordu → donanımın tek sahibi olan sürücü katmanı (ROS2).
- Test, bağımlılık listesi ve paketleme yoktu → C++ çekirdek ve testler, Docker ortamı, CI.
- Derleme çıktıları ve büyük veri repoya girmişti; kod biçimi tutarsızdı → `.gitignore`, otomatik biçimlendirme ve pre-commit denetimi.

## V1 (2024, arşiv)

Aşağıdaki metin ve `LikeSoup/`, `KilavuzDeltaRobotics/`, `ImageProcessing/`, `WsAnalysis/` klasörleri 2024 bitirme projesine aittir ve referans olarak değiştirilmeden tutulur.

We are developing Remote Access Parallel Delta Robot Experiment Kit for TEKNOFEST competition. Our team name is DELTA ROBOTICS.

Our project consists of several different areas. These are listed below under the electronic, mechanical and software categories.

<h1>⚡  Electronics:</h1>

We use dynamixel AX12-A smart servos of the robotis brand. We control the entire system with Raspberry pi 4b (8GB). For this case, we fulfill the electronic requirements for communication by using the circuit below.


<h1>⚙️  Mechanics:</h1>

We have a small-sized delta robot design and we are constantly updating our designs as a result of the current tests.


<h1>💻 Softwares:</h1>

We are using raspbian-os on raspberry pi. Since we are in the prototype stage, we use Real-VNC with remote desktop access. We are developing an interface with the tkinter library in Python language. In the following stages, the project will be completely dockerized and the repository will be updated.
