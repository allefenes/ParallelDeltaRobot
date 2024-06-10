import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
import threading
import time

from modules.useYolo import UseYolo

class ImageProcess(UseYolo):
    def __init__(self):
        UseYolo.__init__(self)
        self.camActive = False
        self.ADDR_CAM = 1
        
    def startYoloAgent(self):
        def yolo_background_task():
            if self.camActive:
                self.cap = cv2.VideoCapture(self.ADDR_CAM)
                new_width, new_height = 320, 240
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, new_width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, new_height)
                self.starting_time = time.time()
                self.pureFrame_id = 0
                self.frame_id = 0

            while self.camActive:
                ret, pureFrame= self.cap.read()
                frame = self.scanImage(pureFrame)
                self.frame_id += 1
                elapsed_time = time.time() - self.starting_time
                fps = self.frame_id / elapsed_time
                cv2.putText(frame, "FPS: " + str(round(fps, 2)), (10, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 0), 3)
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(image)
                image = ImageTk.PhotoImage(image)
                self.cam2_label.config(image=image)
                self.cam2_label.image = image
            
            noImage2 = Image.open("theme/hq720.png")
            photo = ImageTk.PhotoImage(noImage2)
            self.cam2_label.config(image=photo)
            self.cam2_label.image = photo
            self.cap.release()

        self.process_thread = threading.Thread(target=yolo_background_task)
        self.process_thread.start()

    def startCamAgent(self):
        def cam_background_task():
            if self.camActive:
                self.cap = cv2.VideoCapture(self.ADDR_CAM)
                new_width, new_height = 320, 240
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, new_width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, new_height)
                self.starting_time = time.time()
                self.frame_id=0

            while self.camActive:
                ret, pureFrame= self.cap.read()
                self.pureFrame_id += 1
                elapsed_time = time.time() - self.starting_time
                fps = self.pureFrame_id / elapsed_time
                cv2.putText(pureFrame, "FPS: " + str(round(fps, 2)), (10, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 0), 3)
                image = cv2.cvtColor(pureFrame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(image)
                image = ImageTk.PhotoImage(image)
                self.cam1_label.config(image=image)
                self.cam1_label.image = image
            
            noImage2 = Image.open("theme/hq720.png")
            photo = ImageTk.PhotoImage(noImage2)
            self.cam1_label.config(image=photo)
            self.cam1_label.image = photo
            self.cap.release()

        self.process_thread = threading.Thread(target=cam_background_task)
        self.process_thread.start()

    def createImgPage(self,tab):

        self.cam1 = ttk.LabelFrame(tab, text="PURE VISION")
        self.cam1.grid(row=0, column=0, rowspan=5, padx=10, pady=10, sticky="nsew")

        self.cam1_label = tk.Label(self.cam1)
        self.cam1_label.pack(fill="both", expand=True, padx=10, pady=10)

        noImage2 = Image.open("theme/hq720.png")
        photo = ImageTk.PhotoImage(noImage2)
        self.cam1_label.config(image=photo)
        self.cam1_label.image = photo
        
        self.cam2 = ttk.LabelFrame(tab, text="YOLO VISION")
        self.cam2.grid(row=5, column=0, rowspan=5, padx=10, pady=10, sticky="nsew")

        self.cam2_label = tk.Label(self.cam2)
        self.cam2_label.pack(fill="both", expand=True, padx=10, pady=10)

        self.cam2_label.config(image=photo)
        self.cam2_label.image = photo

        self.accentbutton = ttk.Button(tab, text="Cam Agent Active", style="Accent.TButton", command=self.toggleCamActive)
        self.accentbutton.grid(row=0, column=2,  padx=10, pady=10, sticky="nsew")

        self.cam1.columnconfigure(0, weight=1)
        self.cam1.rowconfigure(0, weight=1)

    def toggleCamActive(self):
        if self.camActive:
            self.camActive = False
            print('Cam deactivated')
        else:
            self.camActive = True
            self.startCamAgent()
            self.startYoloAgent()
            print('Cam Activated')


