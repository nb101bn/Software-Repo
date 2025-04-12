import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

script_dir = os.path.dirname(__file__)
print(script_dir)
full_dir = os.path.join(script_dir, 'TSSN_reports.xlsx')
print(full_dir)
df = pd.read_excel(full_dir)
print(len(df['Type 1, 2, 3, 4, 5']))
lats = []
lons = []
for i in range(len(df['Type 1, 2, 3, 4, 5'])):
    if df['Type 1, 2, 3, 4, 5'][i] == 1:
        print(df['lat'][i])
        print(df['lon'][i])
        lats.append(df['lat'][i])
        lons.append(df['lon'][i])

print(f'lats: {lats}')
print(f'lons: {lons}')        