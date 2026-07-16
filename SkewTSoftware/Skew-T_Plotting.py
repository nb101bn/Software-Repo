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
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import time
from scipy.interpolate import interp1d
from PIL import Image, ImageGrab

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
        number_retries = 3
        for retries in range(number_retries):
            try:
                # Request data from Wyoming Upper Air service
                df = WyomingUpperAir.request_data(dates[i], station_ids[i])
                dataframes[i] = df  # Store the dataframe in the dictionary
            except Exception as e:
                # Handle any errors during data retrieval
                print(f'Attempt {retries+1} failed: {e}')
                if retries < number_retries-1:
                    time.sleep(5)
                else:
                    print(f'Error fetching or processing data for {station_ids[i]} and date {dates[i]}: {e}')
                    dataframes[i] = None  # Store None if data retrieval fails
    return dataframes  # Return the dictionary of dataframes

def create_skewt(data, stations, dates, title, fig_size):
    """
    Creates and plots a Skew-T diagram from the given data.

    Args:
        data (dict): Dictionary of dataframes.
        stations (list): List of station IDs.
        dates (list): List of datetime objects.
        title (str): Title of the plot.
    """
    plt.clf  # Clear the current figure
    fig = plt.figure(figsize=fig_size)  # Create a new figure
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
            #parcel_profile = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')  # Calculate parcel profile
        except Exception as e:
            # Handle any errors during data processing
            print(f'Error fetching or processing the data: {e}')
            return

        pressure_padding = 20 * units.hPa  # Add padding to labels
        label_pressure = p[0] + pressure_padding

        # Plot temperature, dewpoint, and parcel profile
        skew.plot(p, T, 'r', linewidth=2, label='Temperature')
        skew.plot(p, Td, 'g', linewidth=2, label='Dewpoint')
        #skew.plot(p, parcel_profile, 'k', linewidth=2, label='Parcel Profile')
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

def create_mean_skewt(data, stations, dates, title, fig_size):
    """
    Creates and plots a Skew-T diagram from the average of the given data,
    including CAPE and CIN, handling datasets with different sizes using interpolation.
    """
    plt.clf()
    fig = plt.figure(figsize=fig_size)
    skew = SkewT(fig, rotation=30)

    valid_dataframes = [df for df in data.values() if df is not None]

    if not valid_dataframes:
        print("No valid data available for averaging.")
        return

    reference_p = valid_dataframes[0]['pressure'].values * units.hPa
    common_p = reference_p

    T_interp_list = []
    Td_interp_list = []
    u_interp_list = []
    v_interp_list = []
    height_interp_list = []

    for df in valid_dataframes:
        try:
            p = df['pressure'].values * units.hPa
            T = df['temperature'].values * units.degC
            Td = df['dewpoint'].values * units.degC
            u = df['u_wind'].values * units.knots
            v = df['v_wind'].values * units.knots
            height = df['height'].values * units.meter

            T_interp = interp1d(p, T, bounds_error=False)(common_p) * units.degC
            Td_interp = interp1d(p, Td, bounds_error=False)(common_p) * units.degC
            u_interp = interp1d(p, u, bounds_error=False)(common_p) * units.knots
            v_interp = interp1d(p, v, bounds_error=False)(common_p) * units.knots
            height_interp = interp1d(p, height, bounds_error=False)(common_p) * units.meter

            T_interp_list.append(T_interp)
            Td_interp_list.append(Td_interp)
            u_interp_list.append(u_interp)
            v_interp_list.append(v_interp)
            height_interp_list.append(height_interp)

        except Exception as e:
            print(f'Error processing data: {e}')
            return

    T_avg = np.nanmean(np.array(T_interp_list), axis=0)
    Td_avg = np.nanmean(np.array(Td_interp_list), axis=0)
    u_avg = np.nanmean(np.array(u_interp_list), axis=0)
    v_avg = np.nanmean(np.array(v_interp_list), axis=0)
    height_avg = np.nanmean(np.array(height_interp_list), axis=0)

    pressure_padding = 20 * units.hPa
    label_pressure = common_p[0] + pressure_padding

    skew.plot(common_p, T_avg, 'r', linewidth=2, label='Average Temperature')
    skew.plot(common_p, Td_avg, 'g', linewidth=2, label='Average Dewpoint')
    
    skew.ax.text(T_avg[0], label_pressure, 'Average', color='r', ha='center', va='top', fontsize='8')
    skew.ax.text(Td_avg[0], label_pressure, 'Average', color='g', ha='center', va='top', fontsize='8')

    interval = np.max([1, int(len(common_p) / 50)])
    skew.plot_barbs(common_p[::interval], u_avg[::interval], v_avg[::interval], xloc=1.05)

    skew.plot_dry_adiabats(t0=np.arange(233, 533, 10) * units.K, alpha=0.25, color='k')
    skew.plot_moist_adiabats(t0=np.arange(253, 401, 5) * units.K, alpha=0.25, color='k')

    skew.ax.set_xlim(-50, 40)
    skew.ax.set_ylim(1000, 100)
    skew.ax.set_xlabel('Temperature (°C)')
    skew.ax.set_ylabel('Pressure (hPa)')

    plt.title(f'{title}')

def calculate_thermo_params(df):
    """Calculates thermodynamic parameters from a DataFrame."""
    if df is None:
        return {}

    p = df['pressure'].values * units.hPa
    T = df['temperature'].values * units.degC
    Td = df['dewpoint'].values * units.degC

    try:
        # Calculate CAPE and CIN
        parcel_profile = mpcalc.parcel_profile(p, T[0], Td[0])
        print(f'Parcel Profile: {parcel_profile}')
        parcel_profile_temp = parcel_profile.to('degC')
        print(f'Parcel Profile Temp: {parcel_profile_temp}')

        cape, cin = mpcalc.cape_cin(p, T, Td, parcel_profile_temp)
        print(f'Cape, Cin: {cape}, {cin}')

        # Calculate Lifted Index (LI)
        li = mpcalc.lifted_index(p, T, parcel_profile_temp)
        print(f'Lifted Index: {li}')

        # Calculate Pwat
        
        Pwat = mpcalc.precipitable_water(p, Td)
        print(f'Pwat: {Pwat}')

        most_unstable_parcel = mpcalc.most_unstable_parcel(p, T, Td)
        print(f'Most Unstable Parcel: {most_unstable_parcel}')

        #e = mpcalc.vapor_pressure(Td)
        #mixing_ratio = mpcalc.mixing_ratio(e, p, molecular_weight_ratio=0.6219569100577033)
        #print(f'Mixing Ratio: {mixing_ratio}')

        # You can add more calculations as needed

        return {
            'MU CAPE': cape.to('J/kg').magnitude,
            'MU Parcel': most_unstable_parcel[0].to('hPa').magnitude,
            'LI': li.to('delta_degC').magnitude,
            'Pwat': Pwat.to('mm').magnitude,
            #'Mixing Ratio': mixing_ratio.to('g/kg').magnitude,
            'Parcel Profile': parcel_profile[0].to('degC').magnitude,
            # Add more parameters here
        }
    except Exception as e:
        print(f"Error calculating thermo params: {e}")
        return {}
    
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

def save_plot():
    """
    Saves the current plot to a file.
    """
    filename = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
    if filename:
        plt.savefig(filename)  # Save the plot
        print(f"Plot saved to {filename}")

def save_thermo_plot(tab):
    """Saves the current plot or Treeview to a file."""

    if hasattr(tab, 'tree'):  # Check if Treeview exists
        tree = tab.tree
        x, y, width, height = tree.winfo_rootx(), tree.winfo_rooty(), tree.winfo_width(), tree.winfo_height()
        image = ImageGrab.grab(bbox=(x, y, x + width, y + height))
        filename = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if filename:
            image.save(filename)
            print(f"Treeview saved to {filename}")
        tab.tree = None #reset the tree to none so it doesnt try to save a tree that doesnt exist
    else:  # Save the Matplotlib plot (if any)
        filename = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if filename:
            plt.savefig(filename)
            print(f"Plot saved to {filename}")

def multiple_sation_plot(notebook):
    """
    Creates the GUI elements for multiple station Skew-T plotting.

    Args:
        notebook (ttk.Notebook): The notebook widget to add the tab to.
    """
    number_options = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]  # Options for number of plots

    tab = ttk.Frame(notebook)  # Create a new tab
    notebook.add(tab, text='Observation Comparison Diagrams')  # Add the tab to the notebook

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
    hour = ttk.Label(station_frame, text='Hour:')
    hour.grid(row=0, column=5, padx=5, pady=5, sticky='w')

    def plot_button_command():
        """
        Handles the plot button click event.
        """
        station_list = [menu.get() for menu in tab.station_menus] #get station list
        year_list = [int(menu.get()) for menu in tab.year_menus] #get year list
        month_list = [int(menu.get()) for menu in tab.month_menus] #get month list
        day_list = [int(menu.get()) for menu in tab.day_menus] #get day list
        hour_list = [int(menu.get()) for menu in tab.hour_menus]
        title_var = title_text.get() #get title
        plot_var = plot_type.get()
        print(plot_var)
        generate_plot(station_list, year_list, month_list, day_list, hour_list, title_var, plot_frame, plot_var) #generate plot

    plot_button = ttk.Button(control_frame, text='Generate Plot', command=lambda: plot_button_command()) #create plot button
    plot_button.grid(row=0, column=2, padx=5, pady=5, sticky='w')
    save_button = ttk.Button(control_frame, text='Save Plot', command=lambda: save_plot()) #create save button
    save_button.grid(row=1, column=2, padx=5, pady=5, sticky='w')

    plot_type = tk.StringVar(value='all')
    plot_all_radio = ttk.Radiobutton(control_frame, text='Plot All',variable=plot_type, value='all')
    plot_mean_radio = ttk.Radiobutton(control_frame, text='Plot Mean', variable=plot_type, value='mean')
    plot_all_radio.grid(row=0, column=3, padx=5, pady=5, sticky='w')
    plot_mean_radio.grid(row=1, column=3, padx=5, pady=5, sticky='w')

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
        max_width = screen_width
        max_height = screen_height
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

def thermal_station_plots(notebook):
    tab = ttk.Frame(notebook)
    notebook.add(tab, text='Thermals')

    def change_grid(plot_type):
        plot_var = plot_type.get()
        
        for widget in control_frame.winfo_children():
            widget.destroy()
        for widget in station_frame.winfo_children():
            widget.destroy()
        
        if plot_var == 'single':
            station = ttk.Label(station_frame, text='Sation:') #station label
            station.grid(row=0, column=1, padx=5, pady=5, sticky='w')
            year = ttk.Label(station_frame, text=f'Year:') #year label
            year.grid(row=0, column=2, padx=5, pady=5, sticky='w')
            month = ttk.Label(station_frame, text='Month:') #month label
            month.grid(row=0, column=3, padx=5, pady=5, sticky='w')
            day = ttk.Label(station_frame, text='Day:') #day label
            day.grid(row=0, column=4, padx=5, pady=5, sticky='w')
            hour = ttk.Label(station_frame, text='Hour:')
            hour.grid(row=0, column=5, padx=5, pady=5, sticky='w')

            stations = ['ABQ', 'ABR', 'ALY', 'AMA', 'APX', 'BIS', 'BMX', 'BOI', 'BRO', 'BUF',
                 'CAR', 'CHS', 'CHH', 'CRP', 'DDC', 'DNR', 'DRT', 'DTX', 'DVN', 'EPZ', 
                 'EYW', 'FFC', 'FGZ', 'FWD', 'GGW', 'GJT', 'GRB', 'GSO', 'GYX', 'ILN', 
                 'ILX', 'INL', 'JAN', 'JAX', 'LBF', 'LCH', 'LKN', 'LIX', 'LWX', 'LZK', 
                 'MAF', 'MFL', 'MFR', 'MHX', 'MPX', 'NKX', 'OAK', 'OAX', 'OHX', 'OKX', 
                 'OTX', 'OUN', 'PBZ', 'REV', 'RIW', 'RNK', 'SGF', 'SHV', 'SLC', 'SLE', 
                 'TAE', 'TBW', 'TFX', 'TOP', 'TUS', 'UIL', 'UNR', 'VEF', 'WAL']
            years = list(range(1991, 2026)) #list of years
            months = list(range(1, 13)) #list of months
            day_31 = list(range(1, 32)) #list of days for 31 day months
            day_30 = list(range(1, 31)) #list of days for 30 day months
            day_28 = list(range(1, 29)) #list of days for 28 day months
            day_29 = list(range(1, 30)) #list of days for 29 day months
            hours = [0, 12]

            def make_day_update(dm, mv, yv):
                """
                Creates a function to update the day options based on month and year.
                """
                return lambda *args: update_day_options(dm, mv, yv, day_31, day_30, day_28, day_29)

            def plot_button_command():
                """
                Handles the plot button click event.
                """
                station_list = station_menu.get()
                year_list = year_menu.get()
                month_list = month_menu.get()
                day_list = day_menu.get()
                hour_list = hour_menu.get()
                title_var = title_text.get() #get title
                plot_var = plot_type.get()
                generate_thermal_plot(station_list, year_list, month_list, day_list, hour_list, title_var, plot_frame, plot_var, tab)
            
            title_label = ttk.Label(control_frame, text='Plot Title:')
            title_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            title_text = ttk.Entry(control_frame)
            title_text.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            
            plot_button = ttk.Button(control_frame, text='Generate Plot', command=lambda: plot_button_command()) #create plot button
            plot_button.grid(row=0, column=1, padx=5, pady=5, sticky='w')
            save_button = ttk.Button(control_frame, text='Save Plot', command=lambda: save_thermo_plot(tab)) #create save button
            save_button.grid(row=1, column=1, padx=5, pady=5, sticky='w')

            station_label = ttk.Label(station_frame, text=f'station selection:') #station label
            station_label.grid(row=1, column=0, padx=3, pady=3, sticky='w')
            station_var = tk.StringVar(tab) #station variable
            station_options = stations #station options
            station_menu = ttk.Combobox(station_frame, textvariable=station_var, values=station_options) #station combobox
            station_menu.grid(row=1, column=1, padx=3, pady=3, sticky='w')

            year_var = tk.StringVar(tab) #year variable
            year_options = years #year options
            year_menu = ttk.Combobox(station_frame, textvariable=year_var, values=year_options) #year combobox
            year_menu.grid(row=1, column=2, padx=3, pady=3, sticky='w')

            month_var = tk.StringVar(tab) #month variable
            month_options = months #month options
            month_menu = ttk.Combobox(station_frame, textvariable=month_var, values=month_options) #month combobox
            month_menu.grid(row=1, column=3, padx=3, pady=3, sticky='w')

            day_var = tk.StringVar(tab) #day variable
            day_options = get_day_options(month_var, year_var, day_31, day_30, day_28, day_29) #get day options
            day_menu = ttk.Combobox(station_frame, textvariable=day_var, values=[]) #day combobox
            day_menu.grid(row=1, column=4, padx=3, pady=3, sticky='w')
            if day_options:
                day_menu.current(0) #set day to first option if available
            
            hour_var = tk.StringVar(tab)
            hour_options = hours
            hour_menu = ttk.Combobox(station_frame, textvariable=hour_var, values=hour_options)
            hour_menu.grid(row=1, column=5, padx=5, pady=5, sticky='w')

            year_var.trace_add('write', make_day_update(day_menu, month_var, year_var)) #add trace to year variable
            month_var.trace_add('write', make_day_update(day_menu, month_var, year_var)) #add trace to month variable
        
        elif plot_var == 'mean':
            number_options = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]

            station = ttk.Label(station_frame, text='Sation:') #station label
            station.grid(row=0, column=1, padx=5, pady=5, sticky='w')
            year = ttk.Label(station_frame, text=f'Year:') #year label
            year.grid(row=0, column=2, padx=5, pady=5, sticky='w')
            month = ttk.Label(station_frame, text='Month:') #month label
            month.grid(row=0, column=3, padx=5, pady=5, sticky='w')
            day = ttk.Label(station_frame, text='Day:') #day label
            day.grid(row=0, column=4, padx=5, pady=5, sticky='w')
            hour = ttk.Label(station_frame, text='Hour:')
            hour.grid(row=0, column=5, padx=5, pady=5, sticky='w')

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
            hour = ttk.Label(station_frame, text='Hour:')
            hour.grid(row=0, column=5, padx=5, pady=5, sticky='w')

            def plot_button_command():
                """
                Handles the plot button click event.
                """
                station_list = [menu.get() for menu in tab.station_menus] #get station list
                year_list = [int(menu.get()) for menu in tab.year_menus] #get year list
                month_list = [int(menu.get()) for menu in tab.month_menus] #get month list
                day_list = [int(menu.get()) for menu in tab.day_menus] #get day list
                hour_list = [int(menu.get()) for menu in tab.hour_menus]
                title_var = title_text.get() #get title
                plot_var = plot_type.get()
                print(plot_var)
                generate_thermal_plot(station_list, year_list, month_list, day_list, hour_list, title_var, plot_frame, plot_var, tab) #generate plot

            plot_button = ttk.Button(control_frame, text='Generate Plot', command=lambda: plot_button_command()) #create plot button
            plot_button.grid(row=0, column=2, padx=5, pady=5, sticky='w')
            save_button = ttk.Button(control_frame, text='Save Plot', command=lambda: save_thermo_plot(tab)) #create save button
            save_button.grid(row=1, column=2, padx=5, pady=5, sticky='w')
            
    variable_frame = ttk.LabelFrame(tab, text='Variable Selection')
    variable_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')

    control_frame = ttk.LabelFrame(tab, text='Control Frame')
    control_frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')

    station_frame = ttk.LabelFrame(tab, text='Select Station')
    station_frame.grid(row=1, column=0, padx=10, pady=10, sticky='nsew')

    plot_frame = ttk.LabelFrame(tab, text='Plot Area')
    plot_frame.grid(row=1, column=1, padx=10, pady=10, sticky='nsew')

    plot_label = ttk.Label(variable_frame, text='Select Plot Type:')
    plot_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')

    plot_type = tk.StringVar(value='single')
    plot_single_radio = ttk.Radiobutton(variable_frame, text='Single Station', variable=plot_type, value='single', command= lambda *args: change_grid(plot_type))
    plot_single_radio.grid(row=1, column=0, padx=5, pady=5, sticky='w')
    plot_mean_radio = ttk.Radiobutton(variable_frame, text='Mean Plot', variable=plot_type, value='mean', command= lambda *args: change_grid(plot_type))
    plot_mean_radio.grid(row=2, column=0, padx=5, pady=5, sticky='w')
    

def model_station_plots(notebook):

    tab = ttk.Frame(notebook)
    notebook.add(tab, text = 'Model Comparison Plots')

    control_frame = ttk.LabelFrame(tab, text='Type Of Plots')
    control_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')

    date_time_frame = ttk.LabelFrame(tab, text='Options')
    date_time_frame.grid(row=1, column=0, padx=10, pady=10, sticky='nsew')

    plot_area_frame = ttk.LabelFrame(tab, text='Plot Area')
    plot_area_frame.grid(row=1, column=1, padx=10, pady=10, sticky='nsew')

    plot_type_label = ttk.Label(control_frame, text='Select Type Of Plot:')
    plot_type_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')



def update_station_options(parent, frame, values):
    """
    Updates the station selection options based on the selected number of plots.

    Args:
        parent (tk.Widget): The parent widget.
        frame (ttk.Frame): The frame containing the station selection options.
        values (tk.StringVar): The variable containing the selected number of plots.
    """
    stations = ['ABQ', 'ABR', 'ALY', 'AMA', 'APX', 'BIS', 'BMX', 'BOI', 'BRO', 'BUF',
                 'CAR', 'CHS', 'CHH', 'CRP', 'DDC', 'DNR', 'DRT', 'DTX', 'DVN', 'EPZ', 
                 'EYW', 'FFC', 'FGZ', 'FWD', 'GGW', 'GJT', 'GRB', 'GSO', 'GYX', 'ILN', 
                 'ILX', 'INL', 'JAN', 'JAX', 'LBF', 'LCH', 'LKN', 'LIX', 'LWX', 'LZK', 
                 'MAF', 'MFL', 'MFR', 'MHX', 'MPX', 'NKX', 'OAK', 'OAX', 'OHX', 'OKX', 
                 'OTX', 'OUN', 'PBZ', 'REV', 'RIW', 'RNK', 'SGF', 'SHV', 'SLC', 'SLE', 
                 'TAE', 'TBW', 'TFX', 'TUS', 'TOP', 'UIL', 'UNR', 'VEF', 'WAL']
    quantity = int(values.get()) if values.get() else 1  # Get the selected number
    years = list(range(1991, 2026)) #list of years
    months = list(range(1, 13)) #list of months
    day_31 = list(range(1, 32)) #list of days for 31 day months
    day_30 = list(range(1, 31)) #list of days for 30 day months
    day_28 = list(range(1, 29)) #list of days for 28 day months
    day_29 = list(range(1, 30)) #list of days for 29 day months
    hours = [0, 12]
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
    hour = ttk.Label(frame, text='Hour:')
    hour.grid(row=0, column=5, padx=5, pady=5, sticky='w')

    def make_day_update(dm, mv, yv):
        """
        Creates a function to update the day options based on month and year.
        """
        return lambda *args: update_day_options(dm, mv, yv, day_31, day_30, day_28, day_29)

    parent.station_menus = [] #list of station menus
    parent.year_menus = [] #list of year menus
    parent.month_menus = [] #list of month menus
    parent.day_menus = [] #list of day menus
    parent.hour_menus = []

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
        
        hour_var = tk.StringVar(parent)
        hour_options = hours
        hour_menu = ttk.Combobox(frame, textvariable=hour_var, values=hour_options)
        hour_menu.grid(row=i+1, column=5, padx=5, pady=5, sticky='w')
        parent.hour_menus.append(hour_menu)

        year_var.trace_add('write', make_day_update(day_menu, month_var, year_var)) #add trace to year variable
        month_var.trace_add('write', make_day_update(day_menu, month_var, year_var)) #add trace to month variable

def generate_thermal_plot(station_list, year_list, month_list, day_list, hour_list, title_var, plot_frame, plot_var, parent):
    """Generates Skew-T plots and displays thermodynamic parameters."""

    if plot_var == 'single':
        dates = [dt.datetime(int(year_list), int(month_list), int(day_list), int(hour_list))]
        dataframes = create_dataframes([station_list], dates)
    elif plot_var == 'mean':
        dates = [dt.datetime(year_list[i], month_list[i], day_list[i], hour_list[i]) for i in range(len(station_list))]
        dataframes = create_dataframes(station_list, dates)

    # Display thermodynamic parameters in a table
    display_thermo_params(station_list, dataframes, plot_frame, title_var, plot_var, parent)

def display_thermo_params(station_list, dataframes, plot_frame, title_var, plot_var, parent):
    """Displays thermodynamic parameters in a Treeview table."""

    for widget in plot_frame.winfo_children():
        widget.destroy()

    tree = ttk.Treeview(plot_frame)

    tree['columns'] = ('Station', 'MU CAPE', 'MU Parcel', 'LI', 'Pwat', 'Parcel Profile')  # Add more columns as needed

    tree.column('#0', width=0, stretch=tk.NO)
    tree.column('Station', anchor=tk.W, width=100)
    tree.column('MU CAPE', anchor=tk.CENTER, width=100)
    tree.column('MU Parcel', anchor=tk.CENTER, width=100)
    tree.column('LI', anchor=tk.CENTER, width=100)
    tree.column('Pwat', anchor=tk.CENTER, width=100)
    #tree.column('Mixing Ratio', anchor=tk.CENTER, width=80)
    tree.column('Parcel Profile', anchor=tk.CENTER, width=100)

    tree.heading('#0', text='', anchor=tk.W)
    tree.heading('Station', text='Station', anchor=tk.W)
    tree.heading('MU CAPE', text='MU CAPE (J/kg)', anchor=tk.CENTER)
    tree.heading('MU Parcel', text='MU Parcel (hPa)', anchor=tk.CENTER)
    tree.heading('LI', text='LI (°C)', anchor=tk.CENTER)
    tree.heading('Pwat', text='Pwat (mm)', anchor=tk.CENTER)
    #tree.heading('Mixing Ratio', text='Mixing Ratio (g/kg)', anchor=tk.CENTER)
    tree.heading('Parcel Profile', text='Parcel Profile (°C)', anchor=tk.CENTER)

    if plot_var == 'single':
        if isinstance(dataframes, dict):
            print(plot_var)
            print(dataframes[0])
            params = calculate_thermo_params(dataframes[0])
            if params:
                tree.insert('', tk.END, values=(
                    f"{station_list}",
                    params.get('MU CAPE', 'N/A'),
                    params.get('MU Parcel', 'N/A'),
                    params.get('LI', 'N/A'),
                    params.get('Pwat', 'N/A'),
                    #params.get('Mixing Ratio', 'N/A'),
                    params.get('Parcel Profile', 'N/A')
                ))
    elif plot_var == 'mean':
        mu_cape_list = []
        mu_parcel_list = []
        li_list = []
        pwat_list = []
        #mixing_ratio_list = []
        parcel_profile_list = []

        valid_dfs = [df for df in dataframes.values() if df is not None]

        if valid_dfs:
            for df in valid_dfs:
                params = calculate_thermo_params(df)
                if params:
                    mu_cape_list.append(params.get('MU CAPE', np.nan))
                    mu_parcel_list.append(params.get('MU Parcel', np.nan))
                    li_list.append(params.get('LI', np.nan))
                    pwat_list.append(params.get('Pwat', np.nan))
                    #mixing_ratio_list.append(params.get('Mixing Ratio', np.nan))
                    parcel_profile_list.append(params.get('Parcel Profile', np.nan))

            mean_cape = np.nanmean(mu_cape_list)
            mean_parcel = np.nanmean(mu_parcel_list)
            mean_li = np.nanmean(li_list)
            mean_pwat = np.nanmean(pwat_list)
            #mean_mixing_ratio = np.nanmean(mixing_ratio_list)
            mean_parcel_profile = np.nanmean(parcel_profile_list)


            tree.insert('', tk.END, values=(
                f"Mean",
                mean_cape,
                mean_parcel,
                mean_li,
                mean_pwat,
                #mean_mixing_ratio,
                mean_parcel_profile
            ))
    
    if title_var:  # Insert title row if title_var is not empty
        tree.insert('', tk.END, values=('', '', title_var, '', ''), tags=('title',))
        tree.tag_configure('title', font=('TkDefaultFont', 12, 'bold'))
        title_width = len(title_var)*8 +50
        tree.column('#2', width=title_width, stretch=tk.YES)

    parent.tree = tree
    tree.pack(pady=10)

def generate_plot(stations, years, months, days, hours, title, plot_frame, plot_var):
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
    dates = [dt.datetime(years[i], months[i], days[i], hours[i]) for i in range(len(years))] #create datetime objects
    data_frame = create_dataframes(stations, dates) #get dataframes

    for widget in plot_frame.winfo_children():
        widget.destroy() #destroy previous widgets
    if dates:
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        max_width = screen_width*0.8
        max_height = screen_height*0.8
        aspect_ratio = 1
        fig_size = (min(max_width / 100, max_height / 100), min(max_width / 100, max_height / 100))
        if plot_var == 'mean':
            create_mean_skewt(data_frame, stations, dates, title, fig_size)
        elif plot_var == 'all':
            create_skewt(data_frame, stations, dates, title, fig_size) #create Skew-T plot
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
thermal_station_plots(notebook)
create_event_map_gui(notebook)

root.mainloop() #start main loop