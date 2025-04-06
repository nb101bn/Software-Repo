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

def create_dataframes(station_ids, dates):
    dataframes = {}
    for i in range(len(station_ids)):
        try:
            df = WyomingUpperAir.request_data(dates[i], station_ids[i])
            dataframes[i] = df
        except Exception as e:
            print(f'Error fetching or processing data for {station_ids[i]} and date {dates[i]}: {e}')
            dataframes[i] = None
    return dataframes

def create_skewt(data, stations, dates, title):
    plt.clf
    fig = plt.figure(figsize=(9,9))
    skew = SkewT(fig, rotation=30)
    for i in range(len(stations)):
        df = data[i]
        if df is None:
            print(f'No data avaliable for station {stations[i]}')
            return
        try:
            p = df['pressure'].values*units.hPa
            T = df['temperature'].values*units.degC
            Td = df['dewpoint'].values*units.degC
            u = df['u_wind'].values*units.knots
            v = df['v_wind'].values*units.knots
            height = df['height'].values*units.meter
            parcel_profile = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')
        except Exception as e:
            print(f'Error fetching or processing the data: {e}')
            return
        pressure_padding = 20*units.hPa
        label_pressure = p[0]+pressure_padding
        skew.plot(p, T, 'r', linewidth=2, label='Temperature')
        skew.plot(p, Td, 'g', linewidth=2, label='Dewpoint')
        skew.plot(p, parcel_profile, 'k', linewidth=2, label='Parcel Profile') # Plot Parcel Profile
        skew.ax.text(T[0], label_pressure, stations[i], color='r', ha='center', va='top', fontsize='8')
        skew.ax.text(Td[0], label_pressure, stations[i], color='g', ha='center', va='top', fontsize='8')

        # Plot wind barbs (using only every 10th data point for clarity)
        interval = np.max([1, int(len(p) / 50)]) #adjust interval based on data length
        skew.plot_barbs(p[::interval], u[::interval], v[::interval], xloc=1.05)  # Adjust xloc as needed



        # Add some helper lines
        skew.plot_dry_adiabats(t0=np.arange(233, 533, 10) * units.K, alpha=0.25, color='k')
        skew.plot_moist_adiabats(t0=np.arange(253, 401, 5) * units.K, alpha=0.25, color='k')

        # Set plot limits
        skew.ax.set_xlim(-50, 40)  # Adjust temperature range as needed
        skew.ax.set_ylim(1000, 100)  # Pressure range (reversed)

        # Add labels and title
        skew.ax.set_xlabel('Temperature (°C)')
        skew.ax.set_ylabel('Pressure (hPa)')
    plt.title(f'{title}')
    plt.legend()

def save_plot():
    filename = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
    if filename:
        plt.savefig(filename)
        print(f"Plot saved to {filename}")

def multiple_sation_plot(notebook):
    number_options = [1,2,3,4,5,6,7,8,9,10]

    tab = ttk.Frame(notebook)
    notebook.add(tab, text='Comparison Diagrams')

    control_frame = ttk.LabelFrame(tab, text='Number Selection')
    control_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')

    station_frame = ttk.LabelFrame(tab, text='Station Selection')
    station_frame.grid(row=1, column=0, columnspan=1, padx=10, pady=10, sticky='nsew')

    plot_frame = ttk.LabelFrame(tab, text='Plot Frame')
    plot_frame.grid(row=1, column=1, columnspan=1, padx=10, pady=10, sticky='nsew')

    number_label = ttk.Label(control_frame, text='Select Number of Skew-T Plots:')
    number_label.grid(row=0,column=0, padx=5, pady=5, sticky='w')
    number_var = tk.StringVar(tab)
    number_options = list(number_options)
    number_var.trace_add('write', lambda *args: update_station_options(tab, station_frame, number_var))
    number_menu = ttk.Combobox(control_frame, textvariable=number_var, values=number_options)
    number_menu.grid(row=1, column=0, padx=5, pady=5, sticky='ew')

    title_label = ttk.Label(control_frame, text='Create Label:')
    title_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')
    title_text = ttk.Entry(control_frame)
    title_text.grid(row=1, column=1, padx=5, pady=5, sticky='w')

    station = ttk.Label(station_frame, text='Sation:')
    station.grid(row=0, column=1, padx=5, pady=5, sticky='w')
    year = ttk.Label(station_frame, text=f'Year:')
    year.grid(row=0, column=2, padx=5, pady=5, sticky='w')
    month = ttk.Label(station_frame, text='Month:')
    month.grid(row=0, column=3, padx=5, pady=5, sticky='w')
    day = ttk.Label(station_frame, text='Day:')
    day.grid(row=0, column=4, padx=5, pady=5, sticky='w')

    def plot_button_command():
        station_list = [menu.get() for menu in tab.station_menus]
        year_list = [int(menu.get()) for menu in tab.year_menus]
        month_list = [int(menu.get()) for menu in tab.month_menus]
        day_list = [int(menu.get()) for menu in tab.month_menus]
        title_var = title_text.get()
        generate_plot(station_list, year_list, month_list, day_list, title_var, plot_frame)

    plot_button = ttk.Button(control_frame, text='Generate Plot', command=lambda: plot_button_command())
    plot_button.grid(row=0, column=2, padx=5, pady=5, sticky='w')
    save_button = ttk.Button(control_frame, text='Save Plot', command=lambda: save_plot())
    save_button.grid(row=1, column=2, padx=5, pady=5, sticky='w')

def update_station_options(parent, frame, values):
    quantity = int(values.get()) if values.get() else 1
    stations = [
    'ABQ', 'ALB', 'AMA', 'AWE', 'BIS', 'BMX', 'BOI', 'BUF', 'CAR', 'CHS', 'CRP', 
    'DDC', 'DRT', 'DVN', 'EPZ', 'EYW', 'FFC', 'FGZ', 'FWD', 'GGW', 'GRB', 
    'GSO', 'GTJ', 'GYX', 'IAO', 'IDX', 'ILN', 'ILX', 'INL', 'JAN', 'JAX', 
    'LCH', 'LKN', 'LIX', 'LMN', 'LZK', 'MAF', 'MFL', 'MFR', 'MHX', 'MPX', 
    'NKX', 'OAK', 'OKX', 'OTX', 'OUN', 'PIT', 'REV', 'RIW', 'RNK', 'SGF', 
    'SHV', 'SLE', 'SLC', 'TBW', 'TFX', 'TOP', 'TUS', 'UIL', 'WAL', 'XMR']
    years = list(range(1991, 2026))
    months = list(range(1,13))
    day_31 = list(range(1,32))
    day_30 = list(range(1,31))
    day_28 = list(range(1,29))
    day_29 = list(range(1,30))
    for widget in frame.winfo_children():
        widget.destroy()

    station = ttk.Label(frame, text='Sation:')
    station.grid(row=0, column=1, padx=5, pady=5, sticky='w')
    year = ttk.Label(frame, text=f'Year:')
    year.grid(row=0, column=2, padx=5, pady=5, sticky='w')
    month = ttk.Label(frame, text='Month:')
    month.grid(row=0, column=3, padx=5, pady=5, sticky='w')
    day = ttk.Label(frame, text='Day:')
    day.grid(row=0, column=4, padx=5, pady=5, sticky='w')

    def make_day_update(dm, mv, yv):
            return lambda *args: update_day_options(dm, mv, yv, day_31, day_30, day_28, day_29)
    
    parent.station_menus = []
    parent.year_menus = []
    parent.month_menus = []
    parent.day_menus = []

    for i in range(quantity):
        station_label = ttk.Label(frame, text=f'station selection: {i+1}')
        station_label.grid(row=i+1, column=0, padx=3, pady=3, sticky='w')
        station_var = tk.StringVar(parent)
        station_options = stations
        station_menu = ttk.Combobox(frame, textvariable=station_var, values=station_options)
        station_menu.grid(row=i+1, column=1, padx=3, pady=3, sticky='w')
        parent.station_menus.append(station_menu)

        year_var = tk.StringVar(parent)
        year_options = years
        year_menu = ttk.Combobox(frame, textvariable=year_var, values=year_options)
        year_menu.grid(row=i+1, column=2, padx=3, pady=3, sticky='w')
        parent.year_menus.append(year_menu)

        month_var = tk.StringVar(parent)
        month_options = months
        month_menu = ttk.Combobox(frame, textvariable=month_var, values=month_options)
        month_menu.grid(row=i+1, column=3, padx=3, pady=3, sticky='w')
        parent.month_menus.append(month_menu)

        day_var = tk.StringVar(parent)
        day_options = get_day_options(month_var, year_var, day_31, day_30, day_28, day_29)
        day_menu = ttk.Combobox(frame, textvariable=day_var, values=[])
        day_menu.grid(row=i+1, column=4, padx=3, pady=3, sticky='w')
        parent.day_menus.append(day_menu)
        if day_options:
            day_menu.current(0)
        
        year_var.trace_add('write', make_day_update(day_menu, month_var, year_var))
        month_var.trace_add('write', make_day_update(day_menu, month_var, year_var))

def generate_plot(stations, years, months, days, title, plot_frame):
    dates = [dt.datetime(years[i], months[i], days[i], 0) for i in range(len(years))]
    data_frame = create_dataframes(stations, dates)
    
    for widget in plot_frame.winfo_children():
        widget.destroy()

    if dates:
        create_skewt(data_frame, stations, dates, title)
        canvas = FigureCanvasTkAgg(plt.gcf(), master=plot_frame)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack()
        canvas.draw()
    else:
        print('Invalid Selection(s)')

def update_day_options(day_menu, month_var, year_var, day_31, day_30, day_28, day_29):
    day_options = get_day_options(month_var, year_var, day_31, day_30, day_28, day_29)
    day_menu['values'] = day_options
    if day_options:
        day_menu.current(0)
    else:
        day_menu.set('')

def get_day_options(month_var, year_var, day_31, day_30, day_28, day_29):
    try:
        month = int(month_var.get())
        year = int(year_var.get())
    except ValueError:
        return []  # Return an empty list if month or year is not a valid integer

    if month in [1, 3, 5, 7, 8, 10, 12]:
        return day_31
    elif month in [4, 6, 9, 11]:
        return day_30
    elif month == 2:
        if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
            return day_29  # Leap year
        else:
            return day_28  # Non-leap year
    else:
        return []  # Return empty list if the month is invalid.


root = tk.Tk()
root.title('Skew-T Reanalysis')

notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True)

multiple_sation_plot(notebook)

root.mainloop()


