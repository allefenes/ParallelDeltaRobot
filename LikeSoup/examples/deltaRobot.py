import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from math import cos
from math import sin

class deltaRobot():

    def __init__(self, la = 64.2, lb = 201, ra = 65, rb = 37.5, btf = 240, alpha = [0,120,240], minTurnAngle = 0.29, ccwMax = -70, cwMax = 150, jointMax = 14 ):
        self.jointMax = jointMax
        self.cwMax = cwMax
        self.ccwMax = ccwMax
        self.minTurnAngle = minTurnAngle
        self.alpha = np.array([(alpha[0] * (np.pi / 180)), (alpha[1] * (np.pi / 180)), (alpha[2] * (np.pi / 180))])
        self.btf = btf
        self.rb = rb
        self.ra = ra
        self.lb = lb
        self.la = la
        self.r = self.ra - self.rb

        
    def forwardKinematic(self,teta1 = 0, teta2 = 0, teta3 = 0):

        if teta1 > self.cwMax or teta1 < self.ccwMax or teta2 >  self.cwMax or teta2 < self.ccwMax or teta3 >  self.cwMax or teta3 < self.ccwMax:
            return False

        TETA = np.array([teta1*np.pi/180, teta2*np.pi/180, teta3*np.pi/180])

        Ax = np.zeros(3)
        Ay = np.zeros(3)
        Az = np.zeros(3)
        Bx = np.zeros(3)
        By = np.zeros(3)
        Bz = np.zeros(3)
        rotatedBx = np.zeros(3)
        rotatedBy = np.zeros(3)
        rotatedBz = np.zeros(3)
        Cx = np.zeros(3)
        Cy = np.zeros(3)
        Cz = np.zeros(3)
        rotatedCx = np.zeros(3)
        rotatedCy = np.zeros(3)
        rotatedCz = np.zeros(3)
        x = np.zeros(3)
        y = np.zeros(3)
        z = np.zeros(3)
        AC = np.zeros(3)
        BETA = np.zeros(3)
        FI = np.zeros(3)
        GAMA = np.zeros(3)


        for i in range(3):
            Ax[i] = self.ra * np.cos(self.alpha[i])
            Ay[i] = self.ra * np.sin(self.alpha[i])
            Az[i] = np.zeros_like(self.alpha[i])

            Bx[i] = self.ra * np.cos(self.alpha[i]) + self.la * np.cos(self.alpha[i]) * np.cos(TETA[i])
            By[i] = self.ra * np.sin(self.alpha[i]) + self.la * np.sin(self.alpha[i]) * np.cos(TETA[i])
            Bz[i] = self.la * np.sin(TETA[i])

            x[i] = (self.r + self.la * np.cos(TETA[i])) * np.cos(self.alpha[i])
            y[i] = (self.r + self.la * np.cos(TETA[i])) * np.sin(self.alpha[i])
            z[i] = self.la * np.sin(TETA[i])

        w1 = x[0] ** 2 + y[0] ** 2 + z[0] ** 2
        w2 = x[1] ** 2 + y[1] ** 2 + z[1] ** 2
        w3 = x[2] ** 2 + y[2] ** 2 + z[2] ** 2

        d1 = (x[1] - x[0]) * (y[2] - y[1]) - (x[2] - x[1]) * (y[1] - y[0])
        
        a1 = ((z[2] - z[1]) * (y[1] - y[0])) - ((z[1] - z[0]) * (y[2] - y[1]))
        b1 = ((w2 - w1) * (y[2] - y[1]) - (w3 - w2) * (y[1] - y[0])) / 2

        d2 = (x[2] - x[1]) * (y[1] - y[0]) - (x[1] - x[0]) * (y[2] - y[1])
        a2 = ((z[2] - z[1]) * (x[1] - x[0])) - ((z[1] - z[0]) * (x[2] - x[1]))
        b2 = ((w2 - w1) * (x[2] - x[1]) - (w3 - w2) * (x[1] - x[0])) / 2

        a = ((a1 ** 2) / (d1 ** 2)) + ((a2 ** 2) / (d2 ** 2)) + 1
        b = 2 * (((a1 * b1) / (d1 ** 2)) + ((a2 * b2) / (d2 ** 2)) - ((x[0] * a1) / d1) - ((y[0] * a2) / d2) - z[0])
        c = ((b1 ** 2) / (d1 ** 2)) + ((b2 ** 2) / (d2 ** 2)) - ((2 * x[0] * b1) / d1) - ((2 * y[0] * b2) / d2) + w1 - (self.lb ** 2)

        delta = (b ** 2) - (4 * a * c)
        
        if delta >= 0:
            Dz = (-b + np.sqrt(delta)) / (2 * a)
            Dx = (a1 / d1) * Dz + (b1 / d1)
            Dy = (a2 / d2) * Dz + (b2 / d2)
        else:
            return False
        for i in range(3):
            Cx[i] = Dx + self.rb * np.cos(self.alpha[i])
            Cy[i] = Dy + self.rb * np.sin(self.alpha[i])
            Cz[i] = Dz
            AC[i] = np.sqrt((Cx[i] - Ax[i])**2 + (Cy[i] - Ay[i])**2 + (Cz[i] - Az[i])**2)
            BETA[i] = np.degrees(np.arccos((self.la ** 2 + self.lb ** 2 - ((Cx[i] - Ax[i]) ** 2 + (Cy[i] - Ay[i]) ** 2 + (Cz[i] - Az[i]) ** 2)) / (2 * self.la * self.lb)))
            FI[i] = BETA[i] - (TETA[i] * 180 / np.pi)

            angle = np.radians(360-np.degrees(self.alpha[i]))
            
            rotationMatrix = np.array([
                    [cos(angle),    -sin(angle),    0],
                    [sin(angle),    cos(angle),     0],
                    [0,             0,              1]
                ]    
                )

            rotatedBx[i] = rotationMatrix[0][0] * Bx[i] + rotationMatrix[0][1] * By[i]
            rotatedBy[i] = rotationMatrix[1][0] * Bx[i] + rotationMatrix[1][1] * By[i] 
            rotatedBz[i] = Bz[i]

            rotatedCx[i] = rotationMatrix[0][0] * Cx[i] + rotationMatrix[0][1] * Cy[i] 
            rotatedCy[i] = rotationMatrix[1][0] * Cx[i] + rotationMatrix[1][1] * Cy[i] 
            rotatedCz[i] = Cz[i]

            GAMA[i] = np.degrees(np.arctan2(rotatedCy[i] - rotatedBy[i], rotatedCz[i] - rotatedBz[i]))

        if abs(GAMA[0]) > self.jointMax or abs(GAMA[1]) > self.jointMax or abs(GAMA[2]) > self.jointMax:
            return False


        result =    (
                    ((Ax[0], Ay[0], Az[0]), (Bx[0], By[0], Bz[0]), (Cx[0], Cy[0], Cz[0]), (Dx, Dy, Dz), BETA[0], FI[0],GAMA[0]),
                    ((Ax[1], Ay[1], Az[1]), (Bx[1], By[1], Bz[1]), (Cx[1], Cy[1], Cz[1]), (Dx, Dy, Dz), BETA[1], FI[1],GAMA[1]),
                    ((Ax[2], Ay[2], Az[2]), (Bx[2], By[2], Bz[2]), (Cx[2], Cy[2], Cz[2]), (Dx, Dy, Dz), BETA[2], FI[2],GAMA[2])
                    )



        return result


    def inverseKinematic(self,Dx, Dy, Dz):

        TETA = np.zeros(3)
        X = np.zeros(3)
        CosTETA = np.zeros(3)
        SinTETA = np.zeros(3)
        TTETA = np.zeros(3)

        for i in range(3):
            X[i] = ((self.la**2) - (self.lb**2) + ((Dx - (self.r*np.cos(self.alpha[i])))**2) + ((Dy - (self.r*np.sin(self.alpha[i])))**2) + (Dz**2)) / (2 * self.la)

            A = (Dz**2) + ((Dx*np.cos(self.alpha[i])) + (Dy*np.sin(self.alpha[i])) - self.r)**2
            B = -2 * X[i] * ((Dx*np.cos(self.alpha[i])) + (Dy*np.sin(self.alpha[i])) - self.r)
            C = (X[i]**2) - (Dz**2)
            
            DELTA = (B**2) - (4 * A * C)

            if DELTA >= 0:
                isDefined = True
                CosTETA[i] = (-B + np.sqrt(DELTA)) / (2 * A)
                SinTETA[i] = (X[i] - ((Dx*np.cos(self.alpha[i])) + (Dy*np.sin(self.alpha[i])) - self.r) * CosTETA[i]) / Dz
                TTETA[i] = np.arctan2(SinTETA[i], CosTETA[i])
                TETA[i] = TTETA[i] * 180 / np.pi
            else:
                return False
        
        TETA = tuple(TETA)
        return TETA

    def resolution(self):
        r1=self.forwardKinematic(0,0,0)[0][3]
        r2=self.forwardKinematic(self.minTurnAngle,0,0)[0][3]
    
        x=(r1[1]-r2[1]);
        y=(r1[2]-r2[2]);
        sum=np.sqrt(x*x+y*y);
        return sum