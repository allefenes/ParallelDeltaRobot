# Başlangıç örneği: robotu birkaç noktaya götürür, mıknatısı açıp kapatır.
# Koordinatlar mm; P platform merkezidir (mıknatıs ucu 15 mm aşağıda).
# Çalıştır: Ctrl+Enter ya da "Çalıştır" düğmesi. Robotu durdurmak için "DUR".
from delta_robot import CommandRejected, Robot

robot = Robot()  # sandbox'ta bağlantı kendiliğinden kurulur

durum = robot.state()
print("Durum:", durum.state, "konum:", durum.position_mm)

print("Ev konumuna gidiliyor")
robot.move_to(0, 0, -200)

noktalar = [(20, 0, -200), (0, 20, -210), (-20, -10, -190)]
for x, y, z in noktalar:
    print(f"Hedef: ({x}, {y}, {z})")
    robot.move_to(x, y, z)

robot.magnet(True)
print("Mıknatıs açık")
robot.magnet(False)

# Çalışma alanı dışındaki bir nokta güvenlik kapısında reddedilir.
try:
    robot.move_to(0, 0, -300)
except CommandRejected as hata:
    print("Reddedildi:", hata.requirement, hata.reason)

robot.move_to(0, 0, -200)
print("Bitti")
