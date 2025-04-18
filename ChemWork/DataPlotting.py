import os
import tkinter as tk
from tkinter import ttk
from tkinter import Canvas
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import pickle

def preload_data(Base_Path_Dir, cache_file='preloaded_data.parquet'):
    if os.path.exists(cache_file):
        try:
            return pd.read_parquet(cache_file).to_dict()
        except Exception as e:
            print(f'Error loading from parquet cache: {e}, attempting to load from pickle cache.')
            try:
                with open('preloaded_data.pkl', 'rb') as f:
                    return pickle.load(f)
            except Exception as e2:
                print(f"Error loading from pickle cache: {e2}. Re-loading from excel files.")
    
    preloaded_data = {}
    for run_folder in os.listdir(Base_Path_Dir):
        run_path = os.path.join(Base_Path_Dir, run_folder)
        if os.path.isdir(run_path):
            preloaded_data[run_folder] = {}
            for filename in os.listdir(run_path):
                if filename.endswith('.xlsx'):
                    file_path = os.path.join(run_path, filename)
                    print(f"Processing: {file_path}")
                    preloaded_data[run_folder][filename] = {'column_data': {}, 'column_order': []}
                    try:
                        excel_file = pd.ExcelFile(file_path)
                        df = pd.read_excel(excel_file, header=1)
                        columns = df.columns.tolist()
                        preloaded_data[run_folder][filename]['column_order'] = columns
                        for column in columns:
                            try:
                                data = df[column].to_numpy()
                                preloaded_data[run_folder][filename]['column_data'][column] = data
                            except Exception as column_e:
                                print(f"Error processing column {column} in {file_path}: {column_e}")
                    except Exception as file_e:
                        print(f"Error processing file {file_path}: {file_e}")

    try:
        pd.DataFrame(preloaded_data).to_parquet(cache_file)
    except Exception as parquet_e:
        print(f"Error saving to parquet cache: {parquet_e}")
        try:
            with open("preloaded_data.pkl", "wb") as f:
                pickle.dump(preloaded_data, f)
        except Exception as pickle_e:
            print(f"Error saving to pickle cache: {pickle_e}")
    return preloaded_data

def update_files(tab, run_var, file_menu, file_var):
    run = run_var.get()
    if run:
        files = list(all_data[run].keys())
        file_menu['values'] = files
        if files:
            file_var.set(files[0])

def generate_plot(tab, run_var, file_var, plot_type_var, plot_area_frame):
    run = run_var.get()
    file = file_var.get()
    plot_type = plot_type_var.get()

    if not run or not file:
        return

    data_to_plot = all_data[run][file]['column_data']
    column_names = all_data[run][file]['column_order']

    if not data_to_plot:
        return

    plt.clf()
    if plot_type == 'line':
        plot_line(data_to_plot, column_names)
    elif plot_type == 'box':
        plot_box_whisker(data_to_plot, column_names)
    elif plot_type == 'bar':
        plot_bar(data_to_plot, column_names)
    elif plot_type == 'mean':
        plot_mean(data_to_plot, column_names)
    elif plot_type == 'std':
        plot_std(data_to_plot, column_names)

    # Clear previous plot from the canvas
    for child in plot_area_frame.winfo_children():
        child.destroy()

    # Create a new FigureCanvasTkAgg
    canvas = FigureCanvasTkAgg(plt.gcf(), master=plot_area_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    # Add the Matplotlib toolbar to the frame
    toolbar = NavigationToolbar2Tk(canvas, plot_area_frame)
    toolbar.update()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

def plot_line(data_to_plot, column_names):
    for column, data in data_to_plot.items():
        plt.plot(data, label=column)
    plt.legend()
    plt.xlabel('Index')
    plt.ylabel('Value')
    plt.title('Line Plot')

def plot_box_whisker(data_to_plot, column_names):
    data_list = list(data_to_plot.values())
    plt.boxplot(data_list, labels=column_names, showfliers=False)
    plt.xticks(rotation=45, ha='right')
    plt.ylabel('Value')
    plt.title('Box and Whisker Plot')

def plot_bar(data_to_plot, column_names):
    means = [np.mean(data) for data in data_to_plot.values()]
    plt.bar(column_names, means)
    plt.xticks(rotation=45, ha='right')
    plt.ylabel('Mean Value')
    plt.title('Bar Plot of Means')

def plot_mean(data_to_plot, column_names):
    means = [np.mean(data) for data in data_to_plot.values()]
    plt.plot(column_names, means, marker='o')
    plt.xticks(rotation=45, ha='right')
    plt.ylabel('Mean Value')
    plt.title('Mean Plot')

def plot_std(data_to_plot, column_names):
    stds = [np.std(data) for data in data_to_plot.values()]
    plt.plot(column_names, stds, marker='o')
    plt.xticks(rotation=45, ha='right')
    plt.ylabel('Standard Deviation')
    plt.title('Standard Deviation Plot')

def single_variable_plot(notebook):
    tab = ttk.Frame(notebook)
    notebook.add(tab, text='Single Variable Plots')

    selection_frame = ttk.LabelFrame(tab, text='Data Selection')
    selection_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
    plot_type_frame = ttk.LabelFrame(tab, text='Plot Type')
    plot_type_frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
    plot_area_frame = ttk.Frame(tab)  # Use a Frame to hold the canvas
    plot_area_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')
    tab.grid_columnconfigure(0, weight=1)
    tab.grid_columnconfigure(1, weight=1)
    tab.grid_rowconfigure(1, weight=1)

    run_label = ttk.Label(selection_frame, text='Select Run:')
    run_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
    run_var = tk.StringVar(root)
    run_var.trace_add('write', lambda *args: update_files(tab, run_var, file_menu, file_var))
    run_options = list(all_data.keys())
    run_menu = ttk.Combobox(selection_frame, textvariable=run_var, values=run_options)
    run_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

    file_label = ttk.Label(selection_frame, text="Select File:")
    file_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
    file_var = tk.StringVar(tab)
    file_menu = ttk.Combobox(selection_frame, textvariable=file_var, values=[])
    file_menu.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

    plot_type_label = ttk.Label(plot_type_frame, text='Select Plot Type:')
    plot_type_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
    plot_type_var = tk.StringVar(value='line')
    line_radio = ttk.Radiobutton(plot_type_frame, text='Line plot', variable=plot_type_var, value='line')
    line_radio.grid(row=1, column=0, padx=5, pady=5, sticky='w')
    box_radio = ttk.Radiobutton(plot_type_frame, text='Box Plot', variable=plot_type_var, value='box')
    box_radio.grid(row=2, column=0, padx=5, pady=5, sticky='w')
    bar_radio = ttk.Radiobutton(plot_type_frame, text='Bar Plot', variable=plot_type_var, value='bar')
    bar_radio.grid(row=3, column=0, padx=5, pady=5, sticky='w')
    mean_radio = ttk.Radiobutton(plot_type_frame, text='Mean Plot', variable=plot_type_var, value='mean')
    mean_radio.grid(row=4, column=0, padx=5, pady=5, sticky='w')
    std_radio = ttk.Radiobutton(plot_type_frame, text='STD Plot', variable=plot_type_var, value='std')
    std_radio.grid(row=5, column=0, padx=5, pady=5, sticky='w')

    plot_button = ttk.Button(tab, text='Generate Plot',
                                     command=lambda: generate_plot(tab, run_var, file_var, plot_type_var, plot_area_frame))
    plot_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10)
    return tab

if __name__ == '__main__':
    root = tk.Tk()
    root.title('Single Variable Plotter')

    # Load data
    script_dir = os.path.dirname(__file__)
    Full_Dir = os.path.join(script_dir, 'Datasets')
    all_data = preload_data(Full_Dir)

    notebook = ttk.Notebook(root)
    single_variable_plot_tab = single_variable_plot(notebook)  # Pass the notebook
    notebook.pack(expand=True, fill=tk.BOTH)

    root.mainloop()
