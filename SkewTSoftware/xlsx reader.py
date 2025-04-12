import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
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
        lats.append(float(df['lat'][i]))
        lons.append(float(df['lon'][i]))
print(f'Len Lons: {len(lons)}')
print(f'lons: {lons}')
print(f'Len Lats: {len(lats)}')
print(f'lats: {lats}')   

fig = plt.figure(figsize=(15, 21))
proj = ccrs.PlateCarree(central_longitude=-105)
ax = fig.add_subplot(1,1,1, projection=proj)
lons_np = np.array(lons)
lats_np = np.array(lats)
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
plt.title('Cyclonic Thunder Snow (Type 1)', fontsize=25)
plt.show()