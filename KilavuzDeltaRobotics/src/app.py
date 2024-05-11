import tkinter as tk
from tkinter import ttk

from tools.parameters import Parameters
from tools.kinematic import Kinematic
from tools.trajectory import Trajectory


class App(ttk.Frame, Parameters, Kinematic, Trajectory):
    def __init__(self, parent):
        ttk.Frame.__init__(self,parent)
        self.parent = parent

        self.parent.title("DELTA Robotics")
        self.parent.iconbitmap('logo.ico')
        self.parent.wm_iconbitmap('logo.ico')
        self.parent.geometry("1280x720")

        self.parent.tk.call("source", "theme/azure.tcl")
        self.parent.tk.call("set_theme", "dark")

        self.pack(fill="both", expand=True)

        self.parent.protocol("WM_DELETE_WINDOW", self.parent.quit)

        # Set a minsize for the window, and place it in the middle
        self.update()

        self.themeChoose = tk.IntVar()
        self.themeChoose.set(0)

        def validate_input(char, entry_value):
            return char.isdigit() or char == "" or char == '.'

        def validate_input_char(char, entry_value):
            return char.isalpha()
        

        self.vcmd = (self.register(validate_input), "%S", "%P")

        self.vcmd2= (self.register(validate_input_char), "%S", "%P")

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

    def setup_widgets(self):

        tab_control = ttk.Notebook(self)

        tab1 = ttk.Frame(tab_control)
        tab2 = ttk.Frame(tab_control)
        tab3 = ttk.Frame(tab_control)

        tab_control.add(tab1, text='ROBOT')
        tab_control.add(tab2, text='KINEMATIC')
        tab_control.add(tab3, text='TRAJECTORY')

        self.createParamPage(tab1)
        self.createKinePage(tab2)
        self.createTrajPage(tab3)

        tab_control.pack(side="bottom",fill="both", expand=True)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)