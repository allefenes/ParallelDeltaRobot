import cv2
import numpy as np
import time

class UseYolo():
    def __init__(self):
        # Load Yolo
        self.net = cv2.dnn.readNet("./data/yoloDoc/yolov3-tiny.weights", "./data/yoloDoc/yolov3-tiny.cfg")
        self.classes = []
        with open("./data/yoloDoc/coco.names", "r") as f:
            self.classes = [line.strip() for line in f.readlines()]
        self.layer_names = self.net.getLayerNames()
        self.output_layers = [self.layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
        self.colors = np.random.uniform(0, 255, size=(len(self.classes), 3))

    def scanImage(self,frame):
        self.height, self.width, self.channels = frame.shape

        # Detecting objects
        self.blob = cv2.dnn.blobFromImage(frame, 0.00392, (416,416), (0, 0, 0), True, crop=False)

        self.net.setInput(self.blob)
        self.outs = self.net.forward(self.output_layers)

        # Showing informations on the screen
        self.class_ids = []
        self.confidences = []
        self.boxes = []
        for out in self.outs:
            for detection in out:
                self.scores = detection[5:]
                self.class_id = np.argmax(self.scores)
                self.confidence = self.scores[self.class_id]
                if self.confidence > 0.2:
                    # Object detected
                    self.center_x = int(detection[0] * self.width)
                    self.center_y = int(detection[1] * self.height)
                    self.w = int(detection[2] * self.width)
                    self.h = int(detection[3] * self.height)

                    # Rectangle coordinates
                    self.x = int(self.center_x - self.w / 2)
                    self.y = int(self.center_y - self.h / 2)

                    self.boxes.append([self.x, self.y, self.w, self.h])
                    self.confidences.append(float(self.confidence))
                    self.class_ids.append(self.class_id)

        self.indexes = cv2.dnn.NMSBoxes(self.boxes, self.confidences, 0.8, 0.3)

        for i in range(len(self.boxes)):
            if i in self.indexes:
                self.x, self.y, self.w, self.h = self.boxes[i]  

                self.label = str(self.classes[self.class_ids[i]])
                self.confidence = self.confidences[i]
                self.color = self.colors[self.class_ids[i]]
                cv2.rectangle(frame, (self.x, self.y), (self.x + self.w, self.y + self.h), self.color, 2)

                #Middle Point Calculation
                self.a = self.x + (self.w/2)
                self.b = self.y + (self.h/2)
                cv2.circle(frame, ((int(self.a)), (int(self.b))), 1, (0, 0, 255), 6)

                cv2.putText(frame, self.label + " " + str(round(self.confidence, 2)), (self.x, self.y + 30), cv2.FONT_HERSHEY_PLAIN, 3, self.color, 3)

        return frame