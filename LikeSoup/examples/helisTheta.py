import numpy as np
import json
from deltaRobot import deltaRobot

trajectoryPlan = np.load("trajectoryHelis.npy")

myRobot = deltaRobot(la = 64.2, lb = 201, ra = 75, rb=37.5, btf=240, minTurnAngle=0.29, cwMax=150, ccwMax=-70, jointMax=14)

planTableTheta = []
planTableCoo = []

for i in range(1000):
    res1 = myRobot.inverseKinematic(trajectoryPlan[0,i],trajectoryPlan[1,i],trajectoryPlan[2,i])
    planTableTheta.append(res1)
    res2 = myRobot.forwardKinematic(res1[0], res1[1], res1[2])
    planTableCoo.append(res2)

np.save(f'helisTheta.npy', planTableTheta)