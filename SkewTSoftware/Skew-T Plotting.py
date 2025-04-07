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
    """
    Retrieves upper air data for specified stations and dates.

    Args:
        station_ids (list): List of station IDs.
        dates (list): List of datetime objects representing the dates.

    Returns:
        dict: Dictionary containing dataframes for each station/date combination.
    """
    dataframes = {}  # Initialize an empty dictionary to store dataframes
    for i in range(len(station_ids)):  # Iterate through each station and date
        try:
            # Request data from Wyoming Upper Air service
            df = WyomingUpperAir.request_data(dates[i], station_ids[i])
            dataframes[i] = df  # Store the dataframe in the dictionary
        except Exception as e:
            # Handle any errors during data retrieval
            print(f'Error fetching or processing data for {station_ids[i]} and date {dates[i]}: {e}')
            dataframes[i] = None  # Store None if data retrieval fails
    return dataframes  # Return the dictionary of dataframes

def create_skewt(data, stations, dates, title):
    """
    Creates and plots a Skew-T diagram from the given data.

    Args:
        data (dict): Dictionary of dataframes.
        stations (list): List of station IDs.
        dates (list): List of datetime objects.
        title (str): Title of the plot.
    """
    plt.clf  # Clear the current figure
    fig = plt.figure(figsize=(9, 9))  # Create a new figure
    skew = SkewT(fig, rotation=30)  # Initialize a Skew-T plot

    for i in range(len(stations)):  # Iterate through each station
        df = data[i]  # Get the dataframe for the current station
        if df is None:
            # Handle cases where data is not available
            print(f'No data avaliable for station {stations[i]}')
            return
        try:
            # Extract pressure, temperature, dewpoint, and wind data from the dataframe
            p = df['pressure'].values * units.hPa
            T = df['temperature'].values * units.degC
            Td = df['dewpoint'].values * units.degC
            u = df['u_wind'].values * units.knots
            v = df['v_wind'].values * units.knots
            height = df['height'].values * units.meter
            parcel_profile = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')  # Calculate parcel profile
        except Exception as e:
            # Handle any errors during data processing
            print(f'Error fetching or processing the data: {e}')
            return

        pressure_padding = 20 * units.hPa  # Add padding to labels
        label_pressure = p[0] + pressure_padding

        # Plot temperature, dewpoint, and parcel profile
        skew.plot(p, T, 'r', linewidth=2, label='Temperature')
        skew.plot(p, Td, 'g', linewidth=2, label='Dewpoint')
        skew.plot(p, parcel_profile, 'k', linewidth=2, label='Parcel Profile')
        #add station text to temperature and dewpoint lines
        skew.ax.text(T[0], label_pressure, stations[i], color='r', ha='center', va='top', fontsize='8')
        skew.ax.text(Td[0], label_pressure, stations[i], color='g', ha='center', va='top', fontsize='8')

        # Plot wind barbs
        interval = np.max([1, int(len(p) / 50)])  # Adjust interval based on data length
        skew.plot_barbs(p[::interval], u[::interval], v[::interval], xloc=1.05)  # Plot wind barbs

        # Add dry and moist adiabats
        skew.plot_dry_adiabats(t0=np.arange(233, 533, 10) * units.K, alpha=0.25, color='k')
        skew.plot_moist_adiabats(t0=np.arange(253, 401, 5) * units.K, alpha=0.25, color='k')

        # Set plot limits and labels
        skew.ax.set_xlim(-50, 40)  # Adjust temperature range as needed
        skew.ax.set_ylim(1000, 100)  # Pressure range (reversed)
        skew.ax.set_xlabel('Temperature (°C)')
        skew.ax.set_ylabel('Pressure (hPa)')

    plt.title(f'{title}')  # Set the plot title

def save_plot():
    """
    Saves the current plot to a file.
    """
    filename = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
    if filename:
        plt.savefig(filename)  # Save the plot
        print(f"Plot saved to {filename}")

def multiple_sation_plot(notebook):
    """
    Creates the GUI elements for multiple station Skew-T plotting.

    Args:
        notebook (ttk.Notebook): The notebook widget to add the tab to.
    """
    number_options = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # Options for number of plots

    tab = ttk.Frame(notebook)  # Create a new tab
    notebook.add(tab, text='Comparison Diagrams')  # Add the tab to the notebook

    control_frame = ttk.LabelFrame(tab, text='Number Selection')  # Frame for number selection
    control_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')

    station_frame = ttk.LabelFrame(tab, text='Station Selection')  # Frame for station selection
    station_frame.grid(row=1, column=0, columnspan=1, padx=10, pady=10, sticky='nsew')

    plot_frame = ttk.LabelFrame(tab, text='Plot Frame')  # Frame for the plot
    plot_frame.grid(row=1, column=1, columnspan=1, padx=10, pady=10, sticky='nsew')

    number_label = ttk.Label(control_frame, text='Select Number of Skew-T Plots:')  # Label for number selection
    number_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
    number_var = tk.StringVar(tab)  # Variable to store the selected number
    number_var.trace_add('write', lambda *args: update_station_options(tab, station_frame, number_var))  # Update station options when number changes
    number_menu = ttk.Combobox(control_frame, textvariable=number_var, values=number_options)  # Combobox for number selection
    number_menu.grid(row=1, column=0, padx=5, pady=5, sticky='ew')

    title_label = ttk.Label(control_frame, text='Create Label:') #label for title
    title_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')
    title_text = ttk.Entry(control_frame) #entry for title
    title_text.grid(row=1, column=1, padx=5, pady=5, sticky='w')

    station = ttk.Label(station_frame, text='Sation:') #station label
    station.grid(row=0, column=1, padx=5, pady=5, sticky='w')
    year = ttk.Label(station_frame, text=f'Year:') #year label
    year.grid(row=0, column=2, padx=5, pady=5, sticky='w')
    month = ttk.Label(station_frame, text='Month:') #month label
    month.grid(row=0, column=3, padx=5, pady=5, sticky='w')
    day = ttk.Label(station_frame, text='Day:') #day label
    day.grid(row=0, column=4, padx=5, pady=5, sticky='w')

    def plot_button_command():
        """
        Handles the plot button click event.
        """
        station_list = [menu.get() for menu in tab.station_menus] #get station list
        year_list = [int(menu.get()) for menu in tab.year_menus] #get year list
        month_list = [int(menu.get()) for menu in tab.month_menus] #get month list
        day_list = [int(menu.get()) for menu in tab.day_menus] #get day list
        title_var = title_text.get() #get title
        generate_plot(station_list, year_list, month_list, day_list, title_var, plot_frame) #generate plot

    plot_button = ttk.Button(control_frame, text='Generate Plot', command=lambda: plot_button_command()) #create plot button
    plot_button.grid(row=0, column=2, padx=5, pady=5, sticky='w')
    save_button = ttk.Button(control_frame, text='Save Plot', command=lambda: save_plot()) #create save button
    save_button.grid(row=1, column=2, padx=5, pady=5, sticky='w')

def update_station_options(parent, frame, values):
    """
    Updates the station selection options based on the selected number of plots.

    Args:
        parent (tk.Widget): The parent widget.
        frame (ttk.Frame): The frame containing the station selection options.
        values (tk.StringVar): The variable containing the selected number of plots.
    """
    quantity = int(values.get()) if values.get() else 1  # Get the selected number
    stations = [
        'ABQ', 'ALB', 'AMA', 'AWE', 'BIS', 'BMX', 'BOI', 'BUF', 'CAR', 'CHS', 'CRP',
        'DDC', 'DRT', 'DVN', 'EPZ', 'EYW', 'FFC', 'FGZ', 'FWD', 'GGW', 'GRB',
        'GSO', 'GTJ', 'GYX', 'IAO', 'IDX', 'ILN', 'ILX', 'INL', 'JAN', 'JAX',
        'LCH', 'LKN', 'LIX', 'LMN', 'LZK', 'MAF', 'MFL', 'MFR', 'MHX', 'MPX',
        'NKX', 'OAK', 'OKX', 'OTX', 'OUN', 'PIT', 'REV', 'RIW', 'RNK', 'SGF',
        'SHV', 'SLE', 'SLC', 'TBW', 'TFX', 'TOP', 'TUS', 'UIL', 'WAL', 'XMR'
    ] #list of station codes
    years = list(range(1991, 2026)) #list of years
    months = list(range(1, 13)) #list of months
    day_31 = list(range(1, 32)) #list of days for 31 day months
    day_30 = list(range(1, 31)) #list of days for 30 day months
    day_28 = list(range(1, 29)) #list of days for 28 day months
    day_29 = list(range(1, 30)) #list of days for 29 day months
    for widget in frame.winfo_children():
        widget.destroy() #destroy previous widgets

    station = ttk.Label(frame, text='Sation:') #station label
    station.grid(row=0, column=1, padx=5, pady=5, sticky='w')
    year = ttk.Label(frame, text=f'Year:') #year label
    year.grid(row=0, column=2, padx=5, pady=5, sticky='w')
    month = ttk.Label(frame, text='Month:') #month label
    month.grid(row=0, column=3, padx=5, pady=5, sticky='w')
    day = ttk.Label(frame, text='Day:') #day label
    day.grid(row=0, column=4, padx=5, pady=5, sticky='w')

    def make_day_update(dm, mv, yv):
        """
        Creates a function to update the day options based on month and year.
        """
        return lambda *args: update_day_options(dm, mv, yv, day_31, day_30, day_28, day_29)

    parent.station_menus = [] #list of station menus
    parent.year_menus = [] #list of year menus
    parent.month_menus = [] #list of month menus
    parent.day_menus = [] #list of day menus

    for i in range(quantity): #loop through the number of plots
        station_label = ttk.Label(frame, text=f'station selection: {i+1}') #station label
        station_label.grid(row=i + 1, column=0, padx=3, pady=3, sticky='w')
        station_var = tk.StringVar(parent) #station variable
        station_options = stations #station options
        station_menu = ttk.Combobox(frame, textvariable=station_var, values=station_options) #station combobox
        station_menu.grid(row=i + 1, column=1, padx=3, pady=3, sticky='w')
        parent.station_menus.append(station_menu) #add station menu to list

        year_var = tk.StringVar(parent) #year variable
        year_options = years #year options
        year_menu = ttk.Combobox(frame, textvariable=year_var, values=year_options) #year combobox
        year_menu.grid(row=i + 1, column=2, padx=3, pady=3, sticky='w')
        parent.year_menus.append(year_menu) #add year menu to list

        month_var = tk.StringVar(parent) #month variable
        month_options = months #month options
        month_menu = ttk.Combobox(frame, textvariable=month_var, values=month_options) #month combobox
        month_menu.grid(row=i + 1, column=3, padx=3, pady=3, sticky='w')
        parent.month_menus.append(month_menu) #add month menu to list

        day_var = tk.StringVar(parent) #day variable
        day_options = get_day_options(month_var, year_var, day_31, day_30, day_28, day_29) #get day options
        day_menu = ttk.Combobox(frame, textvariable=day_var, values=[]) #day combobox
        day_menu.grid(row=i + 1, column=4, padx=3, pady=3, sticky='w')
        parent.day_menus.append(day_menu) #add day menu to list
        if day_options:
            day_menu.current(0) #set day to first option if available

        year_var.trace_add('write', make_day_update(day_menu, month_var, year_var)) #add trace to year variable
        month_var.trace_add('write', make_day_update(day_menu, month_var, year_var)) #add trace to month variable

def generate_plot(stations, years, months, days, title, plot_frame):
    """
    Generates and displays the Skew-T plot.

    Args:
        stations (list): List of station IDs.
        years (list): List of years.
        months (list): List of months.
        days (list): list of days.
        title (str): Title of the plot.
        plot_frame (ttk.Frame): The frame to display the plot in.
    """
    dates = [dt.datetime(years[i], months[i], days[i], 0) for i in range(len(years))] #create datetime objects
    data_frame = create_dataframes(stations, dates) #get dataframes

    for widget in plot_frame.winfo_children():
        widget.destroy() #destroy previous widgets
    if dates:
        create_skewt(data_frame, stations, dates, title) #create Skew-T plot
        canvas = FigureCanvasTkAgg(plt.gcf(), master=plot_frame) #create canvas
        canvas_widget = canvas.get_tk_widget() #get canvas widget
        canvas_widget.pack() #pack canvas widget
        canvas.draw() #draw canvas
    else:
        print('Invalid Selection(s)')

def update_day_options(day_menu, month_var, year_var, day_31, day_30, day_28, day_29):
    """
    Updates the day options based on the selected month and year.

    Args:
        day_menu (ttk.Combobox): The day combobox.
        month_var (tk.StringVar): The variable containing the selected month.
        year_var (tk.StringVar): The variable containing the selected year.
        day_31 (list): List of days for 31-day months.
        day_30 (list): List of days for 30-day months.
        day_28 (list): List of days for February in non-leap years.
        day_29 (list): List of days for February in leap years.
    """
    day_options = get_day_options(month_var, year_var, day_31, day_30, day_28, day_29) #get day options
    day_menu['values'] = day_options #set day options
    if day_options:
        day_menu.current(0) #set day to first option if available
    else:
        day_menu.set('')

def get_day_options(month_var, year_var, day_31, day_30, day_28, day_29):
    """
    Gets the day options based on the selected month and year.

    Args:
        month_var (tk.StringVar): The variable containing the selected month.
        year_var (tk.StringVar): The variable containing the selected year.
        day_31 (list): List of days for 31-day months.
        day_30 (list): List of days for 30-day months.
        day_28 (list): List of days for February in non-leap years.
        day_29 (list): List of days for February in leap years.

    Returns:
        list: List of day options.
    """
    try:
        month = int(month_var.get()) #get month
        year = int(year_var.get()) #get year
    except ValueError:
        return []  # Return an empty list if month or year is not a valid integer

    if month in [1, 3, 5, 7, 8, 10, 12]: #31 day months
        return day_31
    elif month in [4, 6, 9, 11]: #30 day months
        return day_30
    elif month == 2: #february
        if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0): #leap year
            return day_29
        else:
            return day_28 #non leap year
    else:
        return []  # Return empty list if the month is invalid.


root = tk.Tk() #create root window
root.title('Skew-T Reanalysis') #set title

notebook = ttk.Notebook(root) #create notebook
notebook.pack(fill='both', expand=True) #pack notebook

multiple_sation_plot(notebook) #create multiple station plot tab

root.mainloop() #start main loop