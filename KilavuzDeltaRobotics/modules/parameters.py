import numpy as np
import tkinter as tk
from tkinter import ttk
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json

from modules.deltaRobot import deltaRobot

class Parameters():
    def createParamPage(self,tab):
        self.robotParams = ttk.LabelFrame(tab, text="ROBOT DIMENSIONS", padding=10)
        self.robotParams.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
            
        self.baseTitle=ttk.Label(self.robotParams,text="Base Radius (mm) :", font = ('Arial',12))
        self.baseTitle.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.baseEntry=ttk.Entry(self.robotParams, font = ('Arial',12), validate="key", validatecommand=self.vcmd)
        self.baseEntry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.bicepTitle=ttk.Label(self.robotParams,text="Bicep Lenght (mm) :", font = ('Arial',12))
        self.bicepTitle.grid(row=1, column=0, ipadx=10, ipady=10, sticky="ew")

        self.bicepEntry=ttk.Entry(self.robotParams, font = ('Arial',12), validate="key", validatecommand=self.vcmd)
        self.bicepEntry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.forearmTitle=ttk.Label(self.robotParams,text="Forearm Lenght (mm) :", font = ('Arial',12))
        self.forearmTitle.grid(row=2, column=0, ipadx=10, ipady=10, sticky="ew")

        self.forearmEntry=ttk.Entry(self.robotParams, font = ('Arial',12), validate="key", validatecommand=self.vcmd)
        self.forearmEntry.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        self.endTitle=ttk.Label(self.robotParams,text="End Eff. Radius (mm) :", font = ('Arial',12))
        self.endTitle.grid(row=3, column=0, ipadx=10, ipady=10, sticky="ew")

        self.endEntry=ttk.Entry(self.robotParams, font = ('Arial',12), validate="key", validatecommand=self.vcmd)
        self.endEntry.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        self.btfTitle=ttk.Label(self.robotParams,text="Base To Floor (mm) :", font = ('Arial',12))
        self.btfTitle.grid(row=4, column=0, ipadx=10, ipady=10, sticky="ew")

        self.btfEntry=ttk.Entry(self.robotParams, font = ('Arial',12), validate="key", validatecommand=self.vcmd)
        self.btfEntry.grid(row=4, column=1, padx=5, pady=5, sticky="w")

        self.eeOffsetTitle=ttk.Label(self.robotParams,text="EndEffector-Offset :", font = ('Arial',12))
        self.eeOffsetTitle.grid(row=5, column=0, ipadx=10, ipady=10, sticky="ew")

        self.eeOffsetEntry=ttk.Entry(self.robotParams, font = ('Arial',12), validate="key", validatecommand=self.vcmd)
        self.eeOffsetEntry.grid(row=5, column=1, padx=5, pady=5, sticky="w")

        self.separator = ttk.Separator(self.robotParams)
        self.separator.grid(row=0, column=2, rowspan=6, padx=10, pady=10, sticky="ns")

        self.turnAngleTitle=ttk.Label(self.robotParams,text="Motor Min. Angle (D) :", font = ('Arial',12))
        self.turnAngleTitle.grid(row=0, column=3, ipadx=10, ipady=10, sticky="ew")

        self.turnAngleEntry=ttk.Entry(self.robotParams, font = ('Arial',12), validate="key", validatecommand=self.vcmd)
        self.turnAngleEntry.grid(row=0, column=4, padx=5, pady=5, sticky="w")

        self.bicepPosAngleTitle=ttk.Label(self.robotParams,text="Motor Pos. Limit (D) :", font = ('Arial',12))
        self.bicepPosAngleTitle.grid(row=1, column=3, ipadx=10, ipady=10, sticky="ew")

        self.bicepPosAngleEntry=ttk.Entry(self.robotParams, font = ('Arial',12), validate="key", validatecommand=self.vcmd)
        self.bicepPosAngleEntry.grid(row=1, column=4, padx=5, pady=5, sticky="w")

        self.bicepNegAngleTitle=ttk.Label(self.robotParams,text="Motor Neg. Limit (D) :", font = ('Arial',12))
        self.bicepNegAngleTitle.grid(row=2, column=3, ipadx=10, ipady=10, sticky="ew")

        self.bicepNegAngleEntry=ttk.Entry(self.robotParams, font = ('Arial',12), validate="key", validatecommand=self.vcmd)
        self.bicepNegAngleEntry.grid(row=2, column=4, padx=5, pady=5, sticky="w")

        self.jointTitle=ttk.Label(self.robotParams,text="Joint Max. (D) :", font = ('Arial',12))
        self.jointTitle.grid(row=3, column=3, ipadx=10, ipady=10, sticky="ew")

        self.jointEntry=ttk.Entry(self.robotParams, font = ('Arial',12), validate="key", validatecommand=self.vcmd)
        self.jointEntry.grid(row=3, column=4, padx=5, pady=5, sticky="w")

        self.robotNameTitle=ttk.Label(self.robotParams,text="Robot Name :", font = ('Arial',12))
        self.robotNameTitle.grid(row=4, column=3, ipadx=10, ipady=10, sticky="ew")

        self.combo_list = [""]
        if os.path.exists("data/robots") and os.path.isdir("data/robots"):
            dosya_isimleri = [os.path.splitext(dosya)[0] for dosya in os.listdir("data/robots") if dosya.endswith(".json")]
            self.combo_list.extend(dosya_isimleri)
        self.combobox = ttk.Combobox(self.robotParams, values=self.combo_list, font = ('Arial',12), validate="key", validatecommand=self.vcmd2)
        self.combobox.current(0)
        self.combobox.grid(row=4, column=4, padx=5, pady=5, sticky="w")
        self.combobox.bind("<<ComboboxSelected>>", self.combobox_secildi)
        
        try:
            with open('data/myRobot.json', 'r') as dosya:
                    json_dosyası = dosya.read()
                    json_icerik = json.loads(json_dosyası)

            usedRobotName = json_icerik.get("robotName")
        except FileNotFoundError:
            usedRobotName = ""

        self.usedRobotTitle=ttk.Label(self.robotParams,text="Used Robot :", font = ('Arial',12))
        self.usedRobotTitle.grid(row=5, column=3, ipadx=10, ipady=10, sticky="ew")

        self.usedRobot=ttk.Label(self.robotParams,text=usedRobotName, font = ('Arial',12))
        self.usedRobot.grid(row=5, column=4, ipadx=10, ipady=10, sticky="w")
        
        self.tab1Buttons = ttk.Label(self.robotParams)
        self.tab1Buttons.grid(row=6, column=0, columnspan=5, padx=0, pady=0, sticky="nsew")

        self.delButton=ttk.Button(self.tab1Buttons, text="DELETE", style="Accent.TButton",command=self.deleteFunc)
        self.delButton.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.saveButton=ttk.Button(self.tab1Buttons, text="SAVE", style="Accent.TButton",command=self.saveFunc)
        self.saveButton.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.useButton=ttk.Button(self.tab1Buttons, text="USE", style="Accent.TButton",command=self.useFunc)
        self.useButton.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        self.figParam = plt.figure()
        self.axParam = self.figParam.add_subplot(111, projection='3d')
        self.canvasParam = FigureCanvasTkAgg(self.figParam, master=tab)
        self.canvasParam.get_tk_widget().grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self.axParam.set_xlabel('X')
        self.axParam.set_ylabel('Y')
        self.axParam.set_zlabel('Z')
        self.axParam.grid(False)

        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)
        tab.columnconfigure(1, weight=5)

        self.robotParams.columnconfigure(0, weight=1)
        self.robotParams.columnconfigure(1, weight=1)
        self.robotParams.columnconfigure(2, weight=1)
        self.robotParams.columnconfigure(3, weight=1)
        self.robotParams.rowconfigure(0, weight=1)
        self.robotParams.rowconfigure(1, weight=1)
        self.robotParams.rowconfigure(2, weight=1)
        self.robotParams.rowconfigure(3, weight=1)
        self.robotParams.rowconfigure(4, weight=1)
        self.robotParams.rowconfigure(5, weight=1)
        self.robotParams.rowconfigure(6, weight=1)

        self.tab1Buttons.columnconfigure(0, weight=1)
        self.tab1Buttons.columnconfigure(1, weight=1)
        self.tab1Buttons.columnconfigure(2, weight=1)
        self.tab1Buttons.rowconfigure(0, weight=1)

    def guncelle_combo_list(self):
        # "robots" klasöründeki .json uzantılı dosya isimlerini al
        robots_klasoru = "data/robots"
        if os.path.exists(robots_klasoru) and os.path.isdir(robots_klasoru):
            dosya_isimleri = [os.path.splitext(dosya)[0] for dosya in os.listdir(robots_klasoru) if
                              dosya.endswith(".json")]
            self.combo_list = [""] + dosya_isimleri
            self.combobox["values"] = self.combo_list

    def clearParamPage(self):
        self.baseEntry.config(validate="none")
        self.baseEntry.delete(0, tk.END)
        self.baseEntry.config(validate="key")

        self.bicepEntry.config(validate="none")
        self.bicepEntry.delete(0, tk.END)
        self.bicepEntry.config(validate="key")

        self.forearmEntry.config(validate="none")
        self.forearmEntry.delete(0, tk.END)
        self.forearmEntry.config(validate="key")
        
        self.endEntry.config(validate="none")
        self.endEntry.delete(0, tk.END)
        self.endEntry.config(validate="key")
        
        self.btfEntry.config(validate="none")
        self.btfEntry.delete(0, tk.END)
        self.btfEntry.config(validate="key")

        self.eeOffsetEntry.config(validate="none")
        self.eeOffsetEntry.delete(0, tk.END)
        self.eeOffsetEntry.config(validate="key")
        
        self.turnAngleEntry.config(validate="none")
        self.turnAngleEntry.delete(0, tk.END)
        self.turnAngleEntry.config(validate="key")
        
        self.bicepPosAngleEntry.config(validate="none")
        self.bicepPosAngleEntry.delete(0, tk.END)
        self.bicepPosAngleEntry.config(validate="key")
        
        self.bicepNegAngleEntry.config(validate="none")
        self.bicepNegAngleEntry.delete(0, tk.END)
        self.bicepNegAngleEntry.config(validate="key")
        
        self.jointEntry.config(validate="none")
        self.jointEntry.delete(0, tk.END)
        self.jointEntry.config(validate="key")

        

    def add_chars_to_entry(self, entry, strData):
        chars = list(strData)
        for char in chars:
            entry.insert(tk.END, char)

    def drawLineParam(self, startDot, endDot, lineColor="b",lineAlpha=1):
        self.axParam.plot([startDot[0], endDot[0]], [startDot[1], endDot[1]], [startDot[2], endDot[2]], color=lineColor, alpha=lineAlpha)

    def distance_3d(self,point1, point2):
        return np.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2 + (point2[2] - point1[2])**2)


    def paramGraph(self, robotName):
        self.axParam.cla()
        self.scatterParam = self.axParam.scatter(0, 0, 0, color="r", alpha=1)

        json_dosya_yolu = os.path.join("data/robots", f"{robotName}.json")

        # JSON dosyasına eriş
        try:
            with open(json_dosya_yolu, 'r') as dosya:
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
            print(f"{robotName}.json dosyası bulunamadı.")
        except Exception as e:
            print(f"Hata oluştu: {e}")
        
        theta = np.linspace(0, 2*np.pi, 100)
        x = base * np.cos(theta)
        y = base * np.sin(theta)
        z = np.zeros_like(x)
        self.axParam.plot(x, y, z, color="b")

        myRobot = deltaRobot(la = bicep, lb = forearm, ra = base, rb=end, btf=btf, minTurnAngle=turnAngle, cwMax=bicepPosAngle, ccwMax=-bicepNegAngle, jointMax=joint)
        cozum = myRobot.forwardKinematic(30,30,30)

        origin = [0, 0, 0]
        vektorler = [[(base/2), 0, 0], [0, (base/2), 0], [0, 0, (base/2)]]
        renkler = ['r', 'g', 'b']
        eksen_isimleri = ['X', 'Y', 'Z']

        for vektor, renk, isim in zip(vektorler, renkler, eksen_isimleri):
            self.axParam.quiver(*origin, *vektor, color=renk)
            self.axParam.text(origin[0] + vektor[0], origin[1] + vektor[1], origin[2] + vektor[2], isim)

        #Actuators
        self.axParam.scatter(cozum[0][0][0],cozum[0][0][1],cozum[0][0][2], color="b", alpha=1)
        self.drawLineParam([0,0,0],cozum[0][0], lineColor="b", lineAlpha=0.3)
        self.axParam.text(cozum[0][0][0], cozum[0][0][1], cozum[0][0][2]-10, "A1")

        self.axParam.scatter(cozum[1][0][0],cozum[1][0][1],cozum[1][0][2], color="b", alpha=1)
        self.drawLineParam([0,0,0],cozum[1][0], lineColor="b", lineAlpha=0.3)
        self.axParam.text(cozum[1][0][0], cozum[1][0][1], cozum[0][0][2]-10, "A2")

        self.axParam.scatter(cozum[2][0][0],cozum[2][0][1],cozum[2][0][2], color="b", alpha=1)
        self.drawLineParam([0,0,0],cozum[2][0], lineColor="b", lineAlpha=0.3)
        self.axParam.text(cozum[2][0][0], cozum[2][0][1], cozum[0][0][2]-10, "A3")

        cornerDis = self.distance_3d(cozum[0][0], cozum[1][0])

        corner1Y = cozum[0][0][1] + cornerDis
        corner2Y = cozum[0][0][1] - cornerDis
        corner3X = cozum[0][0][0] - np.sqrt(3) / 2 * (cornerDis*2)

        self.drawLineParam([cozum[0][0][0],corner1Y,cozum[0][0][2]],[cozum[0][0][0],corner2Y,cozum[0][0][2]],lineColor="r",lineAlpha=0.3)
        self.drawLineParam([cozum[0][0][0],corner1Y,cozum[0][0][2]],[corner3X,cozum[0][0][1],cozum[0][0][2]],lineColor="r",lineAlpha=0.3)
        self.drawLineParam([cozum[0][0][0],corner2Y,cozum[0][0][2]],[corner3X,cozum[0][0][1],cozum[0][0][2]],lineColor="r",lineAlpha=0.3)

        #BicepArms
        self.axParam.scatter(cozum[0][1][0],cozum[0][1][1],cozum[0][1][2], color="b", alpha=1)
        self.drawLineParam(cozum[0][0],cozum[0][1], lineColor="b")

        self.axParam.scatter(cozum[1][1][0],cozum[1][1][1],cozum[1][1][2], color="b", alpha=1)
        self.drawLineParam(cozum[1][0],cozum[1][1], lineColor="b")

        self.axParam.scatter(cozum[2][1][0],cozum[2][1][1],cozum[2][1][2], color="b", alpha=1)
        self.drawLineParam(cozum[2][0],cozum[2][1], lineColor="b")

        #Forearms
        self.axParam.scatter(cozum[0][2][0],cozum[0][2][1],cozum[0][2][2], color="b", alpha=1)
        self.drawLineParam(cozum[0][1],cozum[0][2], lineColor="b")
        self.drawLineParam(cozum[0][2],cozum[0][3], lineColor="b", lineAlpha=0.3)

        self.axParam.scatter(cozum[1][2][0],cozum[1][2][1],cozum[1][2][2], color="b", alpha=1)
        self.drawLineParam(cozum[1][1],cozum[1][2], lineColor="b")
        self.drawLineParam(cozum[1][2],cozum[0][3], lineColor="b", lineAlpha=0.3)

        self.axParam.scatter(cozum[2][2][0],cozum[2][2][1],cozum[2][2][2], color="b", alpha=1)
        self.drawLineParam(cozum[2][1],cozum[2][2], lineColor="b")
        self.drawLineParam(cozum[2][2],cozum[0][3], lineColor="b", lineAlpha=0.3)

        #eeOffset
        self.axParam.scatter(cozum[0][3][0], cozum[0][3][1], (cozum[0][3][2] + eeOffset), color="g", alpha=1)
        self.drawLineParam(cozum[0][3],[cozum[0][3][0],cozum[0][3][1],(cozum[0][3][2]+eeOffset)], lineColor="g")

        #EndEffector
        x = cozum[0][3][0] + end * np.cos(theta)
        y = cozum[0][3][1] + end * np.sin(theta)
        z = cozum[0][3][2] + np.zeros_like(x)
        self.axParam.plot(x, y, z, color="b")

        cornerDis = self.distance_3d(cozum[0][2], cozum[1][2])

        corner1Y = cozum[0][2][1] + cornerDis
        corner2Y = cozum[0][2][1] - cornerDis
        corner3X = cozum[0][2][0] - np.sqrt(3) / 2 * (cornerDis*2)

        #self.drawLineParam([cozum[0][2][0],corner1Y,cozum[0][2][2]],[cozum[0][2][0],corner2Y,cozum[0][2][2]],lineColor="r",lineAlpha=0.3)
        #self.drawLineParam([cozum[0][2][0],corner1Y,cozum[0][2][2]],[corner3X,cozum[0][2][1],cozum[0][2][2]],lineColor="r",lineAlpha=0.3)
        #self.drawLineParam([cozum[0][2][0],corner2Y,cozum[0][2][2]],[corner3X,cozum[0][2][1],cozum[0][2][2]],lineColor="r",lineAlpha=0.3)

        self.axParam.scatter(cozum[0][3][0],cozum[0][3][1],cozum[0][3][2], color="r", alpha=1)
        
        #Floor
        Z = np.full((10, 10), 240)  # 10x10 boyutunda tamamı 240 olan bir array oluştur
        x = np.linspace(-base*2, base*2, 10)
        y = np.linspace(-base*2, base*2, 10)
        X, Y = np.meshgrid(x, y)
        self.axParam.plot_surface(X, Y, Z, color='g', alpha=0.2)

        
        self.axParam.text(base,0,btf, f"{robotName}")

        self.axParam.set_xlim3d((-base*2),(base*2))
        self.axParam.set_ylim3d((-base*2),(base*2))
        self.axParam.set_zlim3d((-10),(btf))
        self.axParam.grid(False)
        self.axParam.view_init(elev=-145,azim=-145)
        self.axParam.set_xlabel('X')
        self.axParam.set_ylabel('Y')
        self.axParam.set_zlabel('Z')
        self.canvasParam.draw()

    def clear_3d_graph(self):
        if self.scatterParam is not None:  # scatter_plot değişkeni boş değilse
            self.axParam.cla()  # Scatter plot öğesini kaldır
            self.canvasParam.draw()  # Grafiği güncelle

    def combobox_secildi(self, event):
        secilen_robot = self.combobox.get()

        self.clearParamPage()

        # Boş bir seçim yapılmış mı kontrol et
        if not secilen_robot:
            self.clear_3d_graph()
            return

        # JSON dosyasının tam yolu
        json_dosya_yolu = os.path.join("data/robots", f"{secilen_robot}.json")

        # JSON dosyasına eriş
        try:
            with open(json_dosya_yolu, 'r') as dosya:
                json_dosyası = dosya.read()
                json_icerik = json.loads(json_dosyası)
                self.add_chars_to_entry(self.baseEntry,json_icerik.get("base"))
                self.add_chars_to_entry(self.bicepEntry,json_icerik.get("bicep"))
                self.add_chars_to_entry(self.forearmEntry, json_icerik.get("forearm"))
                self.add_chars_to_entry(self.endEntry, json_icerik.get("end"))
                self.add_chars_to_entry(self.btfEntry, json_icerik.get("btf"))
                self.add_chars_to_entry(self.eeOffsetEntry, json_icerik.get("eeOffset"))
                self.add_chars_to_entry(self.turnAngleEntry, json_icerik.get("turnAngle"))
                self.add_chars_to_entry(self.bicepPosAngleEntry, json_icerik.get("bicepPosAngle"))
                self.add_chars_to_entry(self.bicepNegAngleEntry, json_icerik.get("bicepNegAngle"))
                self.add_chars_to_entry(self.jointEntry, json_icerik.get("joint"))
        except FileNotFoundError:
            print(f"{secilen_robot}.json dosyası bulunamadı.")
        except Exception as e:
            print(f"Hata oluştu: {e}")

        self.paramGraph(secilen_robot)
        

    def deleteFunc(self):
        robotName = self.combobox.get()
        self.clearParamPage()
        if robotName == "":
            raise ValueError
        self.combobox.current(0)
        
        dosya_adi = "data/robots/" +  robotName + ".json"
        os.remove(dosya_adi)

        self.guncelle_combo_list()
        self.clear_3d_graph()

    def saveFunc(self):
        try:
            base = float(self.baseEntry.get())
            bicep = float(self.bicepEntry.get())
            forearm = float(self.forearmEntry.get())
            end = float(self.endEntry.get())
            btf = float(self.btfEntry.get())
            eeOffset = float(self.eeOffsetEntry.get())
            turnAngle = float(self.turnAngleEntry.get())    
            bicepPosAngle = float(self.bicepPosAngleEntry.get())
            bicepNegAngle = float(self.bicepNegAngleEntry.get())
            joint = float(self.jointEntry.get())
            robotName = self.combobox.get()

            myRobot = deltaRobot(la = bicep, lb = forearm, ra = base, rb=end, btf=btf, minTurnAngle=turnAngle, cwMax=bicepPosAngle, ccwMax=-bicepNegAngle, jointMax=joint)
            cozum = myRobot.forwardKinematic(0,0,0)
            if cozum == False:
                raise ValueError

            if base == 0 or bicep == 0 or forearm == 0 or end == 0 or btf == 0 or turnAngle == 0 or bicepPosAngle == 0 or bicepNegAngle == 0 or joint == 0 or robotName == "":
                raise ValueError

            veri = {
            "base": self.baseEntry.get(),
            "bicep": self.bicepEntry.get(),
            "forearm": self.forearmEntry.get(),
            "end": self.endEntry.get(),
            "btf": self.btfEntry.get(),
            "eeOffset": self.eeOffsetEntry.get(),
            "turnAngle": self.turnAngleEntry.get(),
            "bicepPosAngle": self.bicepPosAngleEntry.get(),
            "bicepNegAngle": self.bicepNegAngleEntry.get(),
            "joint": self.jointEntry.get(),
            "robotName": robotName,
            }

            dosyaAdi =  'data/robots/' + robotName + '.json'

            with open(dosyaAdi, 'w') as dosya:
                json.dump(veri, dosya, indent=2)

            self.guncelle_combo_list()

        except ValueError:
            title = "HATA!"
            message = "Robot parametreleri anlamsız lütfen kontrol edin!"
            messagebox.showerror(title, message)

    def useFunc(self):
        try:
            base = float(self.baseEntry.get())
            bicep = float(self.bicepEntry.get())
            forearm = float(self.forearmEntry.get())
            end = float(self.endEntry.get())
            btf = float(self.btfEntry.get())
            eeOffset = float(self.eeOffsetEntry.get())
            turnAngle = float(self.turnAngleEntry.get())    
            bicepPosAngle = float(self.bicepPosAngleEntry.get())
            bicepNegAngle = float(self.bicepNegAngleEntry.get())
            joint = float(self.jointEntry.get())
            robotName = self.combobox.get()

            myRobot = deltaRobot(la = bicep, lb = forearm, ra = base, rb=end, btf=btf, minTurnAngle=turnAngle, cwMax=bicepPosAngle, ccwMax=-bicepNegAngle, jointMax=joint)
            cozum = myRobot.forwardKinematic(0,0,0)
            if cozum == False:
                raise ValueError

            if base == 0 or bicep == 0 or forearm == 0 or end == 0 or btf == 0 or turnAngle == 0 or bicepPosAngle == 0 or bicepNegAngle == 0 or joint == 0 or robotName == "":
                raise ValueError

            veri = {
            "base": base,
            "bicep": bicep,
            "forearm": forearm,
            "end": end,
            "btf": btf,
            "eeOffset": eeOffset,
            "turnAngle": turnAngle,
            "bicepPosAngle": bicepPosAngle,
            "bicepNegAngle": bicepNegAngle,
            "joint": joint,
            "robotName": robotName,
            }

            dosyaAdi =  'data/myRobot' + '.json'

            with open(dosyaAdi, 'w') as dosya:
                json.dump(veri, dosya, indent=2)

            self.saveFunc()
            self.usedRobot.config(text=robotName)

        except ValueError:
            title = "HATA!"
            message = "Robot parametreleri anlamsız lütfen kontrol edin!"
            messagebox.showerror(title, message)