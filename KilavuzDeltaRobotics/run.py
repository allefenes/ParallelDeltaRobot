from src.app import App
import tkinter as tk
import os

if __name__ == "__main__":

    # Scriptin bulunduğu dosya yolunu al
    script_dosya_yolu = os.path.dirname(os.path.abspath(__file__))

    # Hedef klasör adı
    klasor_adi = "data/robots/"

    klasörTwo = "data/trajectories/"

    # Klasör yolunu oluştur
    klasor_yolu = os.path.join(script_dosya_yolu, klasor_adi)

    yolTwo = os.path.join(script_dosya_yolu, klasörTwo)

    # Klasör kontrolü ve oluşturma
    if not os.path.exists(klasor_yolu):
        os.makedirs(klasor_yolu)

    if not os.path.exists(yolTwo):
        os.makedirs(yolTwo)

    root = tk.Tk()
    app = App(root)
    root.mainloop()