import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import cartopy.feature as cfeature
import numpy as np
import pickle
import os

MAP_FILE = 'saved_map.pkl'

def initialize_map():
    extent = [-125, -66.5, 24, 49]
    num_lons = 1100
    num_lats = 900

    lons = np.linspace(extent[0], extent[1])
    lats = np.linspace(extent[2], extent[3])

    #creates the map
    fig = plt.figure(figsize=(150, 210))
    proj = ccrs.NorthPolarStereo(central_longitude=-105)
    ax = fig.add_subplot(1, 1, 1, projection=proj)
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.COASTLINE)
    land_10m = cfeature.NaturalEarthFeature('physical', 'land', '10m')
    ax.add_feature(land_10m, edgecolor='black', facecolor=cfeature.COLORS['land'])
    ax.add_feature(cfeature.LAKES, alpha=0.75)
    provinces = cfeature.NaturalEarthFeature(
        category='cultural',
        name='admin_1_states_provinces_lakes',
        scale='10m',
        facecolor='none',
        edgecolor='black')
    ax.add_feature(provinces)
    gl = ax.gridlines(draw_labels=True, linewidth=2,color='gray',alpha=0.5)
    gl.xlocator = plt.FixedLocator(lons[::50])
    gl.ylocator = plt.FixedLocator(lats[::50])
    gl.xlabels_top = False
    gl.ylabels_right = False
    plt.show()

def load_map():
    if os.path.exists(MAP_FILE):
        with open(MAP_FILE, 'rb') as f:
            return pickle.load(f)
    else:
        return None, None

def save_map(fig, ax):
    with open(MAP_FILE, 'wb') as f:
        pickle.dump((fig, ax), f)

# Load or initialize the map
fig, ax = load_map()
#if fig is None or ax is None:
    #fig, ax = initialize_map()

# Save the map for future use
#save_map(fig, ax)

plt.show()

# Example of calling the plot multiple times with different data on the same map *in a new python session*
lons2 = np.array([-110, -95, -85, -75])
lats2 = np.array([35, 45, 55, 65])
cloud_cover2 = np.array([0.1, 0.4, 0.7, 0.9])
tair2 = np.array([28, 22, 17, 12])
dewpt2 = np.array([18, 12, 7, 2])
pressure2 = np.array([1012, 1007, 1002, 997])
stid2 = ['E', 'F', 'G', 'H']
u2 = np.array([8,12,18,22])
v2 = np.array([8,12,18,22])

fig, ax = load_map()
if fig is None or ax is None:
    fig,ax = initialize_map()
save_map(fig,ax)
plt.show()