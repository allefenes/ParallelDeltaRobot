import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from scipy.interpolate import griddata

def drawCylinder(bottomZ, topZ, r = 20, circleResolution = 1000):
    merkez = (0,0,0)
    theta = np.linspace(0, 2*np.pi, circleResolution)
    x = r * np.cos(theta)
    y = r * np.sin(theta)

    now = topZ
    rowRes = (bottomZ - topZ) / ((bottomZ - topZ)/0.8)
    for circle in np.arange(topZ,bottomZ,rowRes):
        z = np.full_like(x,circle)
        verts = [list(zip(x, y, z))]
        if (np.round(circle)+1 == np.round(bottomZ)  or circle == topZ):
            ax.add_collection3d(Poly3DCollection(verts, facecolors='green', edgecolors="black", linewidths=2, alpha=0.1))
        else:
            ax.add_collection3d(Poly3DCollection(verts, facecolors='green', alpha=0.1))

def plot_3d_surface(ax, data, color):
    x = [xyz[0] for xyz in data]
    y = [xyz[1] for xyz in data]
    z = [xyz[2] for xyz in data]

    xi, yi = np.linspace(min(x), max(x), 100), np.linspace(min(y), max(y), 100)
    xi, yi = np.meshgrid(xi, yi)

    zi = griddata((x, y), z, (xi, yi), method='linear')

    ax.plot_surface(xi, yi, zi, color=color, alpha=0.2)

with open('outputMaxSurf.json', 'r') as file:
    data_max = json.load(file)

with open('outputMinSurf.json', 'r') as file:
    data_min = json.load(file)

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

plot_3d_surface(ax, data_max, 'blue')

plot_3d_surface(ax, data_min, 'red')

note_x = 3
note_y = 3
note_z = 3

ax.set_xlabel('X Ekseni')
ax.set_ylabel('Y Ekseni')
ax.set_zlabel('Z Ekseni')

ax.view_init(elev=-150, azim=-130)

plt.show()
