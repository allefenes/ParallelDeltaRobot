import numpy as np

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
import itertools

import os
import json

from deltaRobot import deltaRobot

class App(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(self)

        # Set a minsize for the window, and place it in the middle
        root.update()
        root.minsize(root.winfo_width(), root.winfo_height())
        x_cordinate = int((root.winfo_screenwidth() / 2) - (root.winfo_width() / 2))
        y_cordinate = int((root.winfo_screenheight() / 2) - (root.winfo_height() / 2))
        root.geometry("+{}+{}".format(x_cordinate, y_cordinate-20))

        self.themeChoose = tk.IntVar()
        self.themeChoose.set(0)

        def validate_input(char, entry_value):
            return char.isdigit() or char == "" or char == '.'

        def validate_input_char(char, entry_value):
            return char.isalpha()
        

        self.vcmd = (root.register(validate_input), "%S", "%P")

        self.vcmd2= (root.register(validate_input_char), "%S", "%P")

        self.FontSize = 16 
        self.FontType = 'Arial'
        self.updateStyles()

        # Create widgets :)
        self.setup_widgets()

    def updateStyles(self):
        # Stilleri güncelle
        style = ttk.Style()
        style.configure('Accent.TButton', font=(self.FontType, self.FontSize))
        style.configure('Label', font=(self.FontType, self.FontSize))

    def quit_application(self, event):
        root.quit()

    def toggle_maximize(self, event):
        current_state = root.wm_state()

        if current_state == "normal":  # Eğer pencere normal durumdaysa
            root.wm_state("zoomed")  # Maximize et
        elif current_state == "zoomed":  # Eğer pencere maximize durumdaysa
            root.wm_state("normal")  # Minimize et

    def setup_widgets(self):
        
        #self.windowBar()

        tab_control = ttk.Notebook(self)

        tab1 = ttk.Frame(tab_control)
        tab2 = ttk.Frame(tab_control)
        tab3 = ttk.Frame(tab_control)
        tab4 = ttk.Frame(tab_control)

        tab_control.add(tab1, text='ROBOT')
        tab_control.add(tab2, text='KINEMATIC')
        tab_control.add(tab3, text='TRAJECTORY')
        tab_control.add(tab4, text='INFO')

        self.parametreler(tab1)
        self.kinematikHesaplayici(tab2)
        self.yorunge(tab3)
        self.hakkimizda(tab4)

        tab_control.pack(side="bottom",fill="both", expand=True)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

    def windowBar(self):
        bar = tk.Frame(self, height=32, bg='#1A171B')
        bar.pack(side="top", fill="x")

        self.icon1 = tk.PhotoImage(file='logo/barLogo.png')
        self.mainLogo = tk.Label(bar, image=self.icon1, bg='#1A171B')
        self.mainLogo.pack(side="left", anchor="w", padx=5)

        self.mainTitle = tk.Label(bar, text="DELTA ROBOTICS", font = ('Arial',12), bg='#1A171B')
        self.mainTitle.pack(side="left", anchor="w",padx=10)

        self.icon2 = tk.PhotoImage(file='logo/close.png')
        self.closeButton = tk.Label(bar, image=self.icon2, bg='#1A171B')
        self.closeButton.pack(side="right", anchor="e")
        self.closeButton.bind("<Button-1>", self.quit_application)

        self.icon3 = tk.PhotoImage(file='logo/max.png')
        self.maxButton = tk.Label(bar, image=self.icon3, bg='#1A171B')
        self.maxButton.pack(side="right", anchor="e")
        self.maxButton.bind("<Button-1>", self.toggle_maximize)

        self.icon4 = tk.PhotoImage(file='logo/down.png')
        self.downButton = tk.Label(bar, image=self.icon4, bg='#1A171B')
        self.downButton.pack(side="right", anchor="e")
        self.downButton.bind("<Button-1>", self.iconify_window)

        self.icon1_reference = self.icon1
        self.icon2_reference = self.icon2
        self.icon3_reference = self.icon3
        self.icon4_reference = self.icon4

    def quit_application(self, event):
        root.quit()

    def toggle_maximize(self, event):
        current_state = root.wm_state()

        if current_state == "normal":  # Eğer pencere normal durumdaysa
            root.wm_state("zoomed")  # Maximize et
        elif current_state == "zoomed":  # Eğer pencere maximize durumdaysa
            root.wm_state("normal")  # Minimize et

    def iconify_window(self, event):
        root.iconify()

    def parametreler(self,tab):
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
        if os.path.exists("robots") and os.path.isdir("robots"):
            dosya_isimleri = [os.path.splitext(dosya)[0] for dosya in os.listdir("robots") if dosya.endswith(".json")]
            self.combo_list.extend(dosya_isimleri)
        self.combobox = ttk.Combobox(self.robotParams, values=self.combo_list, font = ('Arial',12), validate="key", validatecommand=self.vcmd2)
        self.combobox.current(0)
        self.combobox.grid(row=4, column=4, padx=5, pady=5, sticky="w")
        self.combobox.bind("<<ComboboxSelected>>", self.combobox_secildi)
        
        try:
            with open('myRobot.json', 'r') as dosya:
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
        robots_klasoru = "robots"
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

        json_dosya_yolu = os.path.join("robots", f"{robotName}.json")

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
        json_dosya_yolu = os.path.join("robots", f"{secilen_robot}.json")

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
        
        dosya_adi = "robots/" +  robotName + ".json"
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

            dosyaAdi =  'robots/' + robotName + '.json'

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

            dosyaAdi =  'myRobot' + '.json'

            with open(dosyaAdi, 'w') as dosya:
                json.dump(veri, dosya, indent=2)

            self.saveFunc()
            self.usedRobot.config(text=robotName)

        except ValueError:
            title = "HATA!"
            message = "Robot parametreleri anlamsız lütfen kontrol edin!"
            messagebox.showerror(title, message)

    def kinematikHesaplayici(self,tab):

        self.ileriKinematik = ttk.LabelFrame(tab, text="FORWARD KINEMATIC")
        self.ileriKinematik.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.ileriKinematik.grid_propagate(False)

        #Teta açıları girişleri için başlıklar
        self.ileriBeta1Title = ttk.Label(self.ileriKinematik, text="θ1 :  ", font = ('Arial',14))
        self.ileriBeta1Title.grid(row=0, column=0, padx=0, pady=0, sticky="e")

        self.ileriBeta2Title = ttk.Label(self.ileriKinematik, text="θ2 :  ", font = ('Arial',14))
        self.ileriBeta2Title.grid(row=1, column=0, padx=0, pady=0, sticky="e")

        self.ileriBeta3Title = ttk.Label(self.ileriKinematik, text="θ3 :  ", font = ('Arial',14))
        self.ileriBeta3Title.grid(row=2, column=0, padx=0, pady=0, sticky="e")

        #Teta açıları girişleri için entryler
        self.ileriEntryT1 = ttk.Entry(self.ileriKinematik, validate="key", validatecommand=self.vcmd)
        self.ileriEntryT1.grid(row=0, column=1, padx=0, pady=0, sticky="w")

        self.ileriEntryT2 = ttk.Entry(self.ileriKinematik, validate="key", validatecommand=self.vcmd)
        self.ileriEntryT2.grid(row=1, column=1, padx=0, pady=0, sticky="w")
        
        self.ileriEntryT3 = ttk.Entry(self.ileriKinematik, validate="key", validatecommand=self.vcmd)
        self.ileriEntryT3.grid(row=2, column=1, padx=0, pady=0, sticky="w")

        #Beta açıları sonuçları için gerekli labellar
        self.ileriBeta1Title = ttk.LabelFrame(self.ileriKinematik, text="β1")
        self.ileriBeta1Title.grid(row=0, column=2, padx=10, pady=10)

        self.ileriBeta1res = ttk.Label(self.ileriBeta1Title, text="β", font = ('Arial',14))
        self.ileriBeta1res.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.ileriBeta2Title = ttk.LabelFrame(self.ileriKinematik, text="β2")
        self.ileriBeta2Title.grid(row=1, column=2, padx=10, pady=10)

        self.ileriBeta2res = ttk.Label(self.ileriBeta2Title, text="β", font = ('Arial',14))
        self.ileriBeta2res.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.ileriBeta3Title = ttk.LabelFrame(self.ileriKinematik, text="β3")
        self.ileriBeta3Title.grid(row=2, column=2, padx=10, pady=10)

        self.ileriBeta3res = ttk.Label(self.ileriBeta3Title, text="β", font = ('Arial',14))
        self.ileriBeta3res.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        #Phi açıları sonuçları için gerekli labellar
        self.ileriPhi1Title = ttk.LabelFrame(self.ileriKinematik, text="φ1")
        self.ileriPhi1Title.grid(row=0, column=3, padx=10, pady=10)

        self.ileriPhi1res = ttk.Label(self.ileriPhi1Title, text="φ", font = ('Arial',14))
        self.ileriPhi1res.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        self.ileriPhi2Title = ttk.LabelFrame(self.ileriKinematik, text="φ2")
        self.ileriPhi2Title.grid(row=1, column=3, padx=10, pady=10)

        self.ileriPhi2res = ttk.Label(self.ileriPhi2Title, text="φ", font = ('Arial',14))
        self.ileriPhi2res.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        self.ileriPhi3Title = ttk.LabelFrame(self.ileriKinematik, text="φ3")
        self.ileriPhi3Title.grid(row=2, column=3, padx=10, pady=10)

        self.ileriPhi3res = ttk.Label(self.ileriPhi3Title, text="φ", font = ('Arial',14))
        self.ileriPhi3res.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        #İleri Kinematik Gama açıları için gerekli labellar
        self.ileriGama1Title = ttk.LabelFrame(self.ileriKinematik, text="γ1")
        self.ileriGama1Title.grid(row=0, column=4, padx=10, pady=10)

        self.ileriGama1res = ttk.Label(self.ileriGama1Title, text="γ", font = ('Arial',14))
        self.ileriGama1res.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        self.ileriGama2Title = ttk.LabelFrame(self.ileriKinematik, text="γ2")
        self.ileriGama2Title.grid(row=1, column=4, padx=10, pady=10)

        self.ileriGama2res = ttk.Label(self.ileriGama2Title, text="γ", font = ('Arial',14))
        self.ileriGama2res.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        self.ileriGama3Title = ttk.LabelFrame(self.ileriKinematik, text="γ3")
        self.ileriGama3Title.grid(row=2, column=4, padx=10, pady=10)

        self.ileriGama3res = ttk.Label(self.ileriGama3Title, text="γ", font = ('Arial',14))
        self.ileriGama3res.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        #xyz değerleri için gerekli labellar
        self.ileriXTitle = ttk.LabelFrame(self.ileriKinematik, text="X")
        self.ileriXTitle.grid(row=0, column=5, padx=10, pady=10)

        self.ileriXRes = ttk.Label(self.ileriXTitle, text="X", font = ('Arial',14))
        self.ileriXRes.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        self.ileriYTitle = ttk.LabelFrame(self.ileriKinematik, text="Y")
        self.ileriYTitle.grid(row=1, column=5, padx=10, pady=10)

        self.ileriYRes = ttk.Label(self.ileriYTitle, text="Y", font = ('Arial',14))
        self.ileriYRes.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        self.ileriZTitle = ttk.LabelFrame(self.ileriKinematik, text="Z")
        self.ileriZTitle.grid(row=2, column=5, padx=10, pady=10)

        self.ileriZRes = ttk.Label(self.ileriZTitle, text="Z", font = ('Arial',14))
        self.ileriZRes.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        self.forwardButtons = ttk.Label(self.ileriKinematik)
        self.forwardButtons.grid(row=3, column=0, columnspan=6, padx=0, pady=0,  sticky="nsew")

        self.ileriAccentbutton1 = ttk.Button(self.forwardButtons, text="CALCULATE", style="Accent.TButton", command=self.ileriKinematikHesapla)
        self.ileriAccentbutton1.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.ileriAccentbutton2 = ttk.Button(self.forwardButtons, text="CLEAR", style="Accent.TButton", command=self.ileriKinematikTemizle)
        self.ileriAccentbutton2.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
       
        #TERS KİNEMATİK SEKME İÇİN

        self.tersKinematik = ttk.LabelFrame(tab, text="INVERSE KINEMATIC")
        self.tersKinematik.grid(row=0, column=1, padx=(10, 10), pady=10, sticky="nsew")
        self.tersKinematik.grid_propagate(False)

        #Entry başlıkları
        self.tersXEntryTitle = ttk.Label(self.tersKinematik, text="X :  ", font = ('Arial',14))
        self.tersXEntryTitle.grid(row=0, column=0, padx=0, pady=0, sticky="e")

        self.tersYEntryTitle = ttk.Label(self.tersKinematik, text="Y :  ", font = ('Arial',14))
        self.tersYEntryTitle.grid(row=1, column=0, padx=0, pady=0, sticky="e")

        self.tersZEntryTitle = ttk.Label(self.tersKinematik, text="Z :  ", font = ('Arial',14))
        self.tersZEntryTitle.grid(row=2, column=0, padx=0, pady=0, sticky="e")

        #xyz entryleri
        self.tersEntryX = ttk.Entry(self.tersKinematik, validate="key", validatecommand=self.vcmd)
        self.tersEntryX.grid(row=0, column=1, padx=0, pady=0, sticky="w")

        self.tersEntryY = ttk.Entry(self.tersKinematik, validate="key", validatecommand=self.vcmd)
        self.tersEntryY.grid(row=1, column=1, padx=0, pady=0, sticky="w")
        
        self.tersEntryZ = ttk.Entry(self.tersKinematik, validate="key", validatecommand=self.vcmd)
        self.tersEntryZ.grid(row=2, column=1, padx=0, pady=0, sticky="w")

        #ters kinematik beta titlelar
        self.tersBeta1Title = ttk.LabelFrame(self.tersKinematik, text="β1")
        self.tersBeta1Title.grid(row=0, column=2, padx=10, pady=10)

        self.tersBeta1res = ttk.Label(self.tersBeta1Title, text="β", font = ('Arial',14))
        self.tersBeta1res.grid(row=0, column=0, padx=5, pady=5,  sticky="new")

        self.tersBeta2Title = ttk.LabelFrame(self.tersKinematik, text="β2")
        self.tersBeta2Title.grid(row=1, column=2, padx=10, pady=10)

        self.tersBeta2res = ttk.Label(self.tersBeta2Title, text="β", font = ('Arial',14))
        self.tersBeta2res.grid(row=0, column=0, padx=5, pady=5,  sticky="new")

        self.tersBeta3Title = ttk.LabelFrame(self.tersKinematik, text="β3")
        self.tersBeta3Title.grid(row=2, column=2, padx=10, pady=10)

        self.tersBeta3res = ttk.Label(self.tersBeta3Title, text="β", font = ('Arial',14))
        self.tersBeta3res.grid(row=0, column=0, padx=5, pady=5,  sticky="new")

        #ters kinematik phi titlelar
        self.tersPhi1Title = ttk.LabelFrame(self.tersKinematik, text="φ1")
        self.tersPhi1Title.grid(row=0, column=3, padx=10, pady=10)

        self.tersPhi1res = ttk.Label(self.tersPhi1Title, text="φ", font = ('Arial',14))
        self.tersPhi1res.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        self.tersPhi2Title = ttk.LabelFrame(self.tersKinematik, text="φ2")
        self.tersPhi2Title.grid(row=1, column=3, padx=10, pady=10)

        self.tersPhi2res = ttk.Label(self.tersPhi2Title, text="φ", font = ('Arial',14))
        self.tersPhi2res.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        self.tersPhi3Title = ttk.LabelFrame(self.tersKinematik, text="φ3")
        self.tersPhi3Title.grid(row=2, column=3, padx=10, pady=10)

        self.tersPhi3res = ttk.Label(self.tersPhi3Title, text="φ", font = ('Arial',14))
        self.tersPhi3res.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        #Ters Kinematik Gama açıları için gerekli labellar
        self.tersGama1Title = ttk.LabelFrame(self.tersKinematik, text="γ1")
        self.tersGama1Title.grid(row=0, column=4, padx=10, pady=10)

        self.tersGama1res = ttk.Label(self.tersGama1Title, text="γ", font = ('Arial',14))
        self.tersGama1res.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        self.tersGama2Title = ttk.LabelFrame(self.tersKinematik, text="γ2")
        self.tersGama2Title.grid(row=1, column=4, padx=10, pady=10)

        self.tersGama2res = ttk.Label(self.tersGama2Title, text="γ", font = ('Arial',14))
        self.tersGama2res.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        self.tersGama3Title = ttk.LabelFrame(self.tersKinematik, text="γ3")
        self.tersGama3Title.grid(row=2, column=4, padx=10, pady=10)

        self.tersGama3res = ttk.Label(self.tersGama3Title, text="γ", font = ('Arial',14))
        self.tersGama3res.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        #ters kinematik x titlelar
        self.tersT1Title = ttk.LabelFrame(self.tersKinematik, text="θ1")
        self.tersT1Title.grid(row=0, column=5, padx=10, pady=10)

        self.tersT1Res = ttk.Label(self.tersT1Title, text="θ", font = ('Arial',14))
        self.tersT1Res.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        self.tersT2Title = ttk.LabelFrame(self.tersKinematik, text="θ2")
        self.tersT2Title.grid(row=1, column=5, padx=10, pady=10)

        self.tersT2Res = ttk.Label(self.tersT2Title, text="θ", font = ('Arial',14))
        self.tersT2Res.grid(row=0, column=0, padx=5, pady=5,  sticky="nsew")

        self.tersT3Title = ttk.LabelFrame(self.tersKinematik, text="θ3")
        self.tersT3Title.grid(row=2, column=5, padx=10, pady=10)

        self.tersT3Res = ttk.Label(self.tersT3Title, text="θ", font = ('Arial',14))
        self.tersT3Res.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        #Ters Kinematik Butonlar

        self.inverseButtons = ttk.Label(self.tersKinematik)
        self.inverseButtons.grid(row=3, column=0, columnspan=6, padx=0, pady=0,  sticky="nsew")

        self.tersAccentbutton1 = ttk.Button(self.inverseButtons, text="CALCULATE", style="Accent.TButton", command=self.tersKinematikHesapla)
        self.tersAccentbutton1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.tersAccentbutton2 = ttk.Button(self.inverseButtons, text="CLEAR", style="Accent.TButton", command=self.tersKinematikTemizle)
        self.tersAccentbutton2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)

        self.ileriKinematik.columnconfigure(0, weight=1)
        self.ileriKinematik.rowconfigure(0, weight=1)
        self.ileriKinematik.columnconfigure(1, weight=1)
        self.ileriKinematik.rowconfigure(1, weight=1)
        self.ileriKinematik.columnconfigure(2, weight=1)
        self.ileriKinematik.rowconfigure(2, weight=1)
        self.ileriKinematik.columnconfigure(3, weight=1)
        self.ileriKinematik.columnconfigure(4, weight=1)
        self.ileriKinematik.columnconfigure(5, weight=1)

        self.tersKinematik.columnconfigure(0, weight=1)
        self.tersKinematik.rowconfigure(0, weight=1)
        self.tersKinematik.columnconfigure(1, weight=1)
        self.tersKinematik.rowconfigure(1, weight=1)
        self.tersKinematik.columnconfigure(2, weight=1)
        self.tersKinematik.rowconfigure(2, weight=1)
        self.tersKinematik.columnconfigure(3, weight=1)
        self.tersKinematik.columnconfigure(4, weight=1)
        self.tersKinematik.columnconfigure(5, weight=1)

        self.inverseButtons.columnconfigure(0, weight=1)
        self.inverseButtons.columnconfigure(1, weight=1)

        self.forwardButtons.columnconfigure(0, weight=1)
        self.forwardButtons.columnconfigure(1, weight=1)
        

    def roundoff(self,x, y=2):
        z = 10 ** y
        return round(x * z) / z

    def ileriKinematikHesapla(self):
        try:
            teta1 = float(self.ileriEntryT1.get())
            teta2 = float(self.ileriEntryT2.get())
            teta3 = float(self.ileriEntryT3.get())

        except ValueError:
            title = "Hata!"
            message = "Teta Değerleri Anlamsız Kontrol ediniz!"
            messagebox.showerror(title, message)

        try:
            with open('myRobot.json', 'r') as dosya:
                json_dosyası = dosya.read()
                json_icerik = json.loads(json_dosyası)

        except FileNotFoundError:
            print("myRobot.json dosyası bulunamadı.")
        except Exception as e:
            print(f"Hata oluştu: {e}")

        try:
            base = json_icerik.get("base")
            bicep = json_icerik.get("bicep")
            forearm = json_icerik.get("forearm")
            end = json_icerik.get("end")
            btf = json_icerik.get("btf")
            eeOffset = json_icerik.get("eeOffset")
            turnAngle =  json_icerik.get("turnAngle")
            bicepPosAngle = json_icerik.get("bicepPosAngle")
            bicepNegAngle = json_icerik.get("bicepNegAngle")
            joint = json_icerik.get("joint")
            robotName = json_icerik.get("robotName")

            myRobot = deltaRobot(la = bicep, lb = forearm, ra = base, rb=end, btf=btf, minTurnAngle=turnAngle, cwMax=bicepPosAngle, ccwMax=-bicepNegAngle, jointMax=joint)
            cozum = myRobot.forwardKinematic(teta1, teta2, teta3)

            self.ileriBeta1res.config(text=str(self.roundoff(x=cozum[0][4])))
            self.ileriBeta2res.config(text=str(self.roundoff(x=cozum[1][4])))
            self.ileriBeta3res.config(text=str(self.roundoff(x=cozum[2][4])))

            self.ileriPhi1res.config(text=str(self.roundoff(x=cozum[0][5])))
            self.ileriPhi2res.config(text=str(self.roundoff(x=cozum[1][5])))
            self.ileriPhi3res.config(text=str(self.roundoff(x=cozum[2][5])))

            self.ileriGama1res.config(text=str(self.roundoff(x=cozum[0][6])))
            self.ileriGama2res.config(text=str(self.roundoff(x=cozum[1][6])))
            self.ileriGama3res.config(text=str(self.roundoff(x=cozum[2][6])))

            self.ileriXRes.config(text=str(self.roundoff(x=cozum[0][3][0])))
            self.ileriYRes.config(text=str(self.roundoff(x=cozum[1][3][1])))
            self.ileriZRes.config(text=str(self.roundoff(x=cozum[2][3][2] + eeOffset)))
        
        except TypeError:
            title = "Hata!"
            message = f"{robotName} : Tanımladığınız Robotun Çalışma Alanı Dışında Bir Nokta Girdiniz!"
            messagebox.showerror(title, message)

    def ileriKinematikTemizle(self):
        self.ileriEntryT1.delete(0, "end")
        self.ileriEntryT2.delete(0, "end")
        self.ileriEntryT3.delete(0, "end")

        self.ileriBeta1res.config(text="β")
        self.ileriBeta2res.config(text="β")
        self.ileriBeta3res.config(text="β")

        self.ileriPhi1res.config(text="φ")
        self.ileriPhi2res.config(text="φ")
        self.ileriPhi3res.config(text="φ")

        self.ileriGama1res.config(text="γ")
        self.ileriGama2res.config(text="γ")
        self.ileriGama3res.config(text="γ")

        self.ileriXRes.config(text="X")
        self.ileriYRes.config(text="Y")
        self.ileriZRes.config(text="Z")

    def tersKinematikHesapla(self):
        try:
            x = float(self.tersEntryX.get())
            y = float(self.tersEntryY.get())
            z = float(self.tersEntryZ.get())
        except ValueError:
            title = "Hata!"
            message = "XYZ Değerleri Anlamsız Kontrol ediniz!"
            messagebox.showerror(title, message)

        try:
            with open('myRobot.json', 'r') as dosya:
                json_dosyası = dosya.read()
                json_icerik = json.loads(json_dosyası)

        except FileNotFoundError:
            print("myRobot.json dosyası bulunamadı.")
        except Exception as e:
            print(f"Hata oluştu: {e}")
        
        try:
            base = json_icerik.get("base")
            bicep = json_icerik.get("bicep")
            forearm = json_icerik.get("forearm")
            end = json_icerik.get("end")
            btf = json_icerik.get("btf")
            eeOffset = json_icerik.get("eeOffset")
            turnAngle =  json_icerik.get("turnAngle")
            bicepPosAngle = json_icerik.get("bicepPosAngle")
            bicepNegAngle = json_icerik.get("bicepNegAngle")
            joint = json_icerik.get("joint")
            robotName = json_icerik.get("robotName")

            myRobot = deltaRobot(la = bicep, lb = forearm, ra = base, rb=end, btf=btf, minTurnAngle=turnAngle, cwMax=bicepPosAngle, ccwMax=-bicepNegAngle, jointMax=joint)
            cozum = myRobot.inverseKinematic(x,y,z-eeOffset)
        
            ileriCozum = myRobot.forwardKinematic(cozum[0],cozum[1],cozum[2])

            self.tersBeta1res.config(text=str(self.roundoff(x=ileriCozum[0][4])))
            self.tersBeta2res.config(text=str(self.roundoff(x=ileriCozum[1][4])))
            self.tersBeta3res.config(text=str(self.roundoff(x=ileriCozum[2][4])))

            self.tersPhi1res.config(text=str(self.roundoff(x=ileriCozum[0][5])))
            self.tersPhi2res.config(text=str(self.roundoff(x=ileriCozum[1][5])))
            self.tersPhi3res.config(text=str(self.roundoff(x=ileriCozum[2][5])))

            self.tersGama1res.config(text=str(self.roundoff(x=ileriCozum[0][6])))
            self.tersGama2res.config(text=str(self.roundoff(x=ileriCozum[1][6])))
            self.tersGama3res.config(text=str(self.roundoff(x=ileriCozum[2][6])))

            self.tersT1Res.config(text=str(self.roundoff(x=cozum[0])))
            self.tersT2Res.config(text=str(self.roundoff(x=cozum[1])))
            self.tersT3Res.config(text=str(self.roundoff(x=cozum[2])))
        except TypeError:
            title = "Hata!"
            message = f"{robotName} : Tanımladığınız Robotun Çalışma Alanı Dışında Bir Nokta Girdiniz!"
            messagebox.showerror(title, message)


    def tersKinematikTemizle(self):
        self.tersEntryX.delete(0, "end")
        self.tersEntryY.delete(0, "end")
        self.tersEntryZ.delete(0, "end")

        self.tersBeta1res.config(text="β")
        self.tersBeta2res.config(text="β")
        self.tersBeta3res.config(text="β")

        self.tersPhi1res.config(text="φ")
        self.tersPhi2res.config(text="φ")
        self.tersPhi3res.config(text="φ")

        self.tersGama1res.config(text="γ")
        self.tersGama2res.config(text="γ")
        self.tersGama3res.config(text="γ")

        self.tersT1Res.config(text="θ")
        self.tersT2Res.config(text="θ")
        self.tersT3Res.config(text="θ")


    def yorunge(self,tab):
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
        if os.path.exists("trajectories") and os.path.isdir("trajectories"):
            dosya_isimleri = [os.path.splitext(dosya)[0] for dosya in os.listdir("trajectories") if dosya.endswith(".npy")]
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
            trajectoryPlan = np.load(f"trajectories/{secilenTrajectory}.npy")
        except FileNotFoundError:
            print(f"Trajectory Seçiniz.")

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

    def hakkimizda(self,tab):

        self.togglebutton = ttk.Button(tab, text="CHANGE THEME", style="Accent.TButton", command=self.changeTheme)
        self.togglebutton.pack(side="top", fill="x", padx=10, pady=10)

        # Resmi tanımla, ancak henüz ekleme
        self.icon = tk.PhotoImage(file='logo/blackSquare.png')
        self.label = tk.Label(tab, image=self.icon)
        self.label.pack(fill="both", expand=True, anchor="center")

        self.tersZRes = ttk.Label(tab, text="Version 1.00",font=("Arial",14))
        self.tersZRes.pack(side="bottom", anchor="s")

        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)
        tab.columnconfigure(2, weight=1)
        tab.rowconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        tab.rowconfigure(2, weight=1)
        

    def changeTheme(self):
        current_deger = self.themeChoose.get()
        new_deger = 1 - current_deger
        self.themeChoose.set(new_deger)

        if new_deger == 0:
            root.tk.call("set_theme", "dark")
            self.icon.config(file='logo/blackSquare.png')
            self.updateStyles()
        elif (new_deger == 1):
            root.tk.call("set_theme", "light")
            self.icon.config(file='logo/whiteSquare.png')
            self.updateStyles()
        else:
            root.tk.call("set_theme", "dark")
            self.icon.config(file='logo/blackSquare.png')
            self.updateStyles()


if __name__ == "__main__":

    # Scriptin bulunduğu dosya yolunu al
    script_dosya_yolu = os.path.dirname(os.path.abspath(__file__))

    # Hedef klasör adı
    klasor_adi = "robots"

    klasörTwo = "trajectories"

    # Klasör yolunu oluştur
    klasor_yolu = os.path.join(script_dosya_yolu, klasor_adi)

    yolTwo = os.path.join(script_dosya_yolu, klasörTwo)

    # Klasör kontrolü ve oluşturma
    if not os.path.exists(klasor_yolu):
        os.makedirs(klasor_yolu)

    if not os.path.exists(yolTwo):
        os.makedirs(yolTwo)

    root = tk.Tk()
    root.title("DELTA Robotics")
    root.iconbitmap('logo/logo.ico')
    root.wm_iconbitmap('logo/logo.ico')
    root.geometry("1280x720")
    #root.minsize(200, 150)
    #root.overrideredirect(True)

    root.tk.call("source", "azure.tcl")
    root.tk.call("set_theme", "dark")

    app = App(root)
    app.pack(fill="both", expand=True)

    root.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()