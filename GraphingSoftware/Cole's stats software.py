import tkinter as tk
from tkinter import ttk
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pickle
from PIL import Image, ImageGrab
from tkinter import filedialog
import collections

def preload_data_1(Base_Path_Dir):
    preloaded_data = {}
    for run_folder in os.listdir(Base_Path_Dir):
        run_path = os.path.join(Base_Path_Dir, run_folder)
        if os.path.isdir(run_path):
            preloaded_data[run_folder] = {}
            for filename in os.listdir(run_path):
                if filename.endswith('.xlsx'):
                    file_path = os.path.join(run_path, filename)
                    preloaded_data[run_folder][filename] = {}
                    try:
                        excel_file = pd.ExcelFile(file_path)
                        sheet_data = {}
                        for sheet_name in excel_file.sheet_names:
                            df = pd.read_excel(file_path, sheet_name=sheet_name, header=1)
                            print(f'sheet: {sheet_name}, DataFrame:\n{df}')
                            df = excel_file.parse(sheet_name, header=1)
                            data = df.to_numpy()
                            print(f'sheet: {sheet_name}, Np Array:\n: {data}')
                            flattened_data = data.flatten()
                            sheet_data[sheet_name] = flattened_data
                        preloaded_data[run_folder][filename] = sheet_data
                    except Exception as e:
                        print(f'Error loading data from {file_path}: {e}')
    return preloaded_data

def preload_data(Base_Path_Dir, cache_file='preloaded_data.parquet'):
    if os.path.exists(cache_file):
        try:
            return pd.read_parquet(cache_file).to_dict()
        except Exception as e:
            print(f'Error loading from parquet cache: {e}, attempting to lead from pickle cache.')
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
                    print(f"Processing: {file_path}") #add print statement
                    preloaded_data[run_folder][filename] = {'sheet_data': {}, 'sheet_order': []}
                    try:
                        excel_file = pd.ExcelFile(file_path)
                        sheet_names = excel_file.sheet_names
                        preloaded_data[run_folder][filename]['sheet_order'] = sheet_names
                        for sheet_name in sheet_names:
                            try:
                                df = excel_file.parse(sheet_name, header=1)
                                data = df.to_numpy()
                                flattened_data = data.flatten()
                                preloaded_data[run_folder][filename]['sheet_data'][sheet_name] = flattened_data
                            except Exception as sheet_e:
                                print(f"Error processing sheet {sheet_name} in {file_path}: {sheet_e}")
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

def load_excel_file_data(run_folder, filename, file_path):
    """
    Helper function to load data from all sheets of a single Excel file,
    parsing only a specific range.
    This function will be executed by each worker process.

    Args:
        run_folder (str): The name of the run folder.
        filename (str): The name of the Excel file.
        file_path (str): The full path to the Excel file.

    Returns:
        tuple: A tuple containing (run_folder, filename, sheet_data_dict)
               or (run_folder, filename, None) if an error occurs.
    """
    sheet_data = {}
    try:
        # Use pd.ExcelFile context manager for proper file closing
        with pd.ExcelFile(file_path) as excel_file:
            for sheet_name in excel_file.sheet_names:
                # Read the sheet directly into a DataFrame,
                # specifying the range and header row relative to that range.
                # 'A2:YH550' is the desired range.
                # 'header=0' means the first row of the loaded range (A2) is the header.
                # To read 'A2:YH550', you need to skip 1 row (A1) and read 549 more rows (from A2 to A550 inclusive).
                # The total number of rows from A2 to A550 is 550 - 2 + 1 = 549.
                # However, your original nrows=551 would read more than A550 if skiprows=1 is used.
                # Let's assume you want to read A2 through YH550, meaning 549 rows starting from A2.
                # If 'header=0' is used with a 'range' parameter, it refers to the header within that range.
                # Since pd.read_excel doesn't have a direct 'range' argument like 'openpyxl.load_workbook',
                # you simulate it using skiprows and nrows.
                # 'skiprows=1' skips the first row (A1).
                # 'nrows=549' will read 549 rows starting from A2, effectively reading A2 to A550.
                df = pd.read_excel(excel_file, sheet_name=sheet_name,
                                   header=None, # No header row, we'll slice it if needed or assume data starts from A2
                                   skiprows=1,  # Skip A1
                                   nrows=549)   # Read 549 rows (A2 to A550)

                # If you need to treat A2 as the header, you'd then do:
                # df.columns = df.iloc[0]
                # df = df[1:].reset_index(drop=True)

                # To mimic the range A2:YH550, we first read starting from A2.
                # Then, to get columns up to YH (which is column 2333, assuming 0-indexed A=0, B=1, ... YH=2333),
                # you might need to slice columns if the file has more columns.
                # Assuming your files always have at least YH columns within the relevant data.
                # If 'YH' is truly a specific column, you'd need its index.
                # For simplicity, assuming you want all columns in the read DataFrame or
                # that the Excel files only contain data up to YH within the A2:YH550 range.
                # If you strictly need to slice columns, you'd do:
                # df = df.iloc[:, :target_column_index_for_YH + 1] # Assuming YH is the last column you want

                data = df.to_numpy()
                flattened_data = data.flatten()
                sheet_data[sheet_name] = flattened_data
        return run_folder, filename, sheet_data
    except Exception as e:
        print(f'Error loading data from {file_path}: {e}')
        return run_folder, filename, None # Indicate failure for this file

def preload_data_multiprocessing(Base_Path_Dir):
    """
    Preloads data from all Excel files within specified run folders
    using multiprocessing for improved efficiency.

    Args:
        Base_Path_Dir (str): The base directory containing run folders with Excel files.

    Returns:
        dict: A nested dictionary containing the preloaded flattened data.
              Structure: {run_folder: {filename: {sheet_name: flattened_numpy_array}}}
    """
    pkl_file_path = os.path.join(Base_Path_Dir, 'preloaded_data.pkl')

    # Check if the .pkl file exists
    if os.path.exists(pkl_file_path):
        print(f"Loading data from existing pickle file: {pkl_file_path}")
        try:
            with open(pkl_file_path, 'rb') as f:
                # Using collections.OrderedDict if you need explicit ordering for older Python versions
                # For Python 3.7+, a regular dict preserves insertion order.
                preloaded_data = pickle.load(f)
            print("Data loaded successfully from pickle file.")
            return preloaded_data
        except Exception as e:
            print(f"Error loading pickle file ({e}). Re-parsing data.")

    print("Pickle file not found or corrupted. Parsing Excel files...")
    preloaded_data_raw = {} # Use a temporary dictionary to build the data
    all_excel_files_info = []

    # First, collect all Excel files and their paths to prepare tasks for the pool
    # Sort run_folders and filenames to ensure consistent order
    run_folders = sorted([d for d in os.listdir(Base_Path_Dir) if os.path.isdir(os.path.join(Base_Path_Dir, d))])

    for run_folder in run_folders:
        run_path = os.path.join(Base_Path_Dir, run_folder)
        filenames = sorted([f for f in os.listdir(run_path) if f.endswith('.xlsx')])
        for filename in filenames:
            file_path = os.path.join(run_path, filename)
            all_excel_files_info.append((run_folder, filename, file_path))

    # Use ProcessPoolExecutor to parallelize the loading of each Excel file
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = [executor.submit(load_excel_file_data, rf, fn, fp)
                   for rf, fn, fp in all_excel_files_info]

        for future in as_completed(futures):
            run_folder, filename, sheet_data = future.result()
            if sheet_data is not None:
                if run_folder not in preloaded_data_raw:
                    preloaded_data_raw[run_folder] = {}
                preloaded_data_raw[run_folder][filename] = sheet_data
            else:
                print(f"Warning: Failed to load data for '{filename}' in '{run_folder}'. Skipping this file.")

    # Now, explicitly create the final ordered dictionary from the raw data
    # This step is crucial for guaranteed order if you're concerned about it,
    # especially for the top-level 'run_folder' keys.
    # For sub-dictionaries (filenames and sheet_names), they are populated
    # in the order they are processed within load_excel_file_data and the loop above.
    preloaded_data = {}
    for run_folder in sorted(preloaded_data_raw.keys()):
        preloaded_data[run_folder] = {}
        for filename in sorted(preloaded_data_raw[run_folder].keys()):
            preloaded_data[run_folder][filename] = preloaded_data_raw[run_folder][filename]


    # Save the preloaded data to a .pkl file
    try:
        with open(pkl_file_path, 'wb') as f:
            pickle.dump(preloaded_data, f)
        print(f"Data successfully saved to pickle file: {pkl_file_path}")
    except Exception as e:
        print(f"Error saving data to pickle file ({e}).")

    return preloaded_data

# Example Usage (assuming you have a 'data' directory with your Excel files)
# For demonstration, create dummy files if you don't have them
if __name__ == '__main__':
    script_dir = os.path.dirname(__file__)
    Full_Dir = os.path.join(script_dir, 'Datasets')

    print(f"\nStarting preloading from: {Full_Dir}")
    all_data = preload_data_multiprocessing(Full_Dir)

    print("\nPreloading complete. Structure of preloaded_data:")
    for run_folder, files in all_data.items():
        print(f"  {run_folder}/")
        for filename, sheets in files.items():
            print(f"    {filename}/")
            for sheet_name, data_array in sheets.items():
                print(f"      {sheet_name}: Data shape={data_array.shape}, first 5 elements={data_array[:5]}")
        
    if all_data is not None:
        #script_dir = os.path.dirname(__file__)
        #Full_Dir = os.path.join(script_dir, 'Datasets')
        #all_data = preload_data(Full_Dir)
        #print(all_data['Run1']['Reflectivity_OVER20dBZ_Level12.xlsx']['sheet_data'])

        def line_plot(data_to_plot, titlename, unittype, sheet_names, filter=None):
            max_data = []
            min_data = []
            x_positions = np.arange(len(sheet_names))
            plt.figure(figsize=(10,10))
            for sheet_name in sheet_names:
                flattened_data = data_to_plot[sheet_name]
                if filter is not None:
                    filtered_data = flattened_data[flattened_data>=filter]
                else:
                    filtered_data = flattened_data
                if filtered_data.size >0:
                    min_value = np.min(filtered_data)
                    max_value = np.max(filtered_data)
                    max_data.append(max_value)
                    min_data.append(min_value)
                else:
                    print(f'Warning: No data available for sheet: {sheet_name} after filtering')
            if min_data:
                plt.plot(x_positions, min_data, marker='o', linestyle='--', label='minimum')
                plt.plot(x_positions, max_data, marker='s', linestyle='-', label = 'maximum')
                plt.title(titlename)
                plt.ylabel(unittype)
                plt.xlabel('time')
                plt.xticks(x_positions, sheet_names, rotation=45, ha='right', fontsize = 6)
                plt.legend()
            else:
                return print('Warning: No data to plot.')

        def Box_Whisker_preloaded(data_to_plot, titlename, unittype, sheet_names):
            all_data_list = list(data_to_plot.values())
            max_min_data = []
            whisker_highs = []
            whisker_lows = []
            plt.figure(figsize=(10, 10))
            for flattened_data in all_data_list:
                min_data = np.min(flattened_data)
                max_data = np.max(flattened_data)
                max_min_data.append((min_data, max_data))
                
                Q1 = np.percentile(flattened_data, 25)
                Q2 = np.percentile(flattened_data, 75)
                IQR = Q2-Q1
                whisker_low = Q1-1.5*IQR
                whisker_high = Q2+1.5*IQR
                whisker_highs.append(whisker_high)
                whisker_lows.append(whisker_low)
            plt.boxplot(all_data_list, showfliers=False)
            for idx, (min_value, max_value) in enumerate(max_min_data):
                if min_value < min(whisker_lows):
                    min_value_plot = min(whisker_lows)
                    plt.scatter(idx+1, min_value_plot, color='red', zorder=5)
                    plt.text(idx+1, min_value_plot+(max(whisker_highs)/15), f'{min_value}', color = 'black', ha='center', va='top', fontsize=6, rotation = 45)
                else:
                    plt.scatter(idx+1, min_value, color='red', zorder=5)
                if max_value > (max(whisker_highs)+(max(whisker_highs)/4)):
                    max_value_plot = max(whisker_highs)+(max(whisker_highs)/4)
                    plt.scatter(idx+1, max_value_plot, color='green', zorder=5)
                    plt.text(idx+1, max_value_plot+(max_value_plot/14), f'{max_value}', color='black', ha='center', va='top', fontsize=6, rotation = 45)
                else:
                    plt.scatter(idx+1, max_value, color='green', zorder=5)
            plt.ylim([min(whisker_lows), max(whisker_highs)+(max(whisker_highs)/4)])
            plt.title(titlename, pad=25)
            plt.ylabel(unittype)
            plt.xlabel('Time')
            plt.xticks(range(1, len(sheet_names)+1), sheet_names, fontsize=6, rotation=45)

        def save_plot():
            """
            Saves the current plot to a file.
            """
            filename = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
            if filename:
                plt.savefig(filename)  # Save the plot
                print(f"Plot saved to {filename}")


        def single_variable_plot(notebook):
            
            tab = ttk.Frame(notebook)
            notebook.add(tab, text='Single Variable Plots')

            selection_frame = ttk.LabelFrame(tab, text='Data Selection')
            selection_frame.grid(row = 0, column=0, padx=10, pady=10, sticky='nsew')
            plot_type_frame = ttk.LabelFrame(tab, text='Plot Type')
            plot_type_frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
            plot_area_frame = ttk.LabelFrame(tab, text='Plot Display')
            plot_area_frame.grid(row=1, column = 0, columnspan=2, padx=10, pady=10, sticky='nsew')
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_columnconfigure(1, weight=1)
            tab.grid_rowconfigure(1, weight=1)

            run_label = ttk.Label(selection_frame, text='Select Run:')
            run_label.grid(row = 0, column=0, padx=5, pady=5, sticky='w')
            run_var = tk.StringVar(root)
            run_var.trace_add('write', lambda *args: update_files(tab, run_var, file_menu, file_var)) #update_files needs to be defined to update the plot area
            run_options = list(all_data.keys())
            run_menu = ttk.Combobox(selection_frame, textvariable=run_var, values=run_options)
            run_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

            file_label = ttk.Label(selection_frame, text="Select File:")
            file_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            file_var = tk.StringVar(tab)
            #file_var.trace_add('write', update_sheets)
            file_menu = ttk.Combobox(selection_frame, textvariable=file_var, values=[])
            file_menu.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

            title_label = ttk.Label(selection_frame, text='Title:') #label for title
            title_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
            title_text = ttk.Entry(selection_frame) #entry for title
            title_text.grid(row=2, column=1, padx=5, pady=5, sticky='w')
            
            units_label = ttk.Label(selection_frame, text='Units:') #label for title
            units_label.grid(row=3, column=0, padx=5, pady=5, sticky='w')
            units_text = ttk.Entry(selection_frame) #entry for title
            units_text.grid(row=3, column=1, padx=5, pady=5, sticky='w')

            #sheet_label = ttk.Label(selection_frame, text='Select Sheet:')
            #sheet_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
            #sheet_var = tk.StringVar(root)
            #sheet_menu = ttk.Combobox(selection_frame, textvariable=sheet_var, values=[])
            #sheet_menu.grid(row=2, column=1, padx=5, pady=5, sticky='ew')

            plot_type_label = ttk.Label(plot_type_frame, text='Select Plot Type:')
            plot_type_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            plot_type_var = tk.StringVar(value='line')
            line_radio = ttk.Radiobutton(plot_type_frame, text='Line plot', variable=plot_type_var, value='line')
            line_radio.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            box_radio = ttk.Radiobutton(plot_type_frame, text='Box Plot', variable=plot_type_var, value='box')
            box_radio.grid(row=2, column=0, padx=5, pady=5, sticky='w')

            plot_button = ttk.Button(tab, text='Generate Plot',
                                    command= lambda: generate_plot(tab, run_var, file_var, title_text, units_text, plot_type_var, plot_area_frame))
            plot_button.grid(row=2, column=2, columnspan=2, padx=10, pady=10, sticky='e')
            save_button = ttk.Button(tab, text='Save Plot', command = lambda: save_plot())
            save_button.grid(row = 2, column = 0, columnspan=2, padx=10, pady=10, sticky='w')

        def double_variable_plot(notebook):
            
            tab = ttk.Frame(notebook)
            notebook.add(tab, text='Two Variable Plots')

            run_frame = ttk.LabelFrame(tab, text='Run')
            run_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')

            file_frame = ttk.LabelFrame(tab, text='Files')
            file_frame.grid(row=1, column=0, padx=10, pady=10, sticky='nsew')

            plot_type_frame = ttk.LabelFrame(tab, text='Plot Types')
            plot_type_frame.grid(row=1, column=1, padx=10, pady=10, sticky='nsew')
            
            plot_area_frame = ttk.LabelFrame(tab, text='Plot Display')
            plot_area_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')
            
            run_label = ttk.Label(run_frame, text='Select Run:')
            run_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            run_var = tk.StringVar(tab)
            run_options = list(all_data.keys())
            run_var.trace_add('write', lambda *args: update_variables_two_vars(tab, run_var, var1_menu, var1_file_var, var2_menu, var2_file_var))
            run_menu = ttk.Combobox(run_frame, textvariable=run_var, values=run_options)
            run_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

            var1_label = ttk.Label(file_frame, text='Select File 1:')
            var1_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            var1_file_var = tk.StringVar(tab)
            var1_menu = ttk.Combobox(file_frame, textvariable=var1_file_var, values=[])
            var1_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

            var2_label = ttk.Label(file_frame, text='Select File 2:')
            var2_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            var2_file_var = tk.StringVar(tab)
            var2_menu = ttk.Combobox(file_frame, textvariable=var2_file_var, values=[])
            var2_menu.grid(row=1, column=1, padx=5, pady=5, sticky='w')

            title_label = ttk.Label(file_frame, text='Title:') #label for title
            title_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
            title_text = ttk.Entry(file_frame) #entry for title
            title_text.grid(row=2, column=1, padx=5, pady=5, sticky='w')
            
            units_label = ttk.Label(file_frame, text='Units:') #label for title
            units_label.grid(row=3, column=0, padx=5, pady=5, sticky='w')
            units_text = ttk.Entry(file_frame) #entry for title
            units_text.grid(row=3, column=1, padx=5, pady=5, sticky='w')

            var1_plot_type_label = ttk.Label(plot_type_frame, text='Plot Type File 1')
            var1_plot_type_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            var1_plot_type_var = tk.StringVar(value='line')
            var1_line_radio = ttk.Radiobutton(plot_type_frame, text='Line Plot', variable=var1_plot_type_var, value='line')
            var1_line_radio.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            var1_box_radio = ttk.Radiobutton(plot_type_frame, text='Box and Whisker', variable= var1_plot_type_var, value = 'box')
            var1_box_radio.grid(row=2, column=0, padx=5, pady=5, sticky='w')

            var2_plot_type_label = ttk.Label(plot_type_frame, text='Plot Type File 2')
            var2_plot_type_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')
            var2_plot_type_var = tk.StringVar(value='line')
            var2_line_radio = ttk.Radiobutton(plot_type_frame, text='Line Plot', variable=var2_plot_type_var, value='line')
            var2_line_radio.grid(row=1, column=1, padx=5, pady=5, sticky='w')
            var2_box_radio = ttk.Radiobutton(plot_type_frame, text='Box and Whisker', variable=var2_plot_type_var, value='box')
            var2_box_radio.grid(row=2, column=1, padx=5, pady=5, sticky='w')

            plot_button = ttk.Button(tab, text='Generate Plot',
                                    command= lambda: generate_plot_two_vars(tab, run_var, var1_file_var, var2_file_var, var1_plot_type_var, var2_plot_type_var, 
                                                                            title_text, units_text, plot_area_frame))
            plot_button.grid(row=3, column=2, columnspan=2, padx=10, pady=10, sticky='e')
            save_button = ttk.Button(tab, text='Save Plot', command = lambda: save_plot())
            save_button.grid(row = 3, column = 0, columnspan=2, padx=10, pady=10, sticky='w')

        def triple_variable_plot(notebook):
            tab = ttk.Frame(notebook)
            notebook.add(tab, text='Triple Variable Plots')

            run_frame = ttk.LabelFrame(tab, text='Run Selection')
            run_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')

            file_frame = ttk.LabelFrame(tab, text='File Selection')
            file_frame.grid(row=1, column=0, columnspan=1, padx=10, pady=10, sticky='nsew')

            plot_type_frame = ttk.LabelFrame(tab, text='Plot Type Selection')
            plot_type_frame.grid(row=1, column=1, columnspan=1, padx=10, pady=10, sticky='nsew')

            plot_area_frame = ttk.LabelFrame(tab, text='Plot Display')
            plot_area_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')

            run_label = ttk.Label(run_frame, text='Select Run:')
            run_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            run_var = tk.StringVar(tab)
            run_options = list(all_data.keys())
            #run_var.trace_add('write', lambda *args: update_variables_three_vars(tab, run_var, var1_menu, var1_file_var, var2_menu, var2_file_var, var3_menu, var3_file_var))
            run_menu = ttk.Combobox(run_frame, textvariable=run_var, values=run_options)
            run_menu.grid(row=1, column=0, padx=5, pady=5, sticky='ew')
            
            var1_label = ttk.Label(file_frame, text='Select File 1:')
            var1_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            var1_file_var = tk.StringVar(tab)
            var1_menu = ttk.Combobox(file_frame, textvariable=var1_file_var, values=[])
            var1_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

            var2_label = ttk.Label(file_frame, text='Select File 2:')
            var2_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            var2_file_var = tk.StringVar(tab)
            var2_menu = ttk.Combobox(file_frame, textvariable=var2_file_var, values=[])
            var2_menu.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

            var3_label = ttk.Label(file_frame,text='Select File 3:')
            var3_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
            var3_file_var = tk.StringVar(tab)
            var3_menu = ttk.Combobox(file_frame, textvariable=var3_file_var, values=[])
            var3_menu.grid(row=2, column=1, padx=5, pady=5, sticky='ew')

            var1_plot_type_label = ttk.Label(plot_type_frame, text='Plot Type File 1:')
            var1_plot_type_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            var1_plot_type_var = tk.StringVar(value='line')
            var1_line_radio = tk.Radiobutton(plot_type_frame, text='Line Plot', variable=var1_plot_type_var, value='line')
            var1_line_radio.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            var1_box_radio = tk.Radiobutton(plot_type_frame, text='Box and Whisker', variable= var1_plot_type_var, value = 'box')
            var1_box_radio.grid(row=2, column=0, padx=5, pady=5, sticky='w')

            var2_plot_type_label = ttk.Label(plot_type_frame, text='Plot Type File 2:')
            var2_plot_type_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')
            var2_plot_type_var = tk.StringVar(value='line')
            var2_line_radio = tk.Radiobutton(plot_type_frame, text='Line Plot', variable=var2_plot_type_var, value='line')
            var2_line_radio.grid(row=1, column=1, padx=5, pady=5, sticky='w')
            var2_box_radio = tk.Radiobutton(plot_type_frame, text='Box and Whisker', variable=var2_plot_type_var, value='box')
            var2_box_radio.grid(row=2, column=1, padx=5, pady=5, sticky='w')

            var3_plot_type_label = ttk.Label(plot_type_frame, text='Plot Type File 3:')
            var3_plot_type_label.grid(row=0, column=2, padx=5, pady=5, sticky='w')
            var3_plot_type_var = tk.StringVar(value='line')
            var3_line_radio = tk.Radiobutton(plot_type_frame, text='Line Plot', variable=var3_plot_type_var, value='line')
            var3_line_radio.grid(row=1, column=2, padx=5, pady=5, sticky='w')
            var3_box_radio = tk.Radiobutton(plot_type_frame, text='Box and Whisker', variable=var3_plot_type_var, value='box')
            var3_box_radio.grid(row=2, column=2, padx=5, pady=5, sticky='w')
            
        def update_variables_three_vars(parent, run_var, var1_menu, var1_file_var,
                                        var2_menu, var2_file_var,
                                        var3_menu, var3_file_var):
            selected_run = run_var.get()
            var1_menu['values'] = []
            var1_file_var.set('')
            var2_menu['values'] = []

        def update_variables_two_vars(parent, run_var, var1_menu, var1_file_var, var2_menu, var2_file_var):
            selected_run = run_var.get()
            var1_menu['values'] = []
            var1_file_var.set('')
            var2_menu['values'] = []
            var2_file_var.set('')
            if selected_run and selected_run in all_data:
                files = sorted(all_data[selected_run].keys())
                var1_menu['values'] = files
                var2_menu['values'] = files
                if files:
                    var1_file_var.set(files[0])
                    var2_file_var.set(files[0])


        def update_files(parent, run_var, file_menu, file_var):
            selected_run = run_var.get()
            file_menu['values'] = []
            file_var.set('')
            #sheet_menu['values'] = []
            #sheet_var.set('')

            if selected_run and selected_run in all_data:
                files = sorted(all_data[selected_run].keys())
                file_menu['values'] = files
                if files:
                    file_var.set(files[0])
                    #update_sheets()

        def update_sheets(parent, run_var, file_var):
            selected_run = run_var.get()
            selected_file = file_var.get()
            #sheet_menu['values'] = []
            #sheet_var.set('')
            if selected_run and selected_file and selected_run in all_data and selected_file in all_data[selected_file]:
                sheets = sorted(all_data[selected_run][selected_file].keys())
                #sheet_menu['values'] = sheets
                #if sheets:
                    #sheet_var.set(sheets[0])

        def generate_plot_two_vars(parent, run_var, var1_file_var, var2_file_var, var1_plot_type_var, var2_plot_type_var, title_var, unit_var, plot_area_frame):
            selected_run = run_var.get()
            selected_file_1 = var1_file_var.get()
            selected_file_2 = var2_file_var.get()
            selected_title = title_var.get()
            selected_units = unit_var.get()
            plot_type_1 = var1_plot_type_var.get()
            plot_type_2 = var2_plot_type_var.get()
            if selected_run and selected_file_1 and selected_file_2 and selected_run in all_data and selected_file_1 in all_data[selected_run] and selected_file_2 in all_data[selected_run]:
                data_to_plot_1 = all_data[selected_run][selected_file_1]
                data_to_plot_2 = all_data[selected_run][selected_file_2]
                sheet_names_1 = list(data_to_plot_1.keys())
                sheet_names_2 = list(data_to_plot_2.keys())
                for widget in plot_area_frame.winfo_children():
                    widget.destroy()
                plt.close('all')
                plt.clf()
                if plot_type_1 == 'line':
                    line_plot(data_to_plot_1, f'{selected_title}', f'{selected_units}', sheet_names_1)
                elif plot_type_1 =='box':
                    Box_Whisker_preloaded(data_to_plot_1, f'{selected_title}', f'{selected_units}', sheet_names_1)
                if plot_type_2 == 'line':
                    line_plot(data_to_plot_2, f'{selected_title}', f'{selected_units}', sheet_names_2)
                elif plot_type_2 == 'box':
                    Box_Whisker_preloaded(data_to_plot_2, f'{selected_title}', f'{selected_units}', sheet_names_2)
                canvas = FigureCanvasTkAgg(plt.gcf(), master=plot_area_frame)
                canvas_widget = canvas.get_tk_widget()
                canvas_widget.pack()
                canvas.draw()
            else:
                print('Error: Invalid selection')

        def generate_plot(parent, run_var, file_var, title_var, unit_var, plot_type_var, plot_area_frame):
            selected_run = run_var.get()
            selected_file = file_var.get()
            selected_title = title_var.get()
            selected_units = unit_var.get()
            plot_type = plot_type_var.get()
            for widget in plot_area_frame.winfo_children():
                widget.destroy() #destroy previous widgets
            plt.close('all')
            plt.clf()
            if selected_run and selected_file and selected_run in all_data and selected_file in all_data[selected_run]:
                data_to_plot = all_data[selected_run][selected_file]
                sheet_names = list(data_to_plot.keys())
                if plot_type == 'line':
                    line_plot(data_to_plot, f'{selected_title}', f'{selected_units}', sheet_names)
                elif plot_type == 'box':
                    Box_Whisker_preloaded(data_to_plot, f'{selected_title}', f'{selected_units}', sheet_names)
                
                canvas = FigureCanvasTkAgg(plt.gcf(), master=plot_area_frame) #create canvas
                canvas_widget = canvas.get_tk_widget() #get canvas widget
                canvas_widget.pack() #pack canvas widget
                canvas.draw() #draw canvas
            else:
                print('Error: Invalid Selection')

        root = tk.Tk()
        root.title('Data Visulization')

        notebook = ttk.Notebook(root)
        notebook.pack(fill='both', expand=True)

        single_variable_plot(notebook)
        double_variable_plot(notebook)
        triple_variable_plot(notebook)

        root.mainloop()
