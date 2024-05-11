import tkinter as tk
from tkinter import ttk
import json
from tkinter import ttk, messagebox

from modules.deltaRobot import deltaRobot

class Kinematic():
    def createKinePage(self,tab):
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