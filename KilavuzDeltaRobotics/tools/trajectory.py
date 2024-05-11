import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
import os
import numpy as np
import json

from tools.deltaRobot import deltaRobot

class Trajectory():
    def createTrajPage(self,tab):
        self.label_frame = ttk.LabelFrame(tab, text="SIMULTANEOUS ROBOT")
        self.label_frame.grid(row=0, column=0, padx=10, pady=10, rowspan=2, sticky="nsew")

        self.figTra = plt.figure()
        self.axTra = self.figTra.add_subplot(111, projection='3d')
        self.canvasTra = FigureCanvasTkAgg(self.figTra, master=self.label_frame)
        self.canvasTra.get_tk_widget().grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.axTra.grid(False)
        
        self.label_frame.columnconfigure(index=0, weight=1)
        self.label_frame.rowconfigure(index=0, weight=1)
      
        self.notebook = ttk.Notebook(tab)
        self.notebook.grid(row=0, column=1,columnspan=4, padx=10, pady=10, sticky="nsew")

        self.xyzTab = ttk.Frame(self.notebook)
        self.notebook.add(self.xyzTab, text="X-Y-Z")

        self.figCoo = plt.figure(figsize=(6, 3))
        self.axCoo = self.figCoo.add_subplot(111)
        self.canvasCoo = FigureCanvasTkAgg(self.figCoo, master=self.xyzTab)
        self.canvasCoo.get_tk_widget().grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.axCoo.set_title('END EFFECTOR LOCATION')
        self.axCoo.set_xlabel('Time')
        self.axCoo.set_ylabel('Coordinates')
        self.axCoo.set_ylim(-1.1, 1.1)
        self.axCoo.set_xlim(0, 1)
        
        
        self.angTab = ttk.Frame(self.notebook)
        self.notebook.add(self.angTab, text="θ1-θ2-θ3")

        self.figAng = plt.figure(figsize=(6, 3))
        self.axAng = self.figAng.add_subplot(111)
        self.canvasAng = FigureCanvasTkAgg(self.figAng, master=self.angTab)
        self.canvasAng.get_tk_widget().grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.axAng.set_title('MOTOR ANGLES')
        self.axAng.set_xlabel('Time')
        self.axAng.set_ylabel('Angle')
        self.axAng.set_ylim(-1.1, 1.1)
        self.axAng.set_xlim(0, 1)
       
        self.xyzTab.columnconfigure(index=0, weight=1)       
        self.xyzTab.rowconfigure(index=0, weight=1)
        self.angTab.columnconfigure(index=0, weight=1)       
        self.angTab.rowconfigure(index=0, weight=1)

        self.realTimeOutputs = ttk.LabelFrame(tab, text="INSTANT VALUES")
        self.realTimeOutputs.grid(row=1, column=1, columnspan=4, padx=10, pady=10, sticky="nsew")

        self.realTimeOutputs.columnconfigure(index=0, weight=1)
        self.realTimeOutputs.columnconfigure(index=1, weight=1)
        self.realTimeOutputs.columnconfigure(index=2, weight=1)
        self.realTimeOutputs.columnconfigure(index=3, weight=1)
        self.realTimeOutputs.columnconfigure(index=4, weight=1)
        self.realTimeOutputs.columnconfigure(index=5, weight=1)
        self.realTimeOutputs.rowconfigure(index=0, weight=1)
        self.realTimeOutputs.rowconfigure(index=1, weight=1)

        self.label1 = ttk.Label(self.realTimeOutputs,text="X :", font=("Arial", 14))
        self.label1.grid(row=0, column=0, padx=0, pady=0,sticky="e")

        self.label2 = ttk.Label(self.realTimeOutputs,text="180.00", font=("Arial", 14))
        self.label2.grid(row=0, column=1, padx=0, pady=0, sticky="w" )
        
        self.label3 = ttk.Label(self.realTimeOutputs,  text="Y :", font=("Arial",14) )
        self.label3.grid(row=0, column=2, padx=0, pady=0,sticky="e")

        self.label4 = ttk.Label(self.realTimeOutputs,text="180.00", font=("Arial", 14))
        self.label4.grid(row=0, column=3, padx=0, pady=0, sticky="w" )
       
        self.label5 = ttk.Label(self.realTimeOutputs,text="Z: ", font=("Arial", 14 ))
        self.label5.grid(row=0, column=4, padx=0, pady=0,sticky="e")

        self.label6 = ttk.Label(self.realTimeOutputs,text="180.00", font=("Arial", 14))
        self.label6.grid(row=0, column=5, padx=0, pady=0, sticky="w" )

        self.label7 = ttk.Label(self.realTimeOutputs,text="θ1: " , font=("Arial", 14))
        self.label7.grid(row=1, column=0, padx=0, pady=0,sticky="e")

        self.label8 = ttk.Label(self.realTimeOutputs,text="180.00", font=("Arial", 14))
        self.label8.grid(row=1, column=1, padx=0, pady=0, sticky="w" )
        
        self.label9 = ttk.Label(self.realTimeOutputs,  text="θ2:", font=("Arial", 14) )
        self.label9.grid(row=1, column=2, padx=0, pady=0,sticky="e")

        self.label10 = ttk.Label( self.realTimeOutputs,text="180.00", font=("Arial", 14))
        self.label10.grid(row=1, column=3, padx=0, pady=0, sticky="w" )
       
        self.label11 = ttk.Label(self.realTimeOutputs,text="θ3: ", font=("Arial", 14) )
        self.label11.grid(row=1, column=4, padx=0, pady=0,sticky="e")

        self.label12 = ttk.Label(self.realTimeOutputs,text="180.00", font=("Arial", 14))
        self.label12.grid(row=1, column=5, padx=0, pady=0, sticky="w" )

        self.buttons = ttk.Label(tab)
        self.buttons.grid(row=2, column=0,columnspan=4, padx=0, pady=0, sticky="nsew")

        self.accentbutton = ttk.Button(self.buttons, text="ADD", style="Accent.TButton", command=self.addTrajectory)
        self.accentbutton.grid(row=0, column=0,  padx=10, pady=10, sticky="nsew")

        self.traListVar = []
        if os.path.exists("data/trajectories") and os.path.isdir("data/trajectories"):
            dosya_isimleri = [os.path.splitext(dosya)[0] for dosya in os.listdir("data/trajectories") if dosya.endswith(".npy")]
            self.traListVar.extend(dosya_isimleri)
            self.traList = ttk.Combobox(self.buttons, state="readonly", values=self.traListVar)
            self.traList.current(0)
            self.traList.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.accentbutton = ttk.Button(self.buttons, text="PLAY/PAUSE", style="Accent.TButton", command=self.toggleAni)
        self.accentbutton.grid(row=0, column=2,  padx=10, pady=10, sticky="nsew")
        self.aniPlay = True
        
        self.accentbutton = ttk.Button(self.buttons, text="ACTION", style="Accent.TButton")
        self.accentbutton.grid(row=0, column=3,  padx=10, pady=10, sticky="nsew")
        
        self.repetetive = tk.BooleanVar(value=True)
        self.checkbutton = ttk.Checkbutton(self.buttons, text="REPETITIVE", variable=self.repetetive, style="My.TCheckbutton")
        self.checkbutton.grid(row=0, column=4, padx=10, pady=10, sticky="nsew")

        self.buttons.columnconfigure(index=0, weight=1)
        self.buttons.columnconfigure(index=1, weight=10)
        self.buttons.columnconfigure(index=2, weight=10)
        self.buttons.columnconfigure(index=3, weight=10)
        self.buttons.columnconfigure(index=4, weight=1)

        tab.columnconfigure(index=0, weight=5)
        tab.columnconfigure(index=1, weight=3)
        tab.rowconfigure(index=0, weight=20)
        tab.rowconfigure(index=1, weight=6)
        tab.rowconfigure(index=2, weight=1)

        self.ani = None
        

    def addTrajectory(self):
        script_dosya_yolu = os.path.dirname(os.path.abspath(__file__))
        dosya_yolu = filedialog.askopenfilename(initialdir=script_dosya_yolu, title="Dosya Seç", filetypes=(("NPY files", "*.npy"), ("All files", "*.*")))
        if dosya_yolu:
            dosya_adı = os.path.basename(dosya_yolu)
            self.trajectoryPlan = np.load(dosya_yolu)
            np.save(f'trajectories/{dosya_adı}', self.trajectoryPlan)

    def drawLineTra(self, startDot, endDot, lineColor="b",lineAlpha=1):
        self.axTra.plot([startDot[0], endDot[0]], [startDot[1], endDot[1]], [startDot[2], endDot[2]], color=lineColor, alpha=lineAlpha)            

    def toggleAni(self):
        if self.aniPlay == True:
            self.aniPlay = False
            if self.ani:
                self.ani.event_source.start()
                self.aniTheta.event_source.start()
                self.aniCoo.event_source.start()
            else:
                self.aniTrajectory()

        elif self.aniPlay == False:
            self.aniPlay = True
            self.ani.pause()
            self.aniTheta.pause()
            self.aniCoo.pause()

    def aniTrajectory(self):
        self.axTra.cla()

        try:
            secilenTrajectory = self.traList.get()
            trajectoryPlan = np.load(f"data/trajectories/{secilenTrajectory}.npy")
        except FileNotFoundError:
            print(f"Trajectory Seçiniz.")

        try:
            with open('data/myRobot.json', 'r') as dosya:
                self.json_dosyası = dosya.read()
                self.json_icerik = json.loads(self.json_dosyası)

        except FileNotFoundError:
            print("data/myRobot.json dosyası bulunamadı.")
        except Exception as e:
            print(f"Hata oluştu: {e}")

        base = float(self.json_icerik.get("base"))
        bicep = float(self.json_icerik.get("bicep"))
        forearm = float(self.json_icerik.get("forearm"))
        end = float(self.json_icerik.get("end"))
        btf = float(self.json_icerik.get("btf"))
        eeOffset = float(self.json_icerik.get("eeOffset"))
        turnAngle =  float(self.json_icerik.get("turnAngle"))
        bicepPosAngle = float(self.json_icerik.get("bicepPosAngle"))
        bicepNegAngle = float(self.json_icerik.get("bicepNegAngle"))
        joint = float(self.json_icerik.get("joint"))
        robotName = self.json_icerik.get("robotName")


        initialTheta1=0
        initialTheta2=0
        initialTheta3=0

        myRobot = deltaRobot(la = bicep, lb = forearm, ra = base, rb=end, btf=btf, minTurnAngle=turnAngle, cwMax=bicepPosAngle, ccwMax=-bicepNegAngle, jointMax=joint)
        cozum = myRobot.forwardKinematic(initialTheta1,initialTheta2,initialTheta3)

        self.axTra.scatter(0, 0, 0, color="r", alpha=1)

        theta = np.linspace(0, 2*np.pi, 100)
        x1 = base * np.cos(theta)
        y1 = base * np.sin(theta)
        z1 = np.zeros_like(x1)
        self.axTra.plot(x1, y1, z1, color="b")

        origin = [0, 0, 0]
        vektorler = [[(base/2), 0, 0], [0, (base/2), 0], [0, 0, (base/2)]]
        renkler = ['r', 'g', 'b']
        eksen_isimleri = ['X', 'Y', 'Z']

        for vektor, renk, isim in zip(vektorler, renkler, eksen_isimleri):
            self.axTra.quiver(*origin, *vektor, color=renk)
            self.axTra.text(origin[0] + vektor[0], origin[1] + vektor[1], origin[2] + vektor[2], isim)

        def drawLineParam(startDot, endDot, lineColor="b",lineAlpha=1):
            self.axTra.plot([startDot[0], endDot[0]], [startDot[1], endDot[1]], [startDot[2], endDot[2]], color=lineColor, alpha=lineAlpha)

        #Actuators
        self.axTra.scatter(cozum[0][0][0],cozum[0][0][1],cozum[0][0][2], color="b", alpha=1)
        drawLineParam([0,0,0],cozum[0][0], lineColor="b", lineAlpha=0.3)
        self.axTra.text(cozum[0][0][0], cozum[0][0][1], cozum[0][0][2]-10, "A1")

        self.axTra.scatter(cozum[1][0][0],cozum[1][0][1],cozum[1][0][2], color="b", alpha=1)
        drawLineParam([0,0,0],cozum[1][0], lineColor="b", lineAlpha=0.3)
        self.axTra.text(cozum[1][0][0], cozum[1][0][1], cozum[0][0][2]-10, "A2")

        self.axTra.scatter(cozum[2][0][0],cozum[2][0][1],cozum[2][0][2], color="b", alpha=1)
        drawLineParam([0,0,0],cozum[2][0], lineColor="b", lineAlpha=0.3)
        self.axTra.text(cozum[2][0][0], cozum[2][0][1], cozum[0][0][2]-10, "A3")

        #Floor
        Z3 = np.full((10, 10), 240)  # 10x10 boyutunda tamamı 240 olan bir array oluştur
        x2 = np.linspace(-base*2, base*2, 10)
        y2 = np.linspace(-base*2, base*2, 10)
        X3, Y3 = np.meshgrid(x2, y2)
        self.axTra.plot_surface(X3, Y3, Z3, color='g', alpha=0.2)

        self.axTra.plot(trajectoryPlan[0,:], trajectoryPlan[1,:], trajectoryPlan[2,:], color='red')

        bicep1LineX = [cozum[0][0][0], cozum[0][1][0]]
        bicep1LineY = [cozum[0][0][1], cozum[0][1][1]]
        bicep1LineZ = [cozum[0][0][2], cozum[0][1][2]]
        line_bicep1, = self.axTra.plot(bicep1LineX, bicep1LineY, bicep1LineZ, color='blue')

        forearm1LineX = [cozum[0][1][0], cozum[0][2][0]]
        forearm1LineY = [cozum[0][1][1], cozum[0][2][1]]
        forearm1LineZ = [cozum[0][1][2], cozum[0][2][2]]
        line_forearm1, = self.axTra.plot(forearm1LineX, forearm1LineY, forearm1LineZ, color='blue')

        bicep2LineX = [cozum[1][0][0], cozum[1][1][0]]
        bicep2LineY = [cozum[1][0][1], cozum[1][1][1]]
        bicep2LineZ = [cozum[1][0][2], cozum[1][1][2]]
        line_bicep2, = self.axTra.plot(bicep2LineX, bicep2LineY, bicep2LineZ, color='blue')

        forearm2LineX = [cozum[1][1][0], cozum[1][2][0]]
        forearm2LineY = [cozum[1][1][1], cozum[1][2][1]]
        forearm2LineZ = [cozum[1][1][2], cozum[1][2][2]]
        line_forearm2, = self.axTra.plot(forearm2LineX, forearm2LineY, forearm2LineZ, color='blue')

        bicep3LineX = [cozum[2][0][0], cozum[2][1][0]]
        bicep3LineY = [cozum[2][0][1], cozum[2][1][1]]
        bicep3LineZ = [cozum[2][0][2], cozum[2][1][2]]
        line_bicep3, = self.axTra.plot(bicep3LineX, bicep3LineY, bicep3LineZ, color='blue')

        forearm3LineX = [cozum[2][1][0], cozum[2][2][0]]
        forearm3LineY = [cozum[2][1][1], cozum[2][2][1]]
        forearm3LineZ = [cozum[2][1][2], cozum[2][2][2]]
        line_forearm3, = self.axTra.plot(forearm3LineX, forearm3LineY, forearm3LineZ, color='blue')

        endDot1W = [cozum[0][3][0], cozum[0][3][1], (cozum[0][3][2])]
        endDotW, = self.axTra.plot(endDot1W[0], endDot1W[1], endDot1W[2], 'ro')

        end1Dot = [cozum[0][3][0], cozum[0][3][1], (cozum[0][3][2] + eeOffset)]
        eeDot, = self.axTra.plot(end1Dot[0], end1Dot[1], end1Dot[2], 'gv')

        eeLineX = [cozum[0][3][0], cozum[0][3][0]]
        eeLineY = [cozum[0][3][1], cozum[0][3][1]]
        eeLineZ = [cozum[0][3][2], cozum[0][3][2] + eeOffset]
        line_ee, = self.axTra.plot(eeLineX, eeLineY, eeLineZ, color='green')

        eeRadiusX = cozum[0][3][0] + end * np.cos(theta)
        eeRadiusY = cozum[0][3][1] + end * np.sin(theta)
        eeRadiusZ = cozum[0][3][2] + np.zeros_like(eeRadiusX)
        eeRadius, = self.axTra.plot(eeRadiusX, eeRadiusY, eeRadiusZ, color='blue')

        eeLine1X = [cozum[0][2][0],cozum[0][3][0]]
        eeLine1Y = [cozum[0][2][1],cozum[0][3][1]]
        eeLine1Z = [cozum[0][2][2],cozum[0][3][2]]
        eeLine1, = self.axTra.plot(eeLine1X, eeLine1Y, eeLine1Z, color="b", alpha=0.3)

        eeLine2X = [cozum[1][2][0],cozum[1][3][0]]
        eeLine2Y = [cozum[1][2][1],cozum[1][3][1]]
        eeLine2Z = [cozum[1][2][2],cozum[1][3][2]]
        eeLine2, = self.axTra.plot(eeLine2X, eeLine2Y, eeLine2Z, color="b", alpha=0.3)

        eeLine3X = [cozum[2][2][0],cozum[2][3][0]]
        eeLine3Y = [cozum[2][2][1],cozum[2][3][1]]
        eeLine3Z = [cozum[2][2][2],cozum[2][3][2]]
        eeLine3, = self.axTra.plot(eeLine3X, eeLine3Y, eeLine3Z, color="b", alpha=0.3)

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

            self.axAng.plot(num,planTableTheta[num][0],color='red')


            return line_bicep1, line_bicep2, line_bicep3, line_forearm1, line_forearm2, line_forearm3, eeDot, line_ee, eeLine1, eeLine2, eeLine3, endDotW

        dynamicInterval = 0
        self.ani = animation.FuncAnimation(self.figTra, update, frames=sutunSayisi, fargs=[line_bicep1, line_bicep2, line_bicep3, line_forearm1, line_forearm2, line_forearm3, eeDot, line_ee, eeLine1, eeLine2, eeLine3, endDotW], interval=dynamicInterval, blit=False, init_func=init)

        self.axTra.text(base,0,btf, f"{robotName}")
        self.axTra.view_init(elev=-145,azim=-145)
        self.axTra.set_xlabel('X')
        self.axTra.set_ylabel('Y')
        self.axTra.set_zlabel('Z')
        self.axTra.set_aspect('equal')
        self.canvasTra.draw()

        def init():
            self.axAng.set_ylim(-1.1, 1.1)
            self.axAng.set_xlim(0, 1)
            
            del x1data[:]
            del y1data[:]

            del x2data[:]
            del y2data[:]

            del x3data[:]
            del y3data[:]

            line1.set_data(x1data, y1data)
            line2.set_data(x2data, y2data)
            line3.set_data(x3data, y3data)

            self.figAng.legend(loc='upper left')

            return line1, line2, line3

        line1, = self.axAng.plot([], [], lw=2, color="red", label="θ1")
        line2, = self.axAng.plot([], [], lw=2, color="blue", label="θ2")
        line3, = self.axAng.plot([], [], lw=2, color="green", label="θ3")
        self.axAng.grid()
        x1data, y1data = [], []
        x2data, y2data = [], []
        x3data, y3data = [], []

        x1 = range(sutunSayisi)
        y1 = []
        for i in range(sutunSayisi):
            y1.append(planTableTheta[i][0])

        y2 = []
        for i in range(sutunSayisi):
            y2.append(planTableTheta[i][1])
        
        y3 = []
        for i in range(sutunSayisi):
            y3.append(planTableTheta[i][2])
        

        def run(data):

            self.label8.configure(text=str(self.roundoff(y1[data])))
            self.label10.configure(text=str(self.roundoff(y2[data])))
            self.label12.configure(text=str(self.roundoff(y3[data])))

            x1data.append(x1[data])
            y1data.append(y1[data])

            y2data.append(y2[data])
            y3data.append(y3[data])

            xmin, xmax = self.axAng.get_xlim()
            ymin, ymax = self.axAng.get_ylim()

            if x1[data] >= xmax or y2[data] >= ymax or y3[data] >= ymax:
                self.axAng.set_xlim(xmin, 1.1*xmax)
                self.axAng.figure.canvas.draw()

            if y1[data] >= ymax or y2[data] >= ymax or y3[data] >= ymax:
                self.axAng.set_ylim(ymin, 1.1*ymax)
                self.axAng.figure.canvas.draw()

            line1.set_data(x1data, y1data)
            line2.set_data(x1data, y2data)
            line3.set_data(x1data, y3data)
            
            return line1, line2, line3

        self.aniTheta = animation.FuncAnimation(self.figAng, run, interval=0, init_func=init, frames=sutunSayisi)

        self.canvasAng.draw()

        def initCoo():
            self.axCoo.set_ylim(-1.1, 1.1)
            self.axCoo.set_xlim(0, 1)
            
            del x1dataCoo[:]
            del y1dataCoo[:]

            del x2dataCoo[:]
            del y2dataCoo[:]

            del x3dataCoo[:]
            del y3dataCoo[:]

            line1Coo.set_data(x1dataCoo, y1dataCoo)
            line2Coo.set_data(x2dataCoo, y2dataCoo)
            line3Coo.set_data(x3dataCoo, y3dataCoo)

            self.figCoo.legend(loc='upper left')

            return line1Coo, line2Coo, line3Coo

        line1Coo, = self.axCoo.plot([], [], lw=2, color="red", label="Dx")
        line2Coo, = self.axCoo.plot([], [], lw=2, color="blue", label="Dy")
        line3Coo, = self.axCoo.plot([], [], lw=2, color="green", label="Dz")
        self.axCoo.grid()
        x1dataCoo, y1dataCoo = [], []
        x2dataCoo, y2dataCoo = [], []
        x3dataCoo, y3dataCoo = [], []

        x1Coo = range(sutunSayisi)
        y1Coo = []
        for i in range(sutunSayisi):
            y1Coo.append(trajectoryPlan[0][i])

        y2Coo = []
        for i in range(sutunSayisi):
            y2Coo.append(trajectoryPlan[1][i])
        
        y3Coo = []
        for i in range(sutunSayisi):
            y3Coo.append(trajectoryPlan[2][i])
        

        def runCoo(dataCoo):

            self.label2.configure(text=str(self.roundoff(y1Coo[dataCoo])))
            self.label4.configure(text=str(self.roundoff(y2Coo[dataCoo])))
            self.label6.configure(text=str(self.roundoff(y3Coo[dataCoo])))

            x1dataCoo.append(x1Coo[dataCoo])
            y1dataCoo.append(y1Coo[dataCoo])

            y2dataCoo.append(y2Coo[dataCoo])
            y3dataCoo.append(y3Coo[dataCoo])

            xminCoo, xmaxCoo = self.axCoo.get_xlim()
            yminCoo, ymaxCoo = self.axCoo.get_ylim()

            if x1Coo[dataCoo] >= xmaxCoo or y2[dataCoo] >= ymaxCoo or y3Coo[dataCoo] >= ymaxCoo:
                self.axCoo.set_xlim(xminCoo, 1.1*xmaxCoo)
                self.axCoo.figure.canvas.draw()

            if y1Coo[dataCoo] >= ymaxCoo or y2Coo[dataCoo] >= ymaxCoo or y3Coo[dataCoo] >= ymaxCoo:
                self.axCoo.set_ylim(yminCoo, 1.1*ymaxCoo)
                self.axCoo.figure.canvas.draw()
            
            if y1Coo[dataCoo] <= yminCoo or y2Coo[dataCoo] <= yminCoo or y3Coo[dataCoo] <= yminCoo:
                self.axCoo.set_ylim(1.1*yminCoo, ymaxCoo)
                self.axCoo.figure.canvas.draw()

            line1Coo.set_data(x1dataCoo, y1dataCoo)
            line2Coo.set_data(x1dataCoo, y2dataCoo)
            line3Coo.set_data(x1dataCoo, y3dataCoo)
            
            return line1Coo, line2Coo, line3Coo

        self.aniCoo = animation.FuncAnimation(self.figCoo, runCoo, interval=0, init_func=initCoo, frames=sutunSayisi)

        self.canvasCoo.draw()