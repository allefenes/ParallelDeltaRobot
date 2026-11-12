"""En küçük örnek: iki noktaya git, mıknatısı aç/kapat, eve dön.

Çalıştırma: DELTA_URL, DELTA_TOKEN (ve gerekirse DELTA_CA_FILE) ayarlıyken `python hello.py`.
"""

from delta_robot import CommandRejected, Robot

with Robot() as robot:
    home = robot.info()["home_mm"]
    print("durum:", robot.state().state)

    robot.move_to(20, 10, -200)
    robot.magnet(True)
    robot.move_to(-20, -10, -220)
    robot.magnet(False)

    try:
        robot.move_to(0, 0, -300)  # çalışma uzayı dışında: kapı reddeder
    except CommandRejected as exc:
        print(f"reddedildi ({exc.requirement}): {exc.reason}")

    robot.move_to(*home)
    print("son konum:", robot.state().position_mm)
