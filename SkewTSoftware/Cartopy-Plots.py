import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.io.shapereader as shpreader
import geopandas as gpd

fig = plt.figure(figsize=(10,10))
proj = ccrs.Miller(central_longitude=-91.83)
ax = fig.add_subplot(1,1,1, projection=proj)
state_name = 'Missouri'
script_dir = os.path.dirname(__file__)
states_path = os.path.join(script_dir, 'Cartopy-Files\\ne_110m_admin_1_states_provinces.zip')
counties_path = os.path.join(script_dir, 'Cartopy-files', 'ne_20m_admin_0_counties.zip')
cities_path = os.path.join(script_dir, 'Cartopy-Files', 'ne_110m_populated_places.zip')
try:
    states = gpd.read_file(states_path)
    counties = gpd.read_file(counties_path)
    print('First few rows of the counties in Geoframe:')
    print(counties.head())
    print('\nColumns names in counties Geoframe:')
    print(counties.columns)
    print(counties['FEATURECLA'])
    cities = gpd.read_file(cities_path)
    selected_state = states[states['name']==state_name]
    us_counies = counties[counties['adm0_a3']=='USA']
    print('first few rows of us_counties geoframe:')
    print(us_counies.head())
    minx, miny, maxx, maxy = selected_state.total_bounds
    relevant_counties = us_counies.cx[minx:maxx, miny:maxy]
    if selected_state.empty:
        print(f"couldn't find data for the state {state_name}")
        exit()
    if us_counies.empty:
        print(f"couldn't find data for the united states counties")
        exit()
    
    state_geometry = selected_state.geometry.iloc[0]
    ax.set_extent([state_geometry.bounds[0]-2,
                   state_geometry.bounds[2]+2,
                   state_geometry.bounds[1]-2,
                   state_geometry.bounds[3]+2], crs=ccrs.Miller())
    ax.add_geometries([state_geometry], crs=ccrs.Miller(), 
                      facecolor=cfeature.COLORS['land'], edgecolor='black', linewidth=1)
    ax.add_geometries(relevant_counties, crs=ccrs.Miller(), facecolor='none', edgecolor='black', linewidth=1)
    
    ax.set_title(f'Map of {state_name}')

    plt.show()
except FileNotFoundError:
    print("Error: Shapefile not found. Cartopy might be installed correctly or the data is missing.")
    print("Try running: import cartopy.io.shapereader; cartopy.io.shapereader.natural_earth()")
except Exception as e:
    print(f'An error occured: {e}')