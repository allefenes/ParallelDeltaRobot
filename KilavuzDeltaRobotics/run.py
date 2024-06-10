from src.app import App
import tkinter as tk
import os

if __name__ == "__main__":

    script_dosya_yolu = os.path.dirname(os.path.abspath(__file__))

    klasor_adi = "data/robots/"

    klasorTwo = "data/trajectories/"

    klasorThree = "data/trajectories/corrected/"

    klasor_yolu = os.path.join(script_dosya_yolu, klasor_adi)

    yolTwo = os.path.join(script_dosya_yolu, klasorTwo)

    yolThree = os.path.join(script_dosya_yolu,klasorThree)

    if not os.path.exists(klasor_yolu):
        os.makedirs(klasor_yolu)

    if not os.path.exists(yolTwo):
        os.makedirs(yolTwo)

    if not os.path.exists(yolThree):
        os.makedirs(yolThree)

    root = tk.Tk()
    app = App(root)
    root.mainloop()