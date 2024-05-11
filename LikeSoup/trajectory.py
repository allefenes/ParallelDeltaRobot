import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

trajectoryName = 'trajectory1'

t1 = np.linspace(1, 30, 1000)
t2 = np.linspace(180, 235, 1000)

x = t1 * np.cos(t1)
y = t1 *  np.sin(t1)
z = t2

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
ax.plot(x, y, z, label='Yörünge')
ax.scatter(0, 0, 0, color='red', label='Merkez')  # Merkez noktasını göster
ax.set_aspect('equal')
ax.legend()
plt.show()

trajectoryPlan = np.vstack((x, y, z))

np.save(f'trajectories/{trajectoryName}.npy', trajectoryPlan)

