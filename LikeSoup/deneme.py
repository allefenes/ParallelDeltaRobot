import numpy as np
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d.axes3d as p3
import matplotlib.animation as animation
import json
from deltaRobot import deltaRobot

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

try:
    with open('myRobot.json', 'r') as dosya:
        json_dosyası = dosya.read()
        json_icerik = json.loads(json_dosyası)
        base = float(json_icerik.get("base"))
        bicep = float(json_icerik.get("bicep"))
        forearm = float(json_icerik.get("forearm"))
        end = float(json_icerik.get("end"))
        btf = float(json_icerik.get("btf"))
        eeOffset = float(json_icerik.get("eeOffset"))
        turnAngle =  float(json_icerik.get("turnAngle"))
        bicepPosAngle = float(json_icerik.get("bicepPosAngle"))
        bicepNegAngle = float(json_icerik.get("bicepNegAngle"))
        joint = float(json_icerik.get("joint"))
        robotName = json_icerik.get("robotName")
except FileNotFoundError:
    print(f"myRobot.json dosyası bulunamadı.")
except Exception as e:
    print(f"Hata oluştu: {e}")

initialTheta1=0
initialTheta2=0
initialTheta3=0

myRobot = deltaRobot(la = bicep, lb = forearm, ra = base, rb=end, btf=btf, minTurnAngle=turnAngle, cwMax=bicepPosAngle, ccwMax=-bicepNegAngle, jointMax=joint)
cozum = myRobot.forwardKinematic(initialTheta1,initialTheta2,initialTheta3)

ax.scatter(0, 0, 0, color="r", alpha=1)

theta = np.linspace(0, 2*np.pi, 100)
x1 = base * np.cos(theta)
y1 = base * np.sin(theta)
z1 = np.zeros_like(x1)
ax.plot(x1, y1, z1, color="b")

origin = [0, 0, 0]
vektorler = [[(base/2), 0, 0], [0, (base/2), 0], [0, 0, (base/2)]]
renkler = ['r', 'g', 'b']
eksen_isimleri = ['X', 'Y', 'Z']

for vektor, renk, isim in zip(vektorler, renkler, eksen_isimleri):
    ax.quiver(*origin, *vektor, color=renk)
    ax.text(origin[0] + vektor[0], origin[1] + vektor[1], origin[2] + vektor[2], isim)

def drawLineParam(startDot, endDot, lineColor="b",lineAlpha=1):
    ax.plot([startDot[0], endDot[0]], [startDot[1], endDot[1]], [startDot[2], endDot[2]], color=lineColor, alpha=lineAlpha)

#Actuators
ax.scatter(cozum[0][0][0],cozum[0][0][1],cozum[0][0][2], color="b", alpha=1)
drawLineParam([0,0,0],cozum[0][0], lineColor="b", lineAlpha=0.3)
ax.text(cozum[0][0][0], cozum[0][0][1], cozum[0][0][2]-10, "A1")

ax.scatter(cozum[1][0][0],cozum[1][0][1],cozum[1][0][2], color="b", alpha=1)
drawLineParam([0,0,0],cozum[1][0], lineColor="b", lineAlpha=0.3)
ax.text(cozum[1][0][0], cozum[1][0][1], cozum[0][0][2]-10, "A2")

ax.scatter(cozum[2][0][0],cozum[2][0][1],cozum[2][0][2], color="b", alpha=1)
drawLineParam([0,0,0],cozum[2][0], lineColor="b", lineAlpha=0.3)
ax.text(cozum[2][0][0], cozum[2][0][1], cozum[0][0][2]-10, "A3")

#Floor
Z3 = np.full((10, 10), 240)  # 10x10 boyutunda tamamı 240 olan bir array oluştur
x2 = np.linspace(-base*2, base*2, 10)
y2 = np.linspace(-base*2, base*2, 10)
X3, Y3 = np.meshgrid(x2, y2)
ax.plot_surface(X3, Y3, Z3, color='g', alpha=0.2)

trajectoryPlan = np.load("trajectories/trajectory1.npy")

ax.plot(trajectoryPlan[0,:], trajectoryPlan[1,:], trajectoryPlan[2,:], color='red')

bicep1LineX = [cozum[0][0][0], cozum[0][1][0]]
bicep1LineY = [cozum[0][0][1], cozum[0][1][1]]
bicep1LineZ = [cozum[0][0][2], cozum[0][1][2]]
line_bicep1, = ax.plot(bicep1LineX, bicep1LineY, bicep1LineZ, color='blue')

forearm1LineX = [cozum[0][1][0], cozum[0][2][0]]
forearm1LineY = [cozum[0][1][1], cozum[0][2][1]]
forearm1LineZ = [cozum[0][1][2], cozum[0][2][2]]
line_forearm1, = ax.plot(forearm1LineX, forearm1LineY, forearm1LineZ, color='blue')

bicep2LineX = [cozum[1][0][0], cozum[1][1][0]]
bicep2LineY = [cozum[1][0][1], cozum[1][1][1]]
bicep2LineZ = [cozum[1][0][2], cozum[1][1][2]]
line_bicep2, = ax.plot(bicep2LineX, bicep2LineY, bicep2LineZ, color='blue')

forearm2LineX = [cozum[1][1][0], cozum[1][2][0]]
forearm2LineY = [cozum[1][1][1], cozum[1][2][1]]
forearm2LineZ = [cozum[1][1][2], cozum[1][2][2]]
line_forearm2, = ax.plot(forearm2LineX, forearm2LineY, forearm2LineZ, color='blue')

bicep3LineX = [cozum[2][0][0], cozum[2][1][0]]
bicep3LineY = [cozum[2][0][1], cozum[2][1][1]]
bicep3LineZ = [cozum[2][0][2], cozum[2][1][2]]
line_bicep3, = ax.plot(bicep3LineX, bicep3LineY, bicep3LineZ, color='blue')

forearm3LineX = [cozum[2][1][0], cozum[2][2][0]]
forearm3LineY = [cozum[2][1][1], cozum[2][2][1]]
forearm3LineZ = [cozum[2][1][2], cozum[2][2][2]]
line_forearm3, = ax.plot(forearm3LineX, forearm3LineY, forearm3LineZ, color='blue')

endDot1W = [cozum[0][3][0], cozum[0][3][1], (cozum[0][3][2])]
endDotW, = ax.plot(endDot1W[0], endDot1W[1], endDot1W[2], 'ro')

end1Dot = [cozum[0][3][0], cozum[0][3][1], (cozum[0][3][2] + eeOffset)]
eeDot, = ax.plot(end1Dot[0], end1Dot[1], end1Dot[2], 'gv')

eeLineX = [cozum[0][3][0], cozum[0][3][0]]
eeLineY = [cozum[0][3][1], cozum[0][3][1]]
eeLineZ = [cozum[0][3][2], cozum[0][3][2] + eeOffset]
line_ee, = ax.plot(eeLineX, eeLineY, eeLineZ, color='green')

eeRadiusX = cozum[0][3][0] + end * np.cos(theta)
eeRadiusY = cozum[0][3][1] + end * np.sin(theta)
eeRadiusZ = cozum[0][3][2] + np.zeros_like(eeRadiusX)
eeRadius, = ax.plot(eeRadiusX, eeRadiusY, eeRadiusZ, color='blue')

eeLine1X = [cozum[0][2][0],cozum[0][3][0]]
eeLine1Y = [cozum[0][2][1],cozum[0][3][1]]
eeLine1Z = [cozum[0][2][2],cozum[0][3][2]]
eeLine1, = ax.plot(eeLine1X, eeLine1Y, eeLine1Z, color="b", alpha=0.3)

eeLine2X = [cozum[1][2][0],cozum[1][3][0]]
eeLine2Y = [cozum[1][2][1],cozum[1][3][1]]
eeLine2Z = [cozum[1][2][2],cozum[1][3][2]]
eeLine2, = ax.plot(eeLine2X, eeLine2Y, eeLine2Z, color="b", alpha=0.3)

eeLine3X = [cozum[2][2][0],cozum[2][3][0]]
eeLine3Y = [cozum[2][2][1],cozum[2][3][1]]
eeLine3Z = [cozum[2][2][2],cozum[2][3][2]]
eeLine3, = ax.plot(eeLine3X, eeLine3Y, eeLine3Z, color="b", alpha=0.3)

planTableTheta = []
planTableCoo = []

satirSayisi, sutunSayisi = np.shape(trajectoryPlan)

for i in range(sutunSayisi):
    res1 = myRobot.inverseKinematic(trajectoryPlan[0,i],trajectoryPlan[1,i],trajectoryPlan[2,i] - eeOffset )
    planTableTheta.append(res1)
    res2 = myRobot.forwardKinematic(res1[0], res1[1], res1[2])
    planTableCoo.append(res2)

def init():
    return line_bicep1, line_bicep2, line_bicep3, line_forearm1, line_forearm2, line_forearm3, eeDot, line_ee, eeLine1, eeLine2, eeLine3, endDotW

def update(num, line_bicep1, line_bicep2, line_bicep3, line_forearm1, line_forearm2, line_forearm3, eeDot, line_ee, eeLine1, eeLine2,eeLine3, endDotW):
    
    line_bicep1.set_data([planTableCoo[num][0][0][0], planTableCoo[num][0][1][0]], [planTableCoo[num][0][0][1], planTableCoo[num][0][1][1]]) #[Ax,Bx,Ay,By]
    line_bicep1.set_3d_properties([planTableCoo[num][0][0][2], planTableCoo[num][0][1][2]]) #[Az,Bz]

    line_forearm1.set_data([planTableCoo[num][0][1][0], planTableCoo[num][0][2][0]], [planTableCoo[num][0][1][1], planTableCoo[num][0][2][1]]) #[Bx,Cx,By,Cy]
    line_forearm1.set_3d_properties([planTableCoo[num][0][1][2], planTableCoo[num][0][2][2]]) #[Bz,Cz]

    line_bicep2.set_data([planTableCoo[num][1][0][0], planTableCoo[num][1][1][0]], [planTableCoo[num][1][0][1], planTableCoo[num][1][1][1]]) #[Ax,Bx,Ay,By]
    line_bicep2.set_3d_properties([planTableCoo[num][1][0][2], planTableCoo[num][1][1][2]]) #[Az,Bz]

    line_forearm2.set_data([planTableCoo[num][1][1][0], planTableCoo[num][1][2][0]], [planTableCoo[num][1][1][1], planTableCoo[num][1][2][1]]) #[Bx,Cx,By,Cy]
    line_forearm2.set_3d_properties([planTableCoo[num][1][1][2], planTableCoo[num][1][2][2]]) #[Bz,Cz]

    line_bicep3.set_data([planTableCoo[num][2][0][0], planTableCoo[num][2][1][0]], [planTableCoo[num][2][0][1], planTableCoo[num][2][1][1]]) #[Ax,Bx,Ay,By]
    line_bicep3.set_3d_properties([planTableCoo[num][2][0][2], planTableCoo[num][2][1][2]]) #[Az,Bz]

    line_forearm3.set_data([planTableCoo[num][2][1][0], planTableCoo[num][2][2][0]], [planTableCoo[num][2][1][1], planTableCoo[num][2][2][1]]) #[Bx,Cx,By,Cy]
    line_forearm3.set_3d_properties([planTableCoo[num][2][1][2], planTableCoo[num][2][2][2]]) #[Bz,Cz]

    endDotW.set_data([planTableCoo[num][0][3][0]], [planTableCoo[num][0][3][1]])
    endDotW.set_3d_properties([planTableCoo[num][0][3][2]])

    eeDot.set_data([planTableCoo[num][0][3][0]], [planTableCoo[num][0][3][1]])#[Dx,Dy]
    eeDot.set_3d_properties([planTableCoo[num][0][3][2] + eeOffset]) #[Dz+offset]

    line_ee.set_data([planTableCoo[num][0][3][0], planTableCoo[num][0][3][0]], [planTableCoo[num][0][3][1], planTableCoo[num][0][3][1]])
    line_ee.set_3d_properties([planTableCoo[num][0][3][2], planTableCoo[num][0][3][2] + eeOffset])

    xs = planTableCoo[num][0][3][0] + end * np.cos(theta)
    ys = planTableCoo[num][0][3][1] + end * np.sin(theta)
    zs = planTableCoo[num][0][3][2] + np.zeros_like(xs)
    eeRadius.set_data(xs, ys)
    eeRadius.set_3d_properties(zs)

    eeLine1.set_data([planTableCoo[num][0][2][0], planTableCoo[num][0][3][0]], [planTableCoo[num][0][2][1], planTableCoo[num][0][3][1]])
    eeLine1.set_3d_properties([planTableCoo[num][0][2][2], planTableCoo[num][0][2][2]])

    eeLine2.set_data([planTableCoo[num][1][2][0], planTableCoo[num][1][3][0]], [planTableCoo[num][1][2][1], planTableCoo[num][1][3][1]])
    eeLine2.set_3d_properties([planTableCoo[num][1][2][2], planTableCoo[num][1][2][2]])

    eeLine3.set_data([planTableCoo[num][2][2][0], planTableCoo[num][2][3][0]], [planTableCoo[num][2][2][1], planTableCoo[num][2][3][1]])
    eeLine3.set_3d_properties([planTableCoo[num][2][2][2], planTableCoo[num][2][2][2]])

    return line_bicep1, line_bicep2, line_bicep3, line_forearm1, line_forearm2, line_forearm3, eeDot, line_ee, eeLine1, eeLine2, eeLine3, endDotW

dynamicInterval = 0
ani = animation.FuncAnimation(fig, update, frames=sutunSayisi, fargs=[line_bicep1, line_bicep2, line_bicep3, line_forearm1, line_forearm2, line_forearm3, eeDot, line_ee, eeLine1, eeLine2, eeLine3, endDotW], interval=dynamicInterval, blit=False, init_func=init)

ax.text(base,0,btf, f"{robotName}")
ax.view_init(elev=-145,azim=-145)
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
ax.set_aspect('equal')
plt.show()

