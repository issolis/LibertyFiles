import tkinter as tk

from .app import LibertyGUI


def main():
    root = tk.Tk()
    LibertyGUI(root)
    root.mainloop()
