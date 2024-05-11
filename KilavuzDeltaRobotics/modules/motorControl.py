import tkinter as tk
from tkinter import ttk
from modules.dynamixel import Dynamixel
import threading
import time

class MotorControl():
    def __init__(self):
        self.control = Dynamixel()
        self.portFree = True
    def startTempAgent(self):
        def temp_background_task():
            self.control.connect()
            while self.portFree:
                print('Agent Active')
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
                self.load1.config(text=f'1. Motor Yük : {readLoad1}')
                readLoad2 = self.control.readPresentLoad(2)
                self.load2.config(text=f'2. Motor Yük : {readLoad2}')
                readLoad3 = self.control.readPresentLoad(3)
                self.load3.config(text=f'3. Motor Yük : {readLoad3}')
                time.sleep(1)
            self.control.disconnect()
        self.process_thread = threading.Thread(target=temp_background_task)
        self.process_thread.start()

    def createControlPage(self,tab):
        self.motorCom = ttk.LabelFrame(tab, text="MOTOR COMMUNICATION", padding=10)
        self.motorCom.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.accentbutton = ttk.Button(self.motorCom, text="Agents Active", style="Accent.TButton", command=self.toggleAgentsActive)
        self.accentbutton.grid(row=1, column=1,  padx=10, pady=10, sticky="nsew")

        self.temp1=ttk.Label(self.motorCom,text="1. Motor Sicakligi : ", font = ('Arial',12))
        self.temp1.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.temp2=ttk.Label(self.motorCom,text="2. Motor Sicakligi : ", font = ('Arial',12))
        self.temp2.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        self.temp3=ttk.Label(self.motorCom,text="3. Motor Sicakligi : ", font = ('Arial',12))
        self.temp3.grid(row=4, column=0, padx=10, pady=10, sticky="ew")

        self.volt1=ttk.Label(self.motorCom,text="1. Motor Gerilim : ", font = ('Arial',12))
        self.volt1.grid(row=5, column=0, padx=10, pady=10, sticky="ew")

        self.volt2=ttk.Label(self.motorCom,text="2. Motor Gerilim : ", font = ('Arial',12))
        self.volt2.grid(row=6, column=0, padx=10, pady=10, sticky="ew")

        self.volt3=ttk.Label(self.motorCom,text="3. Motor Gerilim : ", font = ('Arial',12))
        self.volt3.grid(row=7, column=0, padx=10, pady=10, sticky="ew")

        self.load1=ttk.Label(self.motorCom,text="1. Motor Yük : ", font = ('Arial',12))
        self.load1.grid(row=5, column=0, padx=10, pady=10, sticky="ew")

        self.load2=ttk.Label(self.motorCom,text="2. Motor Yük : ", font = ('Arial',12))
        self.load2.grid(row=6, column=0, padx=10, pady=10, sticky="ew")

        self.load3=ttk.Label(self.motorCom,text="3. Motor Yük : ", font = ('Arial',12))
        self.load3.grid(row=7, column=0, padx=10, pady=10, sticky="ew")

        self.motorSend = ttk.LabelFrame(tab, text="MOTOR COMMAND", padding=10)
        self.motorSend.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.id1=ttk.Entry(self.motorSend, font = ('Arial',12))
        self.id1.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.id2=ttk.Entry(self.motorSend, font = ('Arial',12))
        self.id2.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        self.id3=ttk.Entry(self.motorSend, font = ('Arial',12))
        self.id3.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        self.accentbutton2 = ttk.Button(self.motorSend, text="LED ON", style="Accent.TButton", command=self.openLed)
        self.accentbutton2.grid(row=3, column=1,  padx=10, pady=10, sticky="nsew")

        self.accentbutton3 = ttk.Button(self.motorSend, text="LED OFF", style="Accent.TButton", command=self.closeLed)
        self.accentbutton3.grid(row=3, column=0,  padx=10, pady=10, sticky="nsew")

        self.accentbutton4 = ttk.Button(self.motorSend, text="Send Loc", style="Accent.TButton", command=self.sendLocation)
        self.accentbutton4.grid(row=4, column=0, columnspan=2,  padx=10, pady=10, sticky="nsew")

        self.startTempAgent()

    def toggleAgentsActive(self):
        if self.portFree:
            self.portFree = False
        else:
            self.portFree = True
            self.startTempAgent()

    def openLed(self):
        self.portFree = False
        self.control.connect()
        self.control.led(1,'on')
        self.control.led(2,'on')
        self.control.led(3,'on')
        self.control.disconnect()
        self.portFree = True
        self.startTempAgent()

    def closeLed(self):
        self.portFree = False
        self.control.connect()
        self.control.led(1,'off')
        self.control.led(2,'off')
        self.control.led(3,'off')
        self.control.disconnect()
        self.portFree = True
        self.startTempAgent()

    def sendLocation(self):
        self.portFree = False
        self.control.connect()
        self.control.writeGoalPosition(1,int(self.id1.get()))
        self.control.writeGoalPosition(2,int(self.id2.get()))
        self.control.writeGoalPosition(3,int(self.id3.get()))
        self.control.disconnect()
        self.portFree = True
        self.startTempAgent()
