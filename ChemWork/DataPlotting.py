import matplotlib.pyplot as plt
import numpy as np
from siphon.simplewebservice.wyoming import WyomingUpperAir
import metpy as mp
import metpy.calc as mpcalc
from metpy.units import units
from metpy.plots import SkewT
import datetime as dt
import pandas as pd
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import os
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def create_GUI(notebook):
    tab = ttk.Frame(notebook)
    notebook.add(tab, text='Data Plotting')
    selection_frame = ttk.LabelFrame(tab, text='Select Type')
    selection_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')


root = tk.Tk()
root.title('Chem Work')

notebook = ttk.Notebook(root)