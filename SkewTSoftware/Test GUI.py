import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
import os
import tkinter as tk
from tkinter import ttk, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def plot_event_map(df, plot_frame, title, event_type, fig_size):
    """Plots the specified event type on a map."""

    lats = []
    lons = []
    for i in range(len(df['Type 1, 2, 3, 4, 5'])):
        if df['Type 1, 2, 3, 4, 5'][i] == event_type:
            lats.append(float(df['lat'][i]))
            lons.append(float(df['lon'][i]))

    fig = plt.figure(figsize=fig_size) # Figure size will be dynamically set.
    proj = ccrs.PlateCarree(central_longitude=-105)
    ax = fig.add_subplot(1, 1, 1, projection=proj)

    for i in range(len(lats)):
        ax.plot(lons[i], lats[i], 'bo', transform=ccrs.PlateCarree(), alpha=0.4)

    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.COASTLINE)
    land_10m = cfeature.NaturalEarthFeature('physical', 'land', '50m')
    ax.add_feature(land_10m, edgecolor='black', facecolor=cfeature.COLORS['land'])
    ax.add_feature(cfeature.STATES)
    ax.add_feature(cfeature.BORDERS)
    ax.add_feature(cfeature.LAKES, alpha=0.75)
    ax.set_extent([-125, -65, 25, 55])
    plt.title(title, fontsize=25)

    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill=tk.BOTH, expand=True) # Fill and expand
    canvas.draw()

def create_event_map_gui(notebook):
    """Creates the GUI for plotting event maps."""

    tab = ttk.Frame(notebook)
    notebook.add(tab, text='Event Map')

    control_frame = ttk.LabelFrame(tab, text='Map Controls')
    control_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')

    plot_frame = ttk.LabelFrame(tab, text='Map Plot')
    plot_frame.grid(row=1, column=0, padx=10, pady=10, sticky='nsew')
    plot_frame.grid_rowconfigure(0, weight=1) # Allow plot frame to expand
    plot_frame.grid_columnconfigure(0, weight=1)

    title_label = ttk.Label(control_frame, text='Map Title:')
    title_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')

    title_entry = ttk.Entry(control_frame)
    title_entry.grid(row=1, column=0, padx=5, pady=5, sticky='ew')
    title_entry.insert(0, 'Event Map')

    event_label = ttk.Label(control_frame, text='Event Type:')
    event_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')

    event_options = [1, 2, 3, 4, 5]
    event_var = tk.IntVar(tab)
    event_menu = ttk.Combobox(control_frame, textvariable=event_var, values=event_options)
    event_menu.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
    event_menu.current(0) # set default to 1

    def plot_button_command():
        """Handles the plot button click event."""
        for widget in plot_frame.winfo_children():
            widget.destroy()
        title = title_entry.get()
        event_type = event_var.get()
        script_dir = os.path.dirname(__file__)
        full_dir = os.path.join(script_dir, 'TSSN_reports.xlsx')
        df = pd.read_excel(full_dir)
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        max_width = screen_width*0.8
        max_height = screen_height*0.8
        fig_size = (min(max_width / 100, max_height / 100), min(max_width / 100, max_height / 100))
        plot_event_map(df, plot_frame, title, event_type, fig_size)

    def save_plot():
        """Saves the current plot to a file."""
        filename = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if filename:
            plt.gcf().savefig(filename)
            print(f"Plot saved to {filename}")

    plot_button = ttk.Button(control_frame, text='Generate Map', command=plot_button_command)
    plot_button.grid(row=2, column=0, padx=5, pady=5, sticky='ew')

    save_button = ttk.Button(control_frame, text='Save Plot', command=save_plot)
    save_button.grid(row=2, column=1, padx=5, pady=5, sticky='ew')

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Event Map GUI")

    notebook = ttk.Notebook(root)
    notebook.pack(expand=True, fill='both')

    create_event_map_gui(notebook)

    root.mainloop()