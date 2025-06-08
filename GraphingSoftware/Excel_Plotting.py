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
from scipy.stats import pearsonr
import collections


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

        def line_plot(data_to_plot : np.array, titlename : str, unittype : str, sheet_names : list, limit : list = None, filter=None, color_type : str = None, ax = None):
            max_data = []
            min_data = []
            x_positions = np.arange(1, len(sheet_names)+1)

            current_ax = ax if ax is not None else plt.gca()
            
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
            if limit and all(limit):
                try:
                    limit = [int(i) for i in limit]
                    current_ax.set_ylim(min(limit), max(limit))
                except Exception as e:
                    print(f'Encountered an error while trying to convert the list to integers: {e} \n continuing with premade plotting logic.')
            else:
                print("List is either empty or missing entries, continuing with premade plotting logic.")
            if min_data:
                current_ax.plot(x_positions, min_data, marker='o', linestyle='--', label='minimum', color = color_type if color_type is not None else None)
                current_ax.plot(x_positions, max_data, marker='s', linestyle='-', label = 'maximum', color = color_type if color_type is not None else None)
                current_ax.set_title(titlename, pad=35)
                current_ax.set_ylabel(unittype)
                current_ax.set_xlabel('time')
                current_ax.set_xticks(x_positions, sheet_names, rotation=45, ha='right', fontsize = 6)
                #plt.legend()
                plt.subplots_adjust(bottom=0.15)
            else:
                return print('Warning: No data to plot.')

        def Box_Whisker_preloaded(data_to_plot : np.array, titlename : str, unittype : str, sheet_names : list, limit : list = None, ax = None):
            all_data_list = list(data_to_plot.values())
            max_min_data = []
            whisker_highs = []
            whisker_lows = []
            current_ax = ax if ax is not None else plt.gca()
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
            if limit and all(limit):
                try:
                    limit = [int(i) for i in limit]
                    current_ax.set_ylim(min(limit), max(limit))
                    min_y_value = min(limit)
                    max_y_value = max(limit)
                except Exception as e:
                    print(f"Encoutered an error while trying to convert the list to integers: {e} \n continuing with premade plotting logic.")
                    current_ax.set_ylim([min(whisker_lows), max(whisker_highs)+(max(whisker_highs)/4)])
                    min_y_value = min(whisker_lows)
                    max_y_value = max(whisker_highs)+(max(whisker_highs)/4)
            else:
                print("List is either empty or missing entries, continuing with premade plotting logic.")
                current_ax.set_ylim([min(whisker_lows), max(whisker_highs)+(max(whisker_highs)/4)])
                min_y_value = min(whisker_lows)
                max_y_value = max(whisker_highs)+(max(whisker_highs)/4)
            for idx, (min_value, max_value) in enumerate(max_min_data):
                if min_value < min_y_value:
                    min_value_plot = min_y_value
                    current_ax.scatter(idx+1, min_value_plot, color='red', zorder=5)
                    current_ax.text(idx+1, min_value_plot+(max_y_value/16), f'{str(min_value):.4}', color = 'black', ha='center', va='top', fontsize=8, rotation = 45)
                else:
                    current_ax.scatter(idx+1, min_value, color='red', zorder=5)
                if max_value > max_y_value:
                    max_value_plot = max_y_value
                    current_ax.scatter(idx+1, max_value_plot, color='green', zorder=5)
                    current_ax.text(idx+1, max_value_plot+(max_value_plot/16), f'{str(max_value):.4}', color='black', ha='center', va='top', fontsize=8, rotation = 45)
                else:
                    current_ax.scatter(idx+1, max_value, color='green', zorder=5)
            current_ax.set_title(titlename, pad=35)
            current_ax.set_ylabel(unittype)
            current_ax.set_xlabel('Time')
            plt.subplots_adjust(bottom=0.15)
            current_ax.set_xticks(range(1, len(sheet_names)+1), sheet_names, fontsize=6, rotation=45)
        
        def pearsoncc(data_var1 : np.array, data_var2: np.array, sheet_names_var1 : list, sheet_names_var2):

            maxs_var1_list = []
            maxs_var2_list = []
            try:
                for sheet_names in sheet_names_var1:
                    filtered_data = data_var1[sheet_names]
                    if filtered_data.size >0:
                        max_value = max(filtered_data)
                        print(f"Variable One: \n max value: {max_value} \n for {sheet_name}")
                        maxs_var1_list.append(max_value)
                    else:
                        print(f"data for {data_var1}, in {sheet_names} doesn't have a size value")
            except Exception as e:
                print(f"Error gathering sheets for {data_var1}: {e}")
                return None
            except FileNotFoundError as e:
                print(f"Didn't find a file that matched {sheet_names_var1}: {e}")
                return None
            except SyntaxError as e:
                print(f"Error filtering data: {e}")
                return None
            print(f"max values for first variable: {maxs_var1_list}")
            try:
                for sheet_names in sheet_names_var2:
                    filtered_data = data_var2[sheet_names]
                    if filtered_data.size >0:
                        max_value = max(filtered_data)
                        print(f"Variable Two: \n max value: {max_value} \n for {sheet_name}")
                        maxs_var2_list.append(max_value)
                    else:
                        print(f"data for {data_var2}, in {sheet_names} doesn't have a size value")
            except Exception as e:
                print(f"Error gathering sheets for {data_var2}: {e}")
                return None
            except FileNotFoundError as e:
                print(f"Didn't find a file that matched {sheet_names_var2}: {e}")
                return None
            except SyntaxError as e:
                print(f"Error filtering data: {e}")
                return None
            print(f"max values for first variable: {maxs_var2_list}")
            if len(maxs_var1_list) == len(maxs_var2_list):
                r_value, p_value = pearsonr(maxs_var1_list, maxs_var2_list)
                return r_value, p_value
            else:
                len1 = len(maxs_var1_list)
                len2 = len(maxs_var2_list)

                if len1 < len2:
                    # maxs_var1_list is smaller, pad it with zeros
                    # Calculate how many zeros are needed
                    diff = len2 - len1
                    # Extend the list with zeros
                    maxs_var1_list.extend([0] * diff)
                    print(f"Padded {data_var1} with {diff} zeros.")
                elif len2 < len1:
                    # maxs_var2_list is smaller, pad it with zeros
                    # Calculate how many zeros are needed
                    diff = len1 - len2
                    # Extend the list with zeros
                    maxs_var2_list.extend([0] * diff)
                    print(f"Padded {data_var2} with {diff} zeros.")

                # Now that the lengths are equal, you can proceed with pearsonr
                r_value, p_value = pearsonr(maxs_var1_list, maxs_var2_list)
                return r_value, p_value

        def percent_error(control_data : np.array, test_data : np.array, control_sheets : list, test_sheets: list, type, limit = None):
            control_avg_list = []
            test_avg_list = []
            control_max_list = []
            test_max_list = []
            try:
                for sheet_names in control_sheets:
                    filtered_data = control_data[sheet_names]
                    if limit:
                        filtered_data = filtered_data[filtered_data>=limit]
                    if filtered_data.size >0:
                        if type == 'average':
                            average_value = np.mean(filtered_data)
                            control_avg_list.append(average_value)
                        elif type == 'max':
                            max_value = max(filtered_data)
                            control_max_list.append(max_value)
                    else:
                        print(f"data for {control_data}, in {sheet_names} doesn't have a size value")
            except Exception as e:
                print(f"Error gathering sheets for {control_data}: {e}")
                return None
            except FileNotFoundError as e:
                print(f"Didn't find a file that matched {control_sheets}: {e}")
                return None
            except SyntaxError as e:
                print(f"Error filtering data: {e}")
                return None

            try:
                for sheet_names in test_sheets:
                    filtered_data = test_data[sheet_names]
                    if limit:
                        filtered_data = filtered_data[filtered_data>=limit]
                    if filtered_data.size >0:
                        if type == 'average':
                            average_value = np.mean(filtered_data)
                            test_avg_list.append(average_value)
                        elif type == 'max':
                            max_value = max(filtered_data)
                            test_max_list.append(max_value)
                    else:
                        print(f"data for {test_data}, in {sheet_names} doesn't have a size value")
            except Exception as e:
                print(f"Error gathering sheets for {test_data}: {e}")
                return None
            except FileNotFoundError as e:
                print(f"Didn't find a file that matched {test_sheets}: {e}")
                return None
            except SyntaxError as e:
                print(f"Error filtering data: {e}")
                return None
            
            total_percent_error = []

            try:
                if len(control_sheets) == len(test_sheets):
                    if type == 'average':
                        for i in range(len(control_avg_list)):
                            percent_error_value = ((test_avg_list[i]-control_avg_list[i])/control_avg_list[i])*100
                            total_percent_error.append(percent_error_value)
                        average_percent_error = np.mean(total_percent_error)
                        return average_percent_error
                    if type == 'max':
                        for i in range(len(control_max_list)):
                            percent_error_value = ((test_max_list[i]-control_max_list[i])/control_max_list[i])*100
                            total_percent_error.append(percent_error_value)
                        average_percent_error = np.mean(total_percent_error)
                        return average_percent_error
                else:
                    print(f"cannot calculate data as the lists are not matching: \n Control has ammount: {len(control_sheets)} \n Test has ammount: {len(test_sheets)}")
                    return None
            except Exception as e:
                print(f"Error trying to calculate percent error: {e}")



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
            title_label.grid(row=0, column=2, padx=5, pady=5, sticky='w')
            title_text = ttk.Entry(selection_frame) #entry for title
            title_text.grid(row=0, column=3, padx=5, pady=5, sticky='w')
            
            units_label = ttk.Label(selection_frame, text='Units:') #label for title
            units_label.grid(row=1, column=2, padx=5, pady=5, sticky='w')
            units_text = ttk.Entry(selection_frame) #entry for title
            units_text.grid(row=1, column=3, padx=5, pady=5, sticky='w')

            max_label = ttk.Label(selection_frame, text='Maximum Limit:')
            max_label.grid(row=2, column=2, padx=5, pady=5, sticky='w')
            max_text = ttk.Entry(selection_frame)
            max_text.grid(row=2, column=3, padx=5, pady=5, sticky='w')

            min_label = ttk.Label(selection_frame, text='Minimum Limit:')
            min_label.grid(row=3, column=2, padx=5, pady=5, sticky='w')
            min_text = ttk.Entry(selection_frame)
            min_text.grid(row=3, column=3, padx=5, pady=5, sticky='w')

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
                                    command= lambda: generate_plot(tab, run_var, file_var, title_text, units_text, plot_type_var, plot_area_frame,
                                                                   min_text, max_text))
            plot_button.grid(row=2, column=2, columnspan=2, padx=10, pady=10, sticky='e')
            save_button = ttk.Button(tab, text='Save Plot', command = lambda: save_plot())
            save_button.grid(row = 2, column = 0, columnspan=2, padx=10, pady=10, sticky='w')

        def double_variable_plot(notebook):
            
            def update_selections(parent, frame_one, frame_two, selection, variable):
                for widget in frame_one.winfo_children():
                    widget.destroy() #destroy previous widgets
                for widget in frame_two.winfo_children():
                    widget.destroy() #destroy previous widgets
                parent.run_menus = []
                parent.file_menus = []
                parent.title_menus = []
                parent.unit_menus = []
                parent.minimum_menus = []
                parent.maximum_menus = []

                selection = selection.get()
                variable = variable.get()

                if selection == 'single':
                    run_label = ttk.Label(frame_one, text='Select Run:')
                    run_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
                    run_var = tk.StringVar(tab)
                    run_options = list(all_data.keys())
                    run_var.trace_add('write', lambda *args: update_variables_two_vars(tab, run_var, var1_menu, var1_file_var, var2_menu, var2_file_var))
                    run_menu = ttk.Combobox(frame_one, textvariable=run_var, values=run_options)
                    run_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

                    var1_label = ttk.Label(frame_one, text='Select File 1:')
                    var1_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
                    var1_file_var = tk.StringVar(tab)
                    var1_menu = ttk.Combobox(frame_one, textvariable=var1_file_var, values=[])
                    var1_menu.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

                    var2_label = ttk.Label(frame_one, text='Select File 2:')
                    var2_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
                    var2_file_var = tk.StringVar(tab)
                    var2_menu = ttk.Combobox(frame_one, textvariable=var2_file_var, values=[])
                    var2_menu.grid(row=2, column=1, padx=5, pady=5, sticky='w')

                    parent.run_menus.append(run_var)
                    parent.run_menus.append(run_var)
                    parent.file_menus.append(var1_file_var)
                    parent.file_menus.append(var2_file_var)

                elif selection == 'multiple':
                    run_label_1 = ttk.Label(frame_one, text='Select First Run:')
                    run_label_1.grid(row=0, column=0, padx=5, pady=5, sticky='w')
                    run_label_2 = ttk.Label(frame_one, text='Select Second Run:')
                    run_label_2.grid(row=0, column=1, padx=5, pady=5, sticky='w')
                    run_var_1 = tk.StringVar(parent)
                    run_options_1 = list(all_data.keys())
                    run_options_2 = list(all_data.keys())
                    run_var_2 = tk.StringVar(parent)
                    run_var_1.trace_add('write', lambda *args: update_files(parent, run_var_1, var1_menu, var1_file_var))
                    run_var_2.trace_add('write', lambda *args: update_files(parent, run_var_2, var2_menu, var2_file_var))
                    run_menu_1 = ttk.Combobox(frame_one, textvariable=run_var_1, values=run_options_1)
                    run_menu_1.grid(row=1, column=0, padx=5, pady=5, sticky='w')
                    run_menu_2 = ttk.Combobox(frame_one, textvariable=run_var_2, values=run_options_2)
                    run_menu_2.grid(row=1, column=1, padx=5, pady=5, sticky='w')

                    var1_label = ttk.Label(frame_one, text='Select File 1:')
                    var1_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
                    var1_file_var = tk.StringVar(tab)
                    var1_menu = ttk.Combobox(frame_one, textvariable=var1_file_var, values=[])
                    var1_menu.grid(row=3, column=0, padx=5, pady=5, sticky='ew')

                    var2_label = ttk.Label(frame_one, text='Select File 2:')
                    var2_label.grid(row=2, column=1, padx=5, pady=5, sticky='w')
                    var2_file_var = tk.StringVar(tab)
                    var2_menu = ttk.Combobox(frame_one, textvariable=var2_file_var, values=[])
                    var2_menu.grid(row=3, column=1, padx=5, pady=5, sticky='w')
                    
                    parent.run_menus.append(run_var_1)
                    parent.run_menus.append(run_var_2)
                    parent.file_menus.append(var1_file_var)
                    parent.file_menus.append(var2_file_var)
                
                title_label = ttk.Label(frame_two, text='Title:') #label for title
                title_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
                title_text = ttk.Entry(frame_two) #entry for title
                title_text.grid(row=1, column=0, padx=5, pady=5, sticky='w')
                if variable == 'Unscaled':
                    parent.axis = False

                    units_label = ttk.Label(frame_two, text='Units:') #label for title
                    units_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')
                    units_text = ttk.Entry(frame_two) #entry for title
                    units_text.grid(row=1, column=1, padx=5, pady=5, sticky='w')

                    max_label = ttk.Label(frame_two, text='Maximum Limit:')
                    max_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
                    max_text = ttk.Entry(frame_two)
                    max_text.grid(row=3, column=0, padx=5, pady=5, sticky='w')

                    min_label = ttk.Label(frame_two, text='Minimum Limit:')
                    min_label.grid(row=2, column=1, padx=5, pady=5, sticky='w')
                    min_text = ttk.Entry(frame_two)
                    min_text.grid(row=3, column=1, padx=5, pady=5, sticky='w')
                    parent.unit_menus.append(units_text)
                    parent.minimum_menus.append(min_text)
                    parent.maximum_menus.append(max_text)
                
                elif variable == 'Scaled':
                    parent.axis = True

                    units_label_1 = ttk.Label(frame_two, text='First Unit:') #label for title
                    units_label_1.grid(row=0, column=1, padx=5, pady=5, sticky='w')
                    units_text_1 = ttk.Entry(frame_two) #entry for title
                    units_text_1.grid(row=1, column=1, padx=5, pady=5, sticky='w')

                    units_label_2 = ttk.Label(frame_two, text='Second Unit:')
                    units_label_2.grid(row=0, column=2, padx=5, pady=5, sticky='w')
                    units_text_2 = ttk.Entry(frame_two)
                    units_text_2.grid(row=1, column=2, padx=5, pady=5, sticky='w')

                    max_label_1 = ttk.Label(frame_two, text='First Maximum Limit:')
                    max_label_1.grid(row=2, column=0, padx=5, pady=5, sticky='w')
                    max_text_1 = ttk.Entry(frame_two)
                    max_text_1.grid(row=3, column=0, padx=5, pady=5, sticky='w')

                    max_label_2 = ttk.Label(frame_two, text='Second Maximum Limit:')
                    max_label_2.grid(row=2, column=2, padx=5, pady=5, sticky='w')
                    max_text_2 = ttk.Entry(frame_two)
                    max_text_2.grid(row=3, column=2, padx=5, pady=5, sticky='w')

                    min_label_1 = ttk.Label(frame_two, text='First Minimum Limit:')
                    min_label_1.grid(row=2, column=1, padx=5, pady=5, sticky='w')
                    min_text_1 = ttk.Entry(frame_two)
                    min_text_1.grid(row=3, column=1, padx=5, pady=5, sticky='w')

                    min_label_2 = ttk.Label(frame_two, text='Second Minimum Limit:')
                    min_label_2.grid(row=2, column=3, padx=5, pady=5, sticky='w')
                    min_text_2 = ttk.Entry(frame_two)
                    min_text_2.grid(row=3, column=3, padx=5, pady=5, sticky='w')
                    
                    parent.unit_menus.append(units_text_1)
                    parent.unit_menus.append(units_text_2)
                    parent.minimum_menus.append(min_text_1)
                    parent.minimum_menus.append(min_text_2)
                    parent.maximum_menus.append(max_text_1)
                    parent.maximum_menus.append(max_text_2)

                parent.title_menus.append(title_text)



            tab = ttk.Frame(notebook)
            notebook.add(tab, text='Two Variable Plots')

            #run_frame = ttk.LabelFrame(tab, text='Run')
            #run_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')

            selection_frame = ttk.LabelFrame(tab, text='Selection type')
            selection_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
            
            file_frame = ttk.LabelFrame(tab, text='Files')
            file_frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')

            plot_type_frame = ttk.LabelFrame(tab, text='Plot Types')
            plot_type_frame.grid(row=0, column=2, padx=10, pady=10, sticky='nsew')

            plot_customization_frame = ttk.LabelFrame(tab, text='Plot Customization')
            plot_customization_frame.grid(row=1, column=2, padx=10, pady=10, sticky='nsew')
            
            plot_area_frame = ttk.LabelFrame(tab, text='Plot Display')
            plot_area_frame.grid(row=1, column = 0, columnspan=2, padx=10, pady=10, sticky='nsew')
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_columnconfigure(1, weight=1)
            tab.grid_rowconfigure(1, weight=1)
            
            run_type_label = ttk.Label(selection_frame, text='Select Run Type:')
            run_type_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            run_type_var = tk.StringVar(value='single')
            run_type = ttk.Combobox(selection_frame, text='Single Run', textvariable=run_type_var, value=['single', 'multiple'])
            run_type.grid(row=1, column=0, padx=5, pady=5, sticky='w')

            variable_type_label = ttk.Label(selection_frame, text='Select Variable Type')
            variable_type_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')
            variable_type_var = tk.StringVar(value='Unscaled')
            variable_type_options = ['Unscaled', 'Scaled']
            variable_type_menu = ttk.Combobox(selection_frame, text='Unscaled', textvariable=variable_type_var, value=variable_type_options)
            variable_type_menu.grid(row=1, column=1, padx=5, pady=5, sticky='w')
            
            run_type_var.trace_add('write', lambda *args: update_selections(tab, file_frame, plot_customization_frame, run_type_var, variable_type_var))
            variable_type_var.trace_add('write', lambda *args: update_selections(tab, file_frame, plot_customization_frame, run_type_var, variable_type_var))
            tab.axis = False
            tab.run_menus = []
            tab.file_menus = []
            tab.title_menus = []
            tab.unit_menus = []
            tab.minimum_menus = []
            tab.maximum_menus = []

            run_label = ttk.Label(file_frame, text='Select Run:')
            run_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            run_var = tk.StringVar(tab)
            run_options = list(all_data.keys())
            run_var.trace_add('write', lambda *args: update_variables_two_vars(tab, run_var, var1_menu, var1_file_var, var2_menu, var2_file_var))
            run_menu = ttk.Combobox(file_frame, textvariable=run_var, values=run_options)
            run_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
            tab.run_menus.append(run_var)
            tab.run_menus.append(run_var)

            var1_label = ttk.Label(file_frame, text='Select File 1:')
            var1_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            var1_file_var = tk.StringVar(tab)
            var1_menu = ttk.Combobox(file_frame, textvariable=var1_file_var, values=[])
            var1_menu.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
            tab.file_menus.append(var1_file_var)

            var2_label = ttk.Label(file_frame, text='Select File 2:')
            var2_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
            var2_file_var = tk.StringVar(tab)
            var2_menu = ttk.Combobox(file_frame, textvariable=var2_file_var, values=[])
            var2_menu.grid(row=2, column=1, padx=5, pady=5, sticky='w')
            tab.file_menus.append(var2_file_var)

            title_label = ttk.Label(plot_customization_frame, text='Title:') #label for title
            title_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            title_text = ttk.Entry(plot_customization_frame) #entry for title
            title_text.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            tab.title_menus.append(title_text)
            
            units_label = ttk.Label(plot_customization_frame, text='Units:') #label for title
            units_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')
            units_text = ttk.Entry(plot_customization_frame) #entry for title
            units_text.grid(row=1, column=1, padx=5, pady=5, sticky='w')
            tab.unit_menus.append(units_text)

            max_label = ttk.Label(plot_customization_frame, text='Maximum Limit:')
            max_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
            max_text = ttk.Entry(plot_customization_frame)
            max_text.grid(row=3, column=0, padx=5, pady=5, sticky='w')
            tab.maximum_menus.append(max_text)

            min_label = ttk.Label(plot_customization_frame, text='Minimum Limit:')
            min_label.grid(row=2, column=1, padx=5, pady=5, sticky='w')
            min_text = ttk.Entry(plot_customization_frame)
            min_text.grid(row=3, column=1, padx=5, pady=5, sticky='w')
            tab.minimum_menus.append(min_text)

            var1_plot_type_label = ttk.Label(plot_type_frame, text='Plot Type File 1')
            var1_plot_type_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            var1_plot_type_var = tk.StringVar(value='line')
            var1_line_radio = ttk.Radiobutton(plot_type_frame, text='Line Plot', variable=var1_plot_type_var, value='line')
            var1_line_radio.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            var1_box_radio = ttk.Radiobutton(plot_type_frame, text='Box and Whisker', variable= var1_plot_type_var, value = 'box')
            var1_box_radio.grid(row=2, column=0, padx=5, pady=5, sticky='w')

            var1_color_type_label = ttk.Label(plot_type_frame, text='Color Type File 1:')
            var1_color_type_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')
            var1_color_type_var = tk.StringVar(value='blue')
            var1_color_blue = ttk.Radiobutton(plot_type_frame, text='Blue', variable=var1_color_type_var, value='blue')
            var1_color_blue.grid(row=1, column=1, padx=5, pady=5, sticky='w')
            var1_color_red = ttk.Radiobutton(plot_type_frame, text='Red', variable=var1_color_type_var, value='red')
            var1_color_red.grid(row=2, column=1, padx=5, pady=5, sticky='w')
            var1_color_green = ttk.Radiobutton(plot_type_frame, text='Green', variable=var1_color_type_var, value='green')
            var1_color_green.grid(row=3, column=1, padx=5, pady=5, sticky='w')

            var2_plot_type_label = ttk.Label(plot_type_frame, text='Plot Type File 2')
            var2_plot_type_label.grid(row=0, column=2, padx=5, pady=5, sticky='w')
            var2_plot_type_var = tk.StringVar(value='line')
            var2_line_radio = ttk.Radiobutton(plot_type_frame, text='Line Plot', variable=var2_plot_type_var, value='line')
            var2_line_radio.grid(row=1, column=2, padx=5, pady=5, sticky='w')
            var2_box_radio = ttk.Radiobutton(plot_type_frame, text='Box and Whisker', variable=var2_plot_type_var, value='box')
            var2_box_radio.grid(row=2, column=2, padx=5, pady=5, sticky='w')

            var2_color_type_label = ttk.Label(plot_type_frame, text='Color Type File 1:')
            var2_color_type_label.grid(row=0, column=3, padx=5, pady=5, sticky='w')
            var2_color_type_var = tk.StringVar(value='blue')
            var2_color_blue = ttk.Radiobutton(plot_type_frame, text='Blue', variable=var2_color_type_var, value='blue')
            var2_color_blue.grid(row=1, column=3, padx=5, pady=5, sticky='w')
            var2_color_red = ttk.Radiobutton(plot_type_frame, text='Red', variable=var2_color_type_var, value='red')
            var2_color_red.grid(row=2, column=3, padx=5, pady=5, sticky='w')
            var2_color_green = ttk.Radiobutton(plot_type_frame, text='Green', variable=var2_color_type_var, value='green')
            var2_color_green.grid(row=3, column=3, padx=5, pady=5, sticky='w')

            def plot_button_press():
                run_list = [run.get() for run in tab.run_menus]
                file_list = [file.get() for file in tab.file_menus]
                tiltle_list = [title.get() for title in tab.title_menus]
                unit_list = [unit.get() for unit in tab.unit_menus]
                min_list = [mins.get() for mins in tab.minimum_menus]
                max_list = [maxs.get() for maxs in tab.maximum_menus]
                plot_type_list = [var1_plot_type_var.get(), var2_plot_type_var.get()]
                color_type_list = [var1_color_type_var.get(), var2_color_type_var.get()]
                axis_type = tab.axis
                print('generating plot:')
                generate_plot_two_vars(tab, run_list, file_list, plot_type_list, tiltle_list, unit_list, plot_area_frame, min_list, max_list, color_type_list, axis_type)


            plot_button = ttk.Button(tab, text='Generate Plot',
                                    command= lambda: plot_button_press())
            plot_button.grid(row=3, column=2, columnspan=2, padx=10, pady=10, sticky='e')
            save_button = ttk.Button(tab, text='Save Plot', command = lambda: save_plot())
            save_button.grid(row = 3, column = 0, columnspan=2, padx=10, pady=10, sticky='w')

        def pearson_variable_plot(notebook):
            
            def update_selections(parent, frame_one, selection):
                for widget in frame_one.winfo_children():
                    widget.destroy() #destroy previous widgets
                parent.run_menus = []
                parent.file_menus = []
                parent.title_menus = []
                parent.unit_menus = []
                parent.minimum_menus = []
                parent.maximum_menus = []

                selection = selection.get()

                if selection == 'single':
                    run_label = ttk.Label(frame_one, text='Select Run:')
                    run_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
                    run_var = tk.StringVar(tab)
                    run_options = list(all_data.keys())
                    run_var.trace_add('write', lambda *args: update_variables_two_vars(tab, run_var, var1_menu, var1_file_var, var2_menu, var2_file_var))
                    run_menu = ttk.Combobox(frame_one, textvariable=run_var, values=run_options)
                    run_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

                    var1_label = ttk.Label(frame_one, text='Select File 1:')
                    var1_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
                    var1_file_var = tk.StringVar(tab)
                    var1_menu = ttk.Combobox(frame_one, textvariable=var1_file_var, values=[])
                    var1_menu.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

                    var2_label = ttk.Label(frame_one, text='Select File 2:')
                    var2_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
                    var2_file_var = tk.StringVar(tab)
                    var2_menu = ttk.Combobox(frame_one, textvariable=var2_file_var, values=[])
                    var2_menu.grid(row=2, column=1, padx=5, pady=5, sticky='w')

                    parent.run_menus.append(run_var)
                    parent.run_menus.append(run_var)
                    parent.file_menus.append(var1_file_var)
                    parent.file_menus.append(var2_file_var)

                elif selection == 'multiple':
                    run_label_1 = ttk.Label(frame_one, text='Select First Run:')
                    run_label_1.grid(row=0, column=0, padx=5, pady=5, sticky='w')
                    run_label_2 = ttk.Label(frame_one, text='Select Second Run:')
                    run_label_2.grid(row=0, column=1, padx=5, pady=5, sticky='w')
                    run_var_1 = tk.StringVar(parent)
                    run_options_1 = list(all_data.keys())
                    run_options_2 = list(all_data.keys())
                    run_var_2 = tk.StringVar(parent)
                    run_var_1.trace_add('write', lambda *args: update_files(parent, run_var_1, var1_menu, var1_file_var))
                    run_var_2.trace_add('write', lambda *args: update_files(parent, run_var_2, var2_menu, var2_file_var))
                    run_menu_1 = ttk.Combobox(frame_one, textvariable=run_var_1, values=run_options_1)
                    run_menu_1.grid(row=1, column=0, padx=5, pady=5, sticky='w')
                    run_menu_2 = ttk.Combobox(frame_one, textvariable=run_var_2, values=run_options_2)
                    run_menu_2.grid(row=1, column=1, padx=5, pady=5, sticky='w')

                    var1_label = ttk.Label(frame_one, text='Select File 1:')
                    var1_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
                    var1_file_var = tk.StringVar(tab)
                    var1_menu = ttk.Combobox(frame_one, textvariable=var1_file_var, values=[])
                    var1_menu.grid(row=3, column=0, padx=5, pady=5, sticky='ew')

                    var2_label = ttk.Label(frame_one, text='Select File 2:')
                    var2_label.grid(row=2, column=1, padx=5, pady=5, sticky='w')
                    var2_file_var = tk.StringVar(tab)
                    var2_menu = ttk.Combobox(frame_one, textvariable=var2_file_var, values=[])
                    var2_menu.grid(row=3, column=1, padx=5, pady=5, sticky='w')
                    
                    parent.run_menus.append(run_var_1)
                    parent.run_menus.append(run_var_2)
                    parent.file_menus.append(var1_file_var)
                    parent.file_menus.append(var2_file_var)



            tab = ttk.Frame(notebook)
            notebook.add(tab, text='Pearson Value')

            #run_frame = ttk.LabelFrame(tab, text='Run')
            #run_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')

            selection_frame = ttk.LabelFrame(tab, text='Selection type')
            selection_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
            
            file_frame = ttk.LabelFrame(tab, text='Files')
            file_frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
            
            plot_area_frame = ttk.LabelFrame(tab, text='Plot Display')
            plot_area_frame.grid(row=1, column = 0, columnspan=2, padx=10, pady=10, sticky='nsew')
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_columnconfigure(1, weight=1)
            tab.grid_rowconfigure(1, weight=1)
            
            run_type_label = ttk.Label(selection_frame, text='Select Run Type:')
            run_type_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            run_type_var = tk.StringVar(value='single')
            run_type = ttk.Combobox(selection_frame, text='Single Run', textvariable=run_type_var, value=['single', 'multiple'])
            run_type.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            
            run_type_var.trace_add('write', lambda *args: update_selections(tab, file_frame, run_type_var))
            tab.axis = False
            tab.run_menus = []
            tab.file_menus = []

            run_label = ttk.Label(file_frame, text='Select Run:')
            run_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            run_var = tk.StringVar(tab)
            run_options = list(all_data.keys())
            run_var.trace_add('write', lambda *args: update_variables_two_vars(tab, run_var, var1_menu, var1_file_var, var2_menu, var2_file_var))
            run_menu = ttk.Combobox(file_frame, textvariable=run_var, values=run_options)
            run_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
            tab.run_menus.append(run_var)
            tab.run_menus.append(run_var)

            var1_label = ttk.Label(file_frame, text='Select File 1:')
            var1_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            var1_file_var = tk.StringVar(tab)
            var1_menu = ttk.Combobox(file_frame, textvariable=var1_file_var, values=[])
            var1_menu.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
            tab.file_menus.append(var1_file_var)

            var2_label = ttk.Label(file_frame, text='Select File 2:')
            var2_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
            var2_file_var = tk.StringVar(tab)
            var2_menu = ttk.Combobox(file_frame, textvariable=var2_file_var, values=[])
            var2_menu.grid(row=2, column=1, padx=5, pady=5, sticky='w')
            tab.file_menus.append(var2_file_var)

            r_results_label = ttk.Label(plot_area_frame, text='R Value Results')
            r_results_label.grid(row=0, column=0, padx=10, pady=10, sticky='n')
            r_results_box = ttk.Entry(plot_area_frame)
            r_results_box.grid(row=1, column=0, padx=10, pady=10, sticky='n')

            p_results_label = ttk.Label(plot_area_frame, text='P Value Results')
            p_results_label.grid(row=0, column=1, padx=10, pady=10, sticky='n')
            p_results_box = ttk.Entry(plot_area_frame)
            p_results_box.grid(row=1, column=1, padx=10, pady=10, sticky='n')

            def plot_button_press():
                run_list = [run.get() for run in tab.run_menus]
                file_list = [file.get() for file in tab.file_menus]
                print('generating value...')
                generate_pearson_values(tab, run_list, file_list, r_results_box, p_results_box)


            plot_button = ttk.Button(tab, text='Generate Plot',
                                    command= lambda: plot_button_press())
            plot_button.grid(row=3, column=2, columnspan=2, padx=10, pady=10, sticky='e')
            save_button = ttk.Button(tab, text='Save Plot', command = lambda: save_plot())
            save_button.grid(row = 3, column = 0, columnspan=2, padx=10, pady=10, sticky='w')

        def percent_error_variable_plot(notebook):
            
            def update_selections(parent, frame_one, selection):
                for widget in frame_one.winfo_children():
                    widget.destroy() #destroy previous widgets
                parent.run_menus = []
                parent.file_menus = []
                parent.title_menus = []
                parent.unit_menus = []
                parent.minimum_menus = []
                parent.maximum_menus = []

                selection = selection.get()

                if selection == 'single':
                    run_label = ttk.Label(frame_one, text='Select Run:')
                    run_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
                    run_var = tk.StringVar(tab)
                    run_options = list(all_data.keys())
                    run_var.trace_add('write', lambda *args: update_variables_two_vars(tab, run_var, var1_menu, var1_file_var, var2_menu, var2_file_var))
                    run_menu = ttk.Combobox(frame_one, textvariable=run_var, values=run_options)
                    run_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

                    var1_label = ttk.Label(frame_one, text='Select File 1:')
                    var1_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
                    var1_file_var = tk.StringVar(tab)
                    var1_menu = ttk.Combobox(frame_one, textvariable=var1_file_var, values=[])
                    var1_menu.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

                    var2_label = ttk.Label(frame_one, text='Select File 2:')
                    var2_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
                    var2_file_var = tk.StringVar(tab)
                    var2_menu = ttk.Combobox(frame_one, textvariable=var2_file_var, values=[])
                    var2_menu.grid(row=2, column=1, padx=5, pady=5, sticky='w')

                    parent.run_menus.append(run_var)
                    parent.run_menus.append(run_var)
                    parent.file_menus.append(var1_file_var)
                    parent.file_menus.append(var2_file_var)

                elif selection == 'multiple':
                    run_label_1 = ttk.Label(frame_one, text='Select First Run:')
                    run_label_1.grid(row=0, column=0, padx=5, pady=5, sticky='w')
                    run_label_2 = ttk.Label(frame_one, text='Select Second Run:')
                    run_label_2.grid(row=0, column=1, padx=5, pady=5, sticky='w')
                    run_var_1 = tk.StringVar(parent)
                    run_options_1 = list(all_data.keys())
                    run_options_2 = list(all_data.keys())
                    run_var_2 = tk.StringVar(parent)
                    run_var_1.trace_add('write', lambda *args: update_files(parent, run_var_1, var1_menu, var1_file_var))
                    run_var_2.trace_add('write', lambda *args: update_files(parent, run_var_2, var2_menu, var2_file_var))
                    run_menu_1 = ttk.Combobox(frame_one, textvariable=run_var_1, values=run_options_1)
                    run_menu_1.grid(row=1, column=0, padx=5, pady=5, sticky='w')
                    run_menu_2 = ttk.Combobox(frame_one, textvariable=run_var_2, values=run_options_2)
                    run_menu_2.grid(row=1, column=1, padx=5, pady=5, sticky='w')

                    var1_label = ttk.Label(frame_one, text='Select File 1:')
                    var1_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
                    var1_file_var = tk.StringVar(tab)
                    var1_menu = ttk.Combobox(frame_one, textvariable=var1_file_var, values=[])
                    var1_menu.grid(row=3, column=0, padx=5, pady=5, sticky='ew')

                    var2_label = ttk.Label(frame_one, text='Select File 2:')
                    var2_label.grid(row=2, column=1, padx=5, pady=5, sticky='w')
                    var2_file_var = tk.StringVar(tab)
                    var2_menu = ttk.Combobox(frame_one, textvariable=var2_file_var, values=[])
                    var2_menu.grid(row=3, column=1, padx=5, pady=5, sticky='w')
                    
                    parent.run_menus.append(run_var_1)
                    parent.run_menus.append(run_var_2)
                    parent.file_menus.append(var1_file_var)
                    parent.file_menus.append(var2_file_var)



            tab = ttk.Frame(notebook)
            notebook.add(tab, text='Percent Error')

            #run_frame = ttk.LabelFrame(tab, text='Run')
            #run_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')

            selection_frame = ttk.LabelFrame(tab, text='Selection type')
            selection_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
            
            file_frame = ttk.LabelFrame(tab, text='Files')
            file_frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
            
            plot_area_frame = ttk.LabelFrame(tab, text='Plot Display')
            plot_area_frame.grid(row=1, column = 0, columnspan=2, padx=10, pady=10, sticky='nsew')
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_columnconfigure(1, weight=1)
            tab.grid_rowconfigure(1, weight=1)
            
            run_type_label = ttk.Label(selection_frame, text='Select Run Type:')
            run_type_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            run_type_var = tk.StringVar(value='single')
            run_type = ttk.Combobox(selection_frame, text='Single Run', textvariable=run_type_var, value=['single', 'multiple'])
            run_type.grid(row=1, column=0, padx=5, pady=5, sticky='w')

            limit_label = ttk.Label(selection_frame, text='Set Limit:')
            limit_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')
            limit_box = ttk.Entry(selection_frame)
            limit_box.grid(row=1, column=1, padx=5, pady=5, sticky='w')

            type_label = ttk.Label(selection_frame, text='Select Type:')
            type_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
            type_box_values = ['max', 'average']
            type_box_var = tk.StringVar(value='max')
            type_box = ttk.Combobox(selection_frame, textvariable=type_box_var, value=type_box_values)
            type_box.grid(row=3, column=0, padx=5, pady=5, sticky='w')
            
            run_type_var.trace_add('write', lambda *args: update_selections(tab, file_frame, run_type_var))
            tab.axis = False
            tab.run_menus = []
            tab.file_menus = []

            run_label = ttk.Label(file_frame, text='Select Run:')
            run_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            run_var = tk.StringVar(tab)
            run_options = list(all_data.keys())
            run_var.trace_add('write', lambda *args: update_variables_two_vars(tab, run_var, var1_menu, var1_file_var, var2_menu, var2_file_var))
            run_menu = ttk.Combobox(file_frame, textvariable=run_var, values=run_options)
            run_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
            tab.run_menus.append(run_var)
            tab.run_menus.append(run_var)

            var1_label = ttk.Label(file_frame, text='Select File 1:')
            var1_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            var1_file_var = tk.StringVar(tab)
            var1_menu = ttk.Combobox(file_frame, textvariable=var1_file_var, values=[])
            var1_menu.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
            tab.file_menus.append(var1_file_var)

            var2_label = ttk.Label(file_frame, text='Select File 2:')
            var2_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
            var2_file_var = tk.StringVar(tab)
            var2_menu = ttk.Combobox(file_frame, textvariable=var2_file_var, values=[])
            var2_menu.grid(row=2, column=1, padx=5, pady=5, sticky='w')
            tab.file_menus.append(var2_file_var)

            error_results_label = ttk.Label(plot_area_frame, text='Percent Error')
            error_results_label.grid(row=0, column=0, padx=10, pady=10, sticky='n')
            error_results_box = ttk.Entry(plot_area_frame)
            error_results_box.grid(row=1, column=0, padx=10, pady=10, sticky='n')

            def plot_button_press():
                run_list = [run.get() for run in tab.run_menus]
                file_list = [file.get() for file in tab.file_menus]
                type_list = type_box_var.get()
                limit_list = limit_box.get()


                print('generating value...')
                percent_error_values(tab, run_list, file_list, error_results_box, type_list, limit_list)


            plot_button = ttk.Button(tab, text='Generate Plot',
                                    command= lambda: plot_button_press())
            plot_button.grid(row=3, column=2, columnspan=2, padx=10, pady=10, sticky='e')

        def triple_variable_plot(notebook):
            
            def update_selections(parent, frame, frame_two, selection):
                for widget in frame.winfo_children():
                    widget.destroy() #destroy previous widgets
                for widget in frame_two.winfo_children():
                    widget.destroy() #destroy previous widgets
                parent.run_menus = []
                parent.file_menus = []
                parent.title_menus = []
                parent.unit_menus = []
                parent.minimum_menus = []
                parent.maximum_menus = []

                selection = selection.get()

                if selection == 'single':
                    run_label = ttk.Label(file_frame, text='Select Run:')
                    run_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
                    run_var = tk.StringVar(tab)
                    run_options = list(all_data.keys())
                    run_var.trace_add('write', lambda *args: update_variables_three_vars(tab, run_var, var1_menu, var1_file_var, var2_menu, var2_file_var, var3_menu, var3_file_var))
                    run_menu = ttk.Combobox(file_frame, textvariable=run_var, values=run_options)
                    run_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
                    
                    var1_label = ttk.Label(file_frame, text='Select File 1:')
                    var1_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
                    var1_file_var = tk.StringVar(tab)
                    var1_menu = ttk.Combobox(file_frame, textvariable=var1_file_var, values=[])
                    var1_menu.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

                    var2_label = ttk.Label(file_frame, text='Select File 2:')
                    var2_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
                    var2_file_var = tk.StringVar(tab)
                    var2_menu = ttk.Combobox(file_frame, textvariable=var2_file_var, values=[])
                    var2_menu.grid(row=2, column=1, padx=5, pady=5, sticky='ew')

                    var3_label = ttk.Label(file_frame,text='Select File 3:')
                    var3_label.grid(row=3, column=0, padx=5, pady=5, sticky='w')
                    var3_file_var = tk.StringVar(tab)
                    var3_menu = ttk.Combobox(file_frame, textvariable=var3_file_var, values=[])
                    var3_menu.grid(row=3, column=1, padx=5, pady=5, sticky='ew')

                    parent.run_menus.append(run_var)
                    parent.run_menus.append(run_var)
                    parent.run_menus.append(run_var)
                    parent.file_menus.append(var1_file_var)
                    parent.file_menus.append(var2_file_var)
                    parent.file_menus.append(var3_file_var)

                elif selection == 'multiple':
                    run_label_1 = ttk.Label(frame, text='Select First Run:')
                    run_label_1.grid(row=0, column=0, padx=5, pady=5, sticky='w')
                    run_label_2 = ttk.Label(frame, text='Select Second Run:')
                    run_label_2.grid(row=0, column=1, padx=5, pady=5, sticky='w')
                    run_label_3 = ttk.Label(frame, text='Select Third Run:')
                    run_label_3.grid(row=0, column=2, padx=5, pady=5, sticky='w')
                    run_options_1 = list(all_data.keys())
                    run_options_2 = list(all_data.keys())
                    run_options_3 = list(all_data.keys())
                    run_var_1 = tk.StringVar(parent)
                    run_var_2 = tk.StringVar(parent)
                    run_var_3 = tk.StringVar(parent)
                    run_var_1.trace_add('write', lambda *args: update_files(parent, run_var_1, var1_menu, var1_file_var))
                    run_var_2.trace_add('write', lambda *args: update_files(parent, run_var_2, var2_menu, var2_file_var))
                    run_var_3.trace_add('write', lambda *args: update_files(parent, run_var_3, var3_menu, var3_file_var))
                    run_menu_1 = ttk.Combobox(frame, textvariable=run_var_1, values=run_options_1)
                    run_menu_1.grid(row=1, column=0, padx=5, pady=5, sticky='w')
                    run_menu_2 = ttk.Combobox(frame, textvariable=run_var_2, values=run_options_2)
                    run_menu_2.grid(row=1, column=1, padx=5, pady=5, sticky='w')
                    run_menu_3 = ttk.Combobox(frame, textvariable=run_var_3, values=run_options_3)
                    run_menu_3.grid(row=1, column=2, padx=5, pady=5, sticky='w')

                    var1_label = ttk.Label(frame, text='Select File 1:')
                    var1_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
                    var1_file_var = tk.StringVar(tab)
                    var1_menu = ttk.Combobox(frame, textvariable=var1_file_var, values=[])
                    var1_menu.grid(row=3, column=0, padx=5, pady=5, sticky='ew')

                    var2_label = ttk.Label(frame, text='Select File 2:')
                    var2_label.grid(row=2, column=1, padx=5, pady=5, sticky='w')
                    var2_file_var = tk.StringVar(tab)
                    var2_menu = ttk.Combobox(frame, textvariable=var2_file_var, values=[])
                    var2_menu.grid(row=3, column=1, padx=5, pady=5, sticky='w')

                    var3_label = ttk.Label(frame, text='Select File 2:')
                    var3_label.grid(row=2, column=2, padx=5, pady=5, sticky='w')
                    var3_file_var = tk.StringVar(tab)
                    var3_menu = ttk.Combobox(frame, textvariable=var3_file_var, values=[])
                    var3_menu.grid(row=3, column=2, padx=5, pady=5, sticky='w')
                    
                    parent.run_menus.append(run_var_1)
                    parent.run_menus.append(run_var_2)
                    parent.run_menus.append(run_var_3)
                    parent.file_menus.append(var1_file_var)
                    parent.file_menus.append(var2_file_var)
                    parent.file_menus.append(var3_file_var)
                
                title_label = ttk.Label(frame_two, text='Title:') #label for title
                title_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
                title_text = ttk.Entry(frame_two) #entry for title
                title_text.grid(row=1, column=0, padx=5, pady=5, sticky='w')
                
                units_label = ttk.Label(frame_two, text='Units:') #label for title
                units_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')
                units_text = ttk.Entry(frame_two) #entry for title
                units_text.grid(row=1, column=1, padx=5, pady=5, sticky='w')

                max_label = ttk.Label(frame_two, text='Maximum Limit:')
                max_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
                max_text = ttk.Entry(frame_two)
                max_text.grid(row=3, column=0, padx=5, pady=5, sticky='w')

                min_label = ttk.Label(frame_two, text='Minimum Limit:')
                min_label.grid(row=2, column=1, padx=5, pady=5, sticky='w')
                min_text = ttk.Entry(frame_two)
                min_text.grid(row=3, column=1, padx=5, pady=5, sticky='w')

                parent.title_menus.append(title_text)
                parent.unit_menus.append(units_text)
                parent.minimum_menus.append(min_text)
                parent.maximum_menus.append(max_text)
            
            tab = ttk.Frame(notebook)
            notebook.add(tab, text='Triple Variable Plots')

            #run_frame = ttk.LabelFrame(tab, text='Run Selection')
            #run_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')
            
            selection_frame = ttk.LabelFrame(tab, text='Selection type')
            selection_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')

            file_frame = ttk.LabelFrame(tab, text='File Selection')
            file_frame.grid(row=0, column=1, columnspan=1, padx=10, pady=10, sticky='nsew')

            plot_type_frame = ttk.LabelFrame(tab, text='Plot Type Selection')
            plot_type_frame.grid(row=0, column=2, columnspan=1, padx=10, pady=10, sticky='nsew')

            selection_frame = ttk.LabelFrame(tab, text='Selection type')
            selection_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')

            plot_customization_frame = ttk.LabelFrame(tab, text='Plot Customization')
            plot_customization_frame.grid(row=1, column=2, padx=10, pady=10, sticky='nsew')

            plot_area_frame = ttk.LabelFrame(tab, text='Plot Display')
            plot_area_frame.grid(row=1, column = 0, columnspan=2, padx=10, pady=10, sticky='nsew')
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_columnconfigure(1, weight=1)
            tab.grid_rowconfigure(1, weight=1)

            run_type_label = ttk.Label(selection_frame, text='Select Run Type:')
            run_type_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            run_type_var = tk.StringVar(value='single')
            run_type_var.trace_add('write', lambda *args: update_selections(tab, file_frame, plot_customization_frame, run_type_var))
            run_type = ttk.Combobox(selection_frame, text='Single Run', textvariable=run_type_var, value=['single', 'multiple'])
            run_type.grid(row=1, column=0, padx=5, pady=5, sticky='w')

            tab.run_menus = []
            tab.file_menus = []
            tab.title_menus = []
            tab.unit_menus = []
            tab.minimum_menus = []
            tab.maximum_menus = []

            run_label = ttk.Label(file_frame, text='Select Run:')
            run_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            run_var = tk.StringVar(tab)
            run_options = list(all_data.keys())
            run_var.trace_add('write', lambda *args: update_variables_three_vars(tab, run_var, var1_menu, var1_file_var, var2_menu, var2_file_var, var3_menu, var3_file_var))
            run_menu = ttk.Combobox(file_frame, textvariable=run_var, values=run_options)
            run_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
            tab.run_menus.append(run_var)
            tab.run_menus.append(run_var)
            tab.run_menus.append(run_var)
            
            var1_label = ttk.Label(file_frame, text='Select File 1:')
            var1_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            var1_file_var = tk.StringVar(tab)
            var1_menu = ttk.Combobox(file_frame, textvariable=var1_file_var, values=[])
            var1_menu.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
            tab.file_menus.append(var1_file_var)

            var2_label = ttk.Label(file_frame, text='Select File 2:')
            var2_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
            var2_file_var = tk.StringVar(tab)
            var2_menu = ttk.Combobox(file_frame, textvariable=var2_file_var, values=[])
            var2_menu.grid(row=2, column=1, padx=5, pady=5, sticky='ew')
            tab.file_menus.append(var2_file_var)

            var3_label = ttk.Label(file_frame,text='Select File 3:')
            var3_label.grid(row=3, column=0, padx=5, pady=5, sticky='w')
            var3_file_var = tk.StringVar(tab)
            var3_menu = ttk.Combobox(file_frame, textvariable=var3_file_var, values=[])
            var3_menu.grid(row=3, column=1, padx=5, pady=5, sticky='ew')
            tab.file_menus.append(var3_file_var)

            title_label = ttk.Label(plot_customization_frame, text='Title:') #label for title
            title_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            title_text = ttk.Entry(plot_customization_frame) #entry for title
            title_text.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            tab.title_menus.append(title_text)
            
            units_label = ttk.Label(plot_customization_frame, text='Units:') #label for title
            units_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')
            units_text = ttk.Entry(plot_customization_frame) #entry for title
            units_text.grid(row=1, column=1, padx=5, pady=5, sticky='w')
            tab.unit_menus.append(units_text)

            max_label = ttk.Label(plot_customization_frame, text='Maximum Limit:')
            max_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
            max_text = ttk.Entry(plot_customization_frame)
            max_text.grid(row=3, column=0, padx=5, pady=5, sticky='w')
            tab.maximum_menus.append(max_text)

            min_label = ttk.Label(plot_customization_frame, text='Minimum Limit:')
            min_label.grid(row=2, column=1, padx=5, pady=5, sticky='w')
            min_text = ttk.Entry(plot_customization_frame)
            min_text.grid(row=3, column=1, padx=5, pady=5, sticky='w')
            tab.minimum_menus.append(min_text)

            var1_plot_type_label = ttk.Label(plot_type_frame, text='Plot Type File 1:')
            var1_plot_type_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            var1_plot_type_var = tk.StringVar(value='line')
            var1_line_radio = ttk.Radiobutton(plot_type_frame, text='Line Plot', variable=var1_plot_type_var, value='line')
            var1_line_radio.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            var1_box_radio = ttk.Radiobutton(plot_type_frame, text='Box and Whisker', variable= var1_plot_type_var, value = 'box')
            var1_box_radio.grid(row=2, column=0, padx=5, pady=5, sticky='w')

            var1_color_type_label = ttk.Label(plot_type_frame, text='Color Type File 1:')
            var1_color_type_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')
            var1_color_type_var = tk.StringVar(value='blue')
            var1_color_blue = ttk.Radiobutton(plot_type_frame, text='Blue', variable=var1_color_type_var, value='blue')
            var1_color_blue.grid(row=1, column=1, padx=5, pady=5, sticky='w')
            var1_color_red = ttk.Radiobutton(plot_type_frame, text='Red', variable=var1_color_type_var, value='red')
            var1_color_red.grid(row=2, column=1, padx=5, pady=5, sticky='w')
            var1_color_green = ttk.Radiobutton(plot_type_frame, text='Green', variable=var1_color_type_var, value='green')
            var1_color_green.grid(row=3, column=1, padx=5, pady=5, sticky='w')

            var2_plot_type_label = ttk.Label(plot_type_frame, text='Plot Type File 2:')
            var2_plot_type_label.grid(row=0, column=2, padx=5, pady=5, sticky='w')
            var2_plot_type_var = tk.StringVar(value='line')
            var2_line_radio = ttk.Radiobutton(plot_type_frame, text='Line Plot', variable=var2_plot_type_var, value='line')
            var2_line_radio.grid(row=1, column=2, padx=5, pady=5, sticky='w')
            var2_box_radio = ttk.Radiobutton(plot_type_frame, text='Box and Whisker', variable=var2_plot_type_var, value='box')
            var2_box_radio.grid(row=2, column=2, padx=5, pady=5, sticky='w')

            var2_color_type_label = ttk.Label(plot_type_frame, text='Color Type File 1:')
            var2_color_type_label.grid(row=0, column=3, padx=5, pady=5, sticky='w')
            var2_color_type_var = tk.StringVar(value='blue')
            var2_color_blue = ttk.Radiobutton(plot_type_frame, text='Blue', variable=var2_color_type_var, value='blue')
            var2_color_blue.grid(row=1, column=3, padx=5, pady=5, sticky='w')
            var2_color_red = ttk.Radiobutton(plot_type_frame, text='Red', variable=var2_color_type_var, value='red')
            var2_color_red.grid(row=2, column=3, padx=5, pady=5, sticky='w')
            var2_color_green = ttk.Radiobutton(plot_type_frame, text='Green', variable=var2_color_type_var, value='green')
            var2_color_green.grid(row=3, column=3, padx=5, pady=5, sticky='w')

            var3_plot_type_label = ttk.Label(plot_type_frame, text='Plot Type File 3:')
            var3_plot_type_label.grid(row=0, column=4, padx=5, pady=5, sticky='w')
            var3_plot_type_var = tk.StringVar(value='line')
            var3_line_radio = ttk.Radiobutton(plot_type_frame, text='Line Plot', variable=var3_plot_type_var, value='line')
            var3_line_radio.grid(row=1, column=4, padx=5, pady=5, sticky='w')
            var3_box_radio = ttk.Radiobutton(plot_type_frame, text='Box and Whisker', variable=var3_plot_type_var, value='box')
            var3_box_radio.grid(row=2, column=4, padx=5, pady=5, sticky='w')

            var3_color_type_label = ttk.Label(plot_type_frame, text='Color Type File 1:')
            var3_color_type_label.grid(row=0, column=6, padx=5, pady=5, sticky='w')
            var3_color_type_var = tk.StringVar(value='blue')
            var3_color_blue = ttk.Radiobutton(plot_type_frame, text='Blue', variable=var3_color_type_var, value='blue')
            var3_color_blue.grid(row=1, column=6, padx=5, pady=5, sticky='w')
            var3_color_red = ttk.Radiobutton(plot_type_frame, text='Red', variable=var3_color_type_var, value='red')
            var3_color_red.grid(row=2, column=6, padx=5, pady=5, sticky='w')
            var3_color_green = ttk.Radiobutton(plot_type_frame, text='Green', variable=var3_color_type_var, value='green')
            var3_color_green.grid(row=3, column=6, padx=5, pady=5, sticky='w')

            def plot_button_press():
                run_list = [run.get() for run in tab.run_menus]
                file_list = [file.get() for file in tab.file_menus]
                tiltle_list = [title.get() for title in tab.title_menus]
                unit_list = [unit.get() for unit in tab.unit_menus]
                min_list = [mins.get() for mins in tab.minimum_menus]
                max_list = [maxs.get() for maxs in tab.maximum_menus]
                plot_type_list = [var1_plot_type_var.get(), var2_plot_type_var.get(), var3_plot_type_var.get()]
                color_type_list = [var1_color_type_var.get(), var2_color_type_var.get(), var3_color_type_var.get()]
                print('generating plot:')
                generate_plot_three_vars(tab, run_list, file_list, plot_type_list, tiltle_list, unit_list, plot_area_frame, min_list, max_list, color_type_list)

            plot_button = ttk.Button(tab, text='Generate Plot',
                                    command= lambda: plot_button_press())
            plot_button.grid(row=3, column=2, columnspan=2, padx=10, pady=10, sticky='e')
            save_button = ttk.Button(tab, text='Save Plot', command = lambda: save_plot())
            save_button.grid(row = 3, column = 0, columnspan=2, padx=10, pady=10, sticky='w')
            
        def update_variables_three_vars(parent, run_var, var1_menu, var1_file_var,
                                        var2_menu, var2_file_var,
                                        var3_menu, var3_file_var):
            selected_run = run_var.get()
            var1_menu['values'] = []
            var1_file_var.set('')
            var2_menu['values'] = []
            var2_file_var.set('')
            var3_menu['values'] = []
            var3_file_var.set('')
            if selected_run and selected_run in all_data:
                files = sorted(all_data[selected_run].keys())
                var1_menu['values'] = files
                var2_menu['values'] = files
                var3_menu['values'] = files
                if files:
                    var1_file_var.set(files[0])
                    var2_file_var.set(files[0])
                    var3_file_var.set(files[0])

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

        def generate_plot(parent, run_var, file_var, title_var, unit_var, plot_type_var, plot_area_frame, min_l, max_l):
            selected_run = run_var.get()
            selected_file = file_var.get()
            selected_title = title_var.get()
            selected_units = unit_var.get()
            plot_type = plot_type_var.get()
            max_lim = max_l.get()
            min_lim = min_l.get()
            max_min = [max_lim, min_lim]
            sorted_limit = sorted(max_min)
            for widget in plot_area_frame.winfo_children():
                widget.destroy() #destroy previous widgets
            plt.close('all')
            plt.clf()
            if selected_run and selected_file and selected_run in all_data and selected_file in all_data[selected_run]:
                screen_width = root.winfo_screenwidth()
                screen_height = root.winfo_screenheight()
                max_width = screen_width*0.9
                max_height = screen_height*0.9
                aspect_ratio = 1
                plt.figure(figsize=(min(max_width / 100, max_height / 100), min(max_width / 100, max_height / 100)))
                plt.grid(True, alpha = 0.5)
                data_to_plot = all_data[selected_run][selected_file]
                sheet_names = list(data_to_plot.keys())
                if plot_type == 'line':
                    line_plot(data_to_plot, f'{selected_title}', f'{selected_units}', sheet_names, sorted_limit)
                elif plot_type == 'box':
                    Box_Whisker_preloaded(data_to_plot, f'{selected_title}', f'{selected_units}', sheet_names, sorted_limit)
                
                canvas = FigureCanvasTkAgg(plt.gcf(), master=plot_area_frame) #create canvas
                canvas_widget = canvas.get_tk_widget() #get canvas widget
                canvas_widget.pack() #pack canvas widget
                canvas.draw() #draw canvas
            else:
                print('Error: Invalid Selection')

        def generate_plot_two_vars(parent, run_var_list, file_var_list, plot_type_list, title_var_list, unit_var_list, plot_area_frame,
                                   min_list, max_list, color_list, ax2 = False):
            data = []
            sheets = []
            if len(run_var_list) == len(file_var_list):
                for run, file in zip(run_var_list, file_var_list):
                    plot_data = all_data[run][file]
                    data.append(plot_data)
                    sheet_name = list(plot_data.keys())
                    sheets.append(sheet_name)
            else:
                print(f"Runs or files are too few \n Number of runs: {len(run_var_list)} \n Number of files: {len(file_var_list)}")
            min_max = []
            print(f"All Minimums: {min_list}")
            print(f"All Maximums: {max_list}")
            if len(min_list) == len(max_list):
                for mins, maxs in zip(min_list, max_list):
                    print(f"mins {mins}")
                    print(f"maxs {maxs}")
                    box = [mins, maxs]
                    box.sort()
                    print(f"ordered pair: {box}")
                    min_max.append(box)
                print(f'Mins and Maxs ordered pairs: {min_max} \n Number of ordered pairs: {len(min_max)}')
            for widget in plot_area_frame.winfo_children():
                widget.destroy()
            plt.close('all')
            plt.clf()
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            max_width = screen_width*0.9
            max_height = screen_height*0.9
            fig, ax1 = plt.subplots(figsize=(min(max_width / 100, max_height / 100), min(max_width / 100, max_height / 100)))
            ax1.grid(True, alpha = 0.5)
            ax_secondary = None
            if ax2 is True:
                ax_secondary = ax1.twinx()
            if len(plot_type_list) == len(data):
                for i in range(len(plot_type_list)):
                    current_plot_ax = ax_secondary if ax2 and i == 1 else ax1
                    current_unit_type = None
                    if i < len(unit_var_list): # Check if 'i' is a valid index
                        current_unit_type = unit_var_list[i]
                    elif unit_var_list: # If 'i' is out of bounds but list is not empty, use the first element
                        current_unit_type = unit_var_list[0]
                    else: # If the list is empty, provide a default or None
                        current_unit_type = "Unit" # Or None, depending on desired behavior

                    # Safely get min_max for the current plot
                    current_min_max = None
                    if i < len(min_max): # Check if 'i' is a valid index
                        current_min_max = min_max[i]
                    elif min_max: # If 'i' is out of bounds but list is not empty, use the first element
                        current_min_max = min_max[0]
                    
                    print(f"Current max and min: {current_min_max}")
                    if plot_type_list[i] == 'line':
                        line_plot(data[i], f'{title_var_list[0]}', f'{current_unit_type}', sheets[i], current_min_max, color_type=color_list[i], ax=current_plot_ax)
                    elif plot_type_list[i] =='box':
                        Box_Whisker_preloaded(data[i], f'{title_var_list[0]}', f'{current_unit_type}', sheets[i], current_min_max, ax=current_plot_ax)
                canvas = FigureCanvasTkAgg(fig, master=plot_area_frame)
                canvas_widget = canvas.get_tk_widget()
                canvas_widget.pack()
                canvas.draw()
            else:
                print("Error: plot type doesn't match data")
                print(f"number of plots: {len(plot_type_list)}")
                print(f"number of data points: {len(data)}")

        def generate_plot_three_vars(parent, run_var_list, file_var_list, plot_type_list, title_var_list, unit_var_list, plot_area_frame,
                                   min_list, max_list, color_list):
            data = []
            sheets = []
            if len(run_var_list) == len(file_var_list):
                for run, file in zip(run_var_list, file_var_list):
                    plot_data = all_data[run][file]
                    data.append(plot_data)
                    sheet_name = list(plot_data.keys())
                    sheets.append(sheet_name)
            else:
                print(f"Runs or files are too few \n Number of runs: {len(run_var_list)} \n Number of files: {len(file_var_list)}")
            min_max = []
            if len(min_list) == len(max_list):
                for mins, maxs in zip(min_list, max_list):
                    box = [mins, maxs]
                    min_max.append(box)
            for widget in plot_area_frame.winfo_children():
                widget.destroy()
            plt.close('all')
            plt.clf()
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            max_width = screen_width*0.9
            max_height = screen_height*0.9
            aspect_ratio = 1
            plt.figure(figsize=(min(max_width / 100, max_height / 100), min(max_width / 100, max_height / 100)))
            plt.grid(True, alpha = 0.5)
            if len(plot_type_list) == len(data):
                for i in range(len(plot_type_list)):
                    if plot_type_list[i] == 'line':
                        line_plot(data[i], f'{title_var_list[0]}', f'{unit_var_list[0]}', sheets[i], min_max[0], color_type=color_list[i])
                    elif plot_type_list[i] =='box':
                        Box_Whisker_preloaded(data[i], f'{title_var_list[0]}', f'{unit_var_list[0]}', sheets[i], min_max[0])
                canvas = FigureCanvasTkAgg(plt.gcf(), master=plot_area_frame)
                canvas_widget = canvas.get_tk_widget()
                canvas_widget.pack()
                canvas.draw()
            else:
                print("Error: plot type doesn't match data")
                print(f"number of plots: {len(plot_type_list)}")
                print(f"number of data points: {len(data)}")

        def generate_pearson_values(parent, run_var_list, file_var_list, r_box, p_box):
            data = []
            sheets = []
            if len(run_var_list) == len(file_var_list):
                for run, file in zip(run_var_list, file_var_list):
                    plot_data = all_data[run][file]
                    data.append(plot_data)
                    sheet_name = list(plot_data.keys())
                    sheets.append(sheet_name)
            else:
                print(f"Runs or files are too few \n Number of runs: {len(run_var_list)} \n Number of files: {len(file_var_list)}")
            r_value_product, p_value_product = pearsoncc(data[0], data[1], sheets[0], sheets[1])
            r_box.delete(0, tk.END)
            r_box.insert(0, f'{str(r_value_product):.6}')
            p_box.delete(0, tk.END)
            p_box.insert(0, f'{str(p_value_product):.6}')
        
        def percent_error_values(parent, run_var_list, file_var_list, percent_box, type, limit):
            data = []
            sheets = []
            if len(run_var_list) == len(file_var_list):
                for run, file in zip(run_var_list, file_var_list):
                    plot_data = all_data[run][file]
                    data.append(plot_data)
                    sheet_name = list(plot_data.keys())
                    sheets.append(sheet_name)
            else:
                print(f"Runs or files are too few \n Number of runs: {len(run_var_list)} \n Number of files: {len(file_var_list)}")
            PE = percent_error(data[0], data[1], sheets[0], sheets[1], type, limit)
            percent_box.delete(0, tk.END)
            percent_box.insert(0, f'{str(PE):.6}%')

        root = tk.Tk()
        root.title('Data Visulization')

        notebook = ttk.Notebook(root)
        notebook.pack(fill='both', expand=True)

        single_variable_plot(notebook)
        double_variable_plot(notebook)
        triple_variable_plot(notebook)
        pearson_variable_plot(notebook)
        percent_error_variable_plot(notebook)

        root.mainloop()