import tkinter as tk
from tkinter import ttk, messagebox
from modules.dynamixel import Dynamixel
import threading
import time
import sys
import serial
import serial.tools.list_ports
import json
import os
import glob
import pickle
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from modules.deltaRobot import deltaRobot
from modules.dynamixel import Dynamixel

class MotorControl():
    def __init__(self):
        global portFree
        portFree = False
        json_dosya_yolu = os.path.join("data/", f"myRobot.json")

        try:
            with open(json_dosya_yolu, 'r') as dosya:
                json_dosyası = dosya.read()
                json_icerik = json.loads(json_dosyası)
                self.base = float(json_icerik.get("base"))
                self.bicep = float(json_icerik.get("bicep"))
                self.forearm = float(json_icerik.get("forearm"))
                self.end = float(json_icerik.get("end"))
                self.btf = float(json_icerik.get("btf"))
                self.eeOffset = float(json_icerik.get("eeOffset"))
                self.turnAngle =  float(json_icerik.get("turnAngle"))
                self.bicepPosAngle = float(json_icerik.get("bicepPosAngle"))
                self.bicepNegAngle = float(json_icerik.get("bicepNegAngle"))
                self.joint = float(json_icerik.get("joint"))
                self.robotName = json_icerik.get("robotName")
        except FileNotFoundError:
            print(f"{robotName}.json dosyası bulunamadı.")
        except Exception as e:
            print(f"Hata oluştu: {e}")
        
        
        self.myRobot = deltaRobot(la = self.bicep, lb = self.forearm, ra = self.base, rb=self.end, btf=self.btf, minTurnAngle=self.turnAngle, cwMax=self.bicepPosAngle, ccwMax=-self.bicepNegAngle, jointMax=self.joint)

    def startTempAgent(self):
        try:
            self.control = Dynamixel(DEVICENAME=self.portbox.get())
        except Exception as e:
            print(f"Seri Port Seçiniz ! : {e}")

        def temp_background_task():
            global portFree
            while portFree:
                print('Agent Active')
                self.measure()
                time.sleep(1)
            self.measureClear()
        self.process_thread = threading.Thread(target=temp_background_task)
        self.process_thread.start()

    def createControlPage(self,tab):
        self.motorCom = ttk.LabelFrame(tab, text="MOTOR CONNECTIONS", padding=10)
        self.motorCom.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.port_list = []
        self.port_list.extend(self.list_serial_ports())
        self.portbox = ttk.Combobox(self.motorCom, values=self.port_list, font = ('Arial',12), validate="key", validatecommand=self.vcmd2)
        self.portbox.current(0)
        self.portbox.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.portbox.bind("<<ComboboxSelected>>", self.combobox_choose)

        self.togglebutton = ttk.Checkbutton(self.motorCom, text="Connection", style="Toggle.TButton", command=self.toggleAgentsActive)
        self.togglebutton.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")













        self.motorData = ttk.LabelFrame(tab, text="MOTOR VALUES", padding=10)
        self.motorData.grid(row=1, column=0, padx=10, pady=10, rowspan=4, sticky="nsew")

        self.temp1=ttk.Label(self.motorData,text="1. Motor Sicakligi : No Data", font = ('Arial',12))
        self.temp1.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        self.temp2=ttk.Label(self.motorData,text="2. Motor Sicakligi : No Data", font = ('Arial',12))
        self.temp2.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.temp3=ttk.Label(self.motorData,text="3. Motor Sicakligi : No Data", font = ('Arial',12))
        self.temp3.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        self.volt1=ttk.Label(self.motorData,text="1. Motor Gerilim : No Data", font = ('Arial',12))
        self.volt1.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        self.volt2=ttk.Label(self.motorData,text="2. Motor Gerilim : No Data", font = ('Arial',12))
        self.volt2.grid(row=4, column=0, padx=10, pady=5, sticky="ew")

        self.volt3=ttk.Label(self.motorData,text="3. Motor Gerilim : No Data", font = ('Arial',12))
        self.volt3.grid(row=5, column=0, padx=10, pady=5, sticky="ew")

        self.load1=ttk.Label(self.motorData,text="1. Motor Yük : No Data", font = ('Arial',12))
        self.load1.grid(row=6, column=0, padx=10, pady=5, sticky="ew")

        self.load2=ttk.Label(self.motorData,text="2. Motor Yük : No Data", font = ('Arial',12))
        self.load2.grid(row=7, column=0, padx=10, pady=5, sticky="ew")

        self.load3=ttk.Label(self.motorData,text="3. Motor Yük : No Data", font = ('Arial',12))
        self.load3.grid(row=8, column=0, padx=10, pady=5, sticky="ew")










        self.writeApproach = ttk.LabelFrame(tab, text="APPROACH SET.", padding=10)
        self.writeApproach.grid(row=0, column=1, padx=10, pady=10, rowspan=2, sticky="nsew")

        self.marginTitle=ttk.Label(self.writeApproach,text="Margin : ", font = ('Arial',12))
        self.marginTitle.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        
        self.margin = tk.IntVar(value=1)
        self.scaleMargin = ttk.Scale(self.writeApproach,from_=1,to=254, variable=self.margin, command=lambda event : self.setMargin())
        self.scaleMargin.grid(row=0, column=1, padx=(10, 10), pady=(10, 10), sticky="ew")

        self.presMargin=ttk.Label(self.writeApproach,text="   ", font = ('Arial',12))
        self.presMargin.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        self.slopeTitle=ttk.Label(self.writeApproach,text="Slope : ", font = ('Arial',12))
        self.slopeTitle.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        self.slope = tk.IntVar(value=2)
        self.scaleSlope = ttk.Scale(self.writeApproach,from_=0,to=254, variable=self.slope, command=lambda event : self.setSlope())
        self.scaleSlope.grid(row=1, column=1, padx=(10, 10), pady=(10, 10), sticky="ew")

        self.presSlope=ttk.Label(self.writeApproach,text="   ", font = ('Arial',12))
        self.presSlope.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

        self.punchTitle=ttk.Label(self.writeApproach,text="Punch : ", font = ('Arial',12))
        self.punchTitle.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        
        self.punch = tk.IntVar(value=0)
        self.scalePunch = ttk.Scale(self.writeApproach,from_=0,to=1023, variable=self.punch, command=lambda event : self.setPunch())
        self.scalePunch.grid(row=2, column=1, padx=(10, 10), pady=(10, 10), sticky="ew")

        self.presPunch=ttk.Label(self.writeApproach,text="   ", font = ('Arial',12))
        self.presPunch.grid(row=2, column=2, padx=5, pady=5, sticky="ew")

        self.accentbutton4 = ttk.Button(self.writeApproach, text="Send", style="Accent.TButton", command=self.sendApproach)
        self.accentbutton4.grid(row=3, column=0, columnspan=2,  padx=5, pady=5, sticky="nsew")











        self.readAngle = ttk.LabelFrame(tab, text="Present Angle", padding=10)
        self.readAngle.grid(row=2, column=1, padx=10, pady=10, sticky="nsew")

        self.mot1=ttk.Label(self.readAngle,text="1. Motor : ", font = ('Arial',12))
        self.mot1.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.ang1=ttk.Label(self.readAngle,text="No Data", font = ('Arial',12))
        self.ang1.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.mot2=ttk.Label(self.readAngle,text="2. Motor : ", font = ('Arial',12))
        self.mot2.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        self.ang2=ttk.Label(self.readAngle,text="No Data", font = ('Arial',12))
        self.ang2.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.mot3=ttk.Label(self.readAngle,text="3. Motor : ", font = ('Arial',12))
        self.mot3.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        
        self.ang3=ttk.Label(self.readAngle,text="No Data", font = ('Arial',12))
        self.ang3.grid(row=2, column=1, padx=5, pady=5, sticky="w")







        self.writeCoo = ttk.LabelFrame(tab, text="COORDINATE", padding=10)
        self.writeCoo.grid(row=0, column=2, padx=10, pady=10, rowspan=2, sticky="nsew")

        self.xTitle=ttk.Label(self.writeCoo,text="X  : ", font = ('Arial',12))
        self.xTitle.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.xCooGoal=ttk.Entry(self.writeCoo, font = ('Arial',12))
        self.xCooGoal.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        self.yTitle=ttk.Label(self.writeCoo,text="Y : ", font = ('Arial',12))
        self.yTitle.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        self.yCooGoal=ttk.Entry(self.writeCoo, font = ('Arial',12))
        self.yCooGoal.grid(row=1, column=1, padx=5, pady=5, sticky="e")

        self.zTitle=ttk.Label(self.writeCoo,text="Z : ", font = ('Arial',12))
        self.zTitle.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        
        self.zCooGoal=ttk.Entry(self.writeCoo, font = ('Arial',12))
        self.zCooGoal.grid(row=2, column=1, padx=5, pady=5, sticky="e")

        self.accentbutton4 = ttk.Button(self.writeCoo, text="Send", style="Accent.TButton", command=self.sendLocation)
        self.accentbutton4.grid(row=3, column=0, columnspan=2,  padx=5, pady=5, sticky="nsew")











        self.readCoo = ttk.LabelFrame(tab, text="Present Coordinates", padding=10)
        self.readCoo.grid(row=2, column=2, padx=10, pady=10, sticky="nsew")

        self.xTitle=ttk.Label(self.readCoo,text="X  : ", font = ('Arial',12))
        self.xTitle.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.xCoo=ttk.Label(self.readCoo,text="No Data", font = ('Arial',12))
        self.xCoo.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.yTitle=ttk.Label(self.readCoo,text="Y : ", font = ('Arial',12))
        self.yTitle.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        self.yCoo=ttk.Label(self.readCoo,text="No Data", font = ('Arial',12))
        self.yCoo.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.zTitle=ttk.Label(self.readCoo,text="Z : ", font = ('Arial',12))
        self.zTitle.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        
        self.zCoo=ttk.Label(self.readCoo,text="No Data", font = ('Arial',12))
        self.zCoo.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        self.notebook = ttk.Notebook(tab)
        self.notebook.grid(row=3, column=1, padx=10, pady=10, columnspan=2, rowspan=2, sticky="nsew")

        self.syncWrite=ttk.Frame(self.notebook)
        self.notebook.add(self.syncWrite, text="Sync Write")
        self.temperatures = ttk.Frame(self.notebook)
        self.notebook.add(self.temperatures, text="Temperatures")
        self.voltages = ttk.Frame(self.notebook)
        self.notebook.add(self.voltages, text="Voltages")
        self.loads = ttk.Frame(self.notebook)
        self.notebook.add(self.loads, text="Loads")

        self.traList = []
        files = glob.glob('data/trajectories/corrected/*')
        for file in files:
            base_name = os.path.basename(file)
            name_part = base_name.split('_')[0]
            self.traList.append(name_part)
        self.traList = ttk.Combobox(self.syncWrite, values=self.traList, font = ('Arial',12), validate="key", validatecommand=self.vcmd2)
        self.traList.current(0)
        self.traList.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.traList.bind("<<ComboboxSelected>>", self.syncWriteBegin)

        self.repetetive = tk.BooleanVar()
        self.checkbutton = ttk.Checkbutton(self.syncWrite, text="3 times", variable=self.repetetive, style="My.TCheckbutton")
        self.checkbutton.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        self.startSync = ttk.Button(self.syncWrite, text="Send", style="Accent.TButton", command=self.syncWriteBegin)
        self.startSync.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

        self.tempFigure = Figure(figsize=(5, 4), dpi=100)
        self.axTemp = self.tempFigure.add_subplot(111)
        self.time = []
        self.tempData1 = []
        self.tempData2 = []
        self.tempData3 = []
        self.line1, = self.axTemp.plot(self.time, self.tempData1, 'r-', label='y = ID 1')
        self.line2, = self.axTemp.plot(self.time, self.tempData2, 'g-', label='y = ID 2')
        self.line3, = self.axTemp.plot(self.time, self.tempData3, 'b-', label='y = ID 3')
        self.axTemp.legend()
        self.canvasTemp = FigureCanvasTkAgg(self.tempFigure, master=self.temperatures)
        self.canvasTemp.draw()
        self.canvasTemp.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.voltFigure = Figure(figsize=(5, 4), dpi=100)
        self.axVolt = self.voltFigure.add_subplot(111)
        self.time2 = []
        self.voltData1 = []
        self.voltData2 = []
        self.voltData3 = []
        self.line12, = self.axVolt.plot(self.time, self.voltData1, 'r-', label='y = ID 1')
        self.line22, = self.axVolt.plot(self.time, self.voltData2, 'g-', label='y = ID 2')
        self.line32, = self.axVolt.plot(self.time, self.voltData3, 'b-', label='y = ID 3')
        self.axVolt.legend()
        self.canvasVolt = FigureCanvasTkAgg(self.voltFigure, master=self.voltages)
        self.canvasVolt.draw()
        self.canvasVolt.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.loadFigure = Figure(figsize=(5, 4), dpi=100)
        self.axLoad = self.loadFigure.add_subplot(111)
        self.time3 = []
        self.loadData1 = []
        self.loadData2 = []
        self.loadData3 = []
        self.line13, = self.axLoad.plot(self.time, self.loadData1, 'r-', label='y = ID 1')
        self.line23, = self.axLoad.plot(self.time, self.loadData2, 'g-', label='y = ID 2')
        self.line33, = self.axLoad.plot(self.time, self.loadData3, 'b-', label='y = ID 3')
        self.axLoad.legend()
        self.canvasLoad = FigureCanvasTkAgg(self.loadFigure, master=self.loads)
        self.canvasLoad.draw()
        self.canvasLoad.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)
        tab.columnconfigure(2, weight=1)
        tab.rowconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        tab.rowconfigure(2, weight=1)
        tab.rowconfigure(3, weight=10)
        tab.rowconfigure(4, weight=10)
        

        self.motorCom.rowconfigure(0, weight=1)
        self.motorCom.columnconfigure(0, weight=1)
        self.motorCom.columnconfigure(1, weight=5)

        self.motorData.rowconfigure(0, weight=1)
        self.motorData.rowconfigure(1, weight=1)
        self.motorData.rowconfigure(2, weight=1)
        self.motorData.rowconfigure(3, weight=1)
        self.motorData.rowconfigure(4, weight=1)
        self.motorData.rowconfigure(5, weight=1)
        self.motorData.rowconfigure(6, weight=1)
        self.motorData.rowconfigure(7, weight=1)
        self.motorData.rowconfigure(8, weight=1)
        self.motorData.columnconfigure(0, weight=1)
        self.motorData.columnconfigure(1, weight=1)

        self.writeApproach.rowconfigure(0, weight=1)
        self.writeApproach.rowconfigure(1, weight=1)
        self.writeApproach.rowconfigure(2, weight=1)
        self.writeApproach.rowconfigure(3, weight=1)
        self.writeApproach.columnconfigure(0, weight=5)
        self.writeApproach.columnconfigure(1, weight=5)
        self.writeApproach.columnconfigure(2, weight=1)

        self.writeCoo.rowconfigure(0, weight=1)
        self.writeCoo.rowconfigure(1, weight=1)
        self.writeCoo.rowconfigure(2, weight=1)
        self.writeCoo.rowconfigure(3, weight=1)
        self.writeCoo.columnconfigure(0, weight=1)
        self.writeCoo.columnconfigure(1, weight=1)

        self.readAngle.rowconfigure(0, weight=1)
        self.readAngle.rowconfigure(1, weight=1)
        self.readAngle.rowconfigure(2, weight=1)
        self.readAngle.columnconfigure(0, weight=1)
        self.readAngle.columnconfigure(1, weight=1)

        self.readCoo.rowconfigure(0, weight=1)
        self.readCoo.rowconfigure(1, weight=1)
        self.readCoo.rowconfigure(2, weight=1)
        self.readCoo.columnconfigure(0, weight=1)
        self.readCoo.columnconfigure(1, weight=1)

        self.syncWrite.rowconfigure(0, weight=5)
        self.syncWrite.rowconfigure(1, weight=1)
        self.syncWrite.columnconfigure(0, weight=5)
        self.syncWrite.columnconfigure(1, weight=1)

    def list_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        available_ports = []
        for port, desc, hwid in sorted(ports):
            available_ports.append(port)
        return available_ports

    def combobox_choose(self, event):
        secilen_port = self.portbox.get()
        print(f'{secilen_port} portu seçildi !')

    def toggleAgentsActive(self):
        global portFree
        if portFree:
            portFree = False
        else:
            portFree = True
            self.startTempAgent()

    def sendLocation(self):
        global portFree
        portFree = False
        time.sleep(0.5)
        goalX = int(self.xCooGoal.get())
        goalY = int(self.yCooGoal.get())
        goalZ = int(self.zCooGoal.get()) - self.eeOffset
        tetas = self.myRobot.inverseKinematic(Dx=goalX, Dy=goalY, Dz=goalZ)
        self.control.connect()
        self.control.syncWrite([(tetas[0],tetas[1],tetas[2])])
        self.control.disconnect()
        portFree = True
        self.startTempAgent()

    def measure(self):
        self.control.connect()
        readTemp1 = self.control.readTemperature(1)
        self.temp1.config(text=f'1. Motor Sicakligi : {readTemp1}')
        readTemp2 = self.control.readTemperature(2)
        self.temp2.config(text=f'2. Motor Sicakligi : {readTemp2}')
        readTemp3 = self.control.readTemperature(3)
        self.temp3.config(text=f'3. Motor Sicakligi : {readTemp3}')

        readVolt1 = self.control.readPresentVoltage(1)
        self.volt1.config(text=f'1. Motor Gerilimi : {readVolt1}')
        readVolt2 = self.control.readPresentVoltage(2)
        self.volt2.config(text=f'2. Motor Gerilimi : {readVolt2}')
        readVolt3 = self.control.readPresentVoltage(3)
        self.volt3.config(text=f'3. Motor Gerilimi : {readVolt3}')

        readLoad1 = self.control.readPresentLoad(1)
        self.load1.config(text=f'1. Motor Yük : % {self.roundoff((readLoad1-1023)*100/1023)}')
        readLoad2 = self.control.readPresentLoad(2)
        self.load2.config(text=f'2. Motor Yük : % {self.roundoff((readLoad2-1023)*100/1023)}')
        readLoad3 = self.control.readPresentLoad(3)
        self.load3.config(text=f'3. Motor Yük : % {self.roundoff((readLoad3-1023)*100/1023)}')

        readPos1 = self.roundoff((-self.control.readPresentPosition(1)+512) * 0.29)
        self.ang1.config(text=f'{readPos1} Degree')
        readPos2 = self.roundoff((-self.control.readPresentPosition(2)+512) * 0.29)
        self.ang2.config(text=f'{readPos2} Degree')
        readPos3 = self.roundoff((-self.control.readPresentPosition(3)+512) * 0.29)
        self.ang3.config(text=f'{readPos3} Degree')

        pos1 = (-self.control.readPresentPosition(1)+512) * 0.29
        pos2 = (-self.control.readPresentPosition(2)+512) * 0.29
        pos3 = (-self.control.readPresentPosition(3)+512) * 0.29

        x,y,z = self.ileriHesapla(pos1,pos2,pos3)

        self.xCoo.config(text = f"{self.roundoff(x)}")
        self.yCoo.config(text = f"{self.roundoff(y)}")
        self.zCoo.config(text = f"{self.roundoff(z)}")

        marg = self.control.readComplianceMargin(1)
        slope = self.control.readComplianceSlope(1)
        punch = self.control.readPunch(1)

        self.margin = tk.IntVar(value=int(marg))
        self.slope = tk.IntVar(value=int(slope))
        self.punch = tk.IntVar(value=int(punch))

        self.marginTitle.config(text=f'Margin : {marg}')
        self.slopeTitle.config(text=f'Slope : {slope}')
        self.punchTitle.config(text=f'Punch : {punch}')

        self.time.append(time.time())
        self.tempData1.append(readTemp1)
        self.tempData2.append(readTemp2)
        self.tempData3.append(readTemp3)
        self.line1.set_xdata(self.time)
        self.line1.set_ydata(self.tempData1)
        self.line2.set_xdata(self.time)
        self.line2.set_ydata(self.tempData2)
        self.line3.set_xdata(self.time)
        self.line3.set_ydata(self.tempData3)
        self.axTemp.relim()
        self.axTemp.autoscale_view()
        self.canvasTemp.draw()

        self.time2.append(time.time())
        self.voltData1.append(readVolt1)
        self.voltData2.append(readVolt2)
        self.voltData3.append(readVolt3)
        self.line12.set_xdata(self.time)
        self.line12.set_ydata(self.voltData1)
        self.line22.set_xdata(self.time)
        self.line22.set_ydata(self.voltData2)
        self.line32.set_xdata(self.time)
        self.line32.set_ydata(self.voltData3)
        self.axVolt.relim()
        self.axVolt.autoscale_view()
        self.canvasVolt.draw()

        self.time3.append(time.time())
        self.loadData1.append((readLoad1-1023)*100/1023)
        self.loadData2.append((readLoad2-1023)*100/1023)
        self.loadData3.append((readLoad3-1023)*100/1023)
        self.line13.set_xdata(self.time)
        self.line13.set_ydata(self.loadData1)
        self.line23.set_xdata(self.time)
        self.line23.set_ydata(self.loadData2)
        self.line33.set_xdata(self.time)
        self.line33.set_ydata(self.loadData3)
        self.axLoad.relim()
        self.axLoad.autoscale_view()
        self.canvasLoad.draw()

        self.control.disconnect()
    
    def roundoff(self,x, y=2):
        z = 10 ** y
        return round(x * z) / z

    def measureClear(self):
        self.temp1.config(text=f'1. Motor Sicakligi : No Data')
        self.temp2.config(text=f'2. Motor Sicakligi : No Data')
        self.temp3.config(text=f'3. Motor Sicakligi : No Data')

        self.volt1.config(text=f'1. Motor Gerilimi : No Data')
        self.volt2.config(text=f'2. Motor Gerilimi : No Data')
        self.volt3.config(text=f'3. Motor Gerilimi : No Data')

        self.load1.config(text=f'1. Motor Yük : No Data')
        self.load2.config(text=f'2. Motor Yük : No Data')
        self.load3.config(text=f'3. Motor Yük : No Data')
        
        self.ang1.config(text='No Data')
        self.ang2.config(text='No Data')
        self.ang3.config(text='No Data')

        self.xCoo.config(text = "No Data")
        self.yCoo.config(text = "No Data")
        self.zCoo.config(text = "No Data")

        self.marginTitle.config(text='Margin : No Data')
        self.slopeTitle.config(text='Margin : No Data')
        self.punchTitle.config(text='Margin : No Data')

    def ileriHesapla(self,teta1, teta2, teta3):
        try:
            with open('data/myRobot.json', 'r') as dosya:
                self.json_dosyası = dosya.read()
                self.json_icerik = json.loads(self.json_dosyası)

        except FileNotFoundError:
            print("data/myRobot.json dosyası bulunamadı.")
        except Exception as e:
            print(f"Hata oluştu: {e}")

        try:
            base = self.json_icerik.get("base")
            bicep = self.json_icerik.get("bicep")
            forearm = self.json_icerik.get("forearm")
            end = self.json_icerik.get("end")
            btf = self.json_icerik.get("btf")
            eeOffset = self.json_icerik.get("eeOffset")
            turnAngle =  self.json_icerik.get("turnAngle")
            bicepPosAngle = self.json_icerik.get("bicepPosAngle")
            bicepNegAngle = self.json_icerik.get("bicepNegAngle")
            joint = self.json_icerik.get("joint")
            robotName = self.json_icerik.get("robotName")

            myRobot = deltaRobot(la = bicep, lb = forearm, ra = base, rb=end, btf=btf, minTurnAngle=turnAngle, cwMax=bicepPosAngle, ccwMax=-bicepNegAngle, jointMax=joint)
            cozum = myRobot.forwardKinematic(teta1, teta2, teta3)
        
        except TypeError:
            title = "Hata!"
            message = f"{robotName} : Tanımladığınız Robotun Çalışma Alanı Dışında Bir Nokta Girdiniz!"
            messagebox.showerror(title, message)
        
        return cozum[0][3][0], cozum[1][3][1], cozum[2][3][2]+eeOffset

    def setMargin(self):
        self.presMargin.config(text=f'{int(self.scaleMargin.get())}')

    def setSlope(self):
        self.presSlope.config(text=f'{int(self.scaleSlope.get())}')
    
    def setPunch(self):
        self.presPunch.config(text=f'{int(self.scalePunch.get())}')

    def sendApproach(self):
        global portFree
        portFree = False
        time.sleep(0.5)
        self.control.connect()
        self.control.writeComplianceMargin(id=1,margin=int(self.scaleMargin.get()))
        self.control.writeComplianceMargin(id=2,margin=int(self.scaleMargin.get()))
        self.control.writeComplianceMargin(id=3,margin=int(self.scaleMargin.get()))

        self.control.writeComplianceSlope(id=1,slope=int(self.scaleSlope.get()))
        self.control.writeComplianceSlope(id=2,slope=int(self.scaleSlope.get()))
        self.control.writeComplianceSlope(id=3,slope=int(self.scaleSlope.get()))
        
        self.control.writePunch(id=1, current=int(self.scalePunch.get()))
        self.control.writePunch(id=2, current=int(self.scalePunch.get()))
        self.control.writePunch(id=3, current=int(self.scalePunch.get()))

        time.sleep(1)
        portFree=True
        self.startTempAgent()

    def syncWriteBegin(self):
        global portFree
        portFree = False
        time.sleep(0.5)
        self.control.connect()
        sec_plan = self.traList.get()
        with open(f'data/trajectories/corrected/{sec_plan}_Theta.pkl', 'rb') as file:
            loadedTrajectory = pickle.load(file)
        if self.repetetive.get() == True:
            for i in range(3):
                self.control.syncWrite(plan=loadedTrajectory)
        else:
            self.control.syncWrite(plan=loadedTrajectory)
        self.control.disconnect()
        portFree = True
        self.startTempAgent()