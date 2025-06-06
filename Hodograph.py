import metpy as mp
from metpy.units import units
from metpy.plots import SkewT, Hodograph
import metpy.calc as mpcalc
import matplotlib.pyplot as plt
from siphon.simplewebservice.wyoming import WyomingUpperAir
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import datetime
import pandas as pd
import time

station = 'OAX'
date = datetime.datetime(2013, 6, 1, 12)
retries = 3
for i in range(retries):
    try:
        df = WyomingUpperAir.request_data(date, station)
    except Exception as e:
        print(f"couldn't gather data error: {e} attempt {i}")
        time.sleep(5)
print(df.columns)
uw = df['u_wind'].values*units.knots
vw = df['v_wind'].values*units.knots
pl = df['pressure'].values*units.hPa


def plot_hodograph(u, v, levels=None, title="Hodograph"):
    """
    Plots a hodograph given u and v wind components.

    Args:
        u (array-like): U wind components (eastward).
        v (array-like): V wind components (northward).
        levels (array-like, optional): Pressure levels corresponding to u and v.
        title (str, optional): Title of the plot.
    """

    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(1, 1, 1)
    
    mask = levels>300*units.hPa
    u_mask = u[mask]
    v_mask = v[mask]
    levels_mask = levels[mask]

    h = Hodograph(ax, component_range=80)  # Adjust component_range as needed
    h.add_grid(increment=80)  # Adjust grid increment as needed
    #h.wind_vectors(u_mask, v_mask)
    h.plot_colormapped(u_mask,v_mask, levels_mask)
    '''
    if levels is not None:
        # Optionally, plot pressure labels along the hodograph
        h.ax.clabel(h.plot_wind(u, v, label="Wind"), inline=True, fontsize=8)
    '''
    ax.set_title(title)
    ax.legend()
    plt.show()

#plot_hodograph(uw, vw, pl)

def three_D_hodograph(u,v,levels, title='3D Hodograph'):
    """
    Plots a 3D compass with wind vectors originating from the z-axis.

    Args:
        u (array-like): U wind components (eastward).
        v (array-like): V wind components (northward).
        levels (array-like): Pressure levels to plot.
        title (str, optional): Title of the plot.
    """

    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='3d')
    mask_300 = levels>300*units.hPa
    levels = levels[mask_300]
    u = u[mask_300]
    v = v[mask_300]
    # Convert levels to numerical values for 3D plotting
    levels_mag = levels.to(units.hPa).magnitude

    # Plot the compass circle at the bottom level
    theta = np.linspace(0, 2*np.pi, 100)
    x_circle = 80 * np.cos(theta)
    y_circle = 80 * np.sin(theta)
    ax.plot(x_circle, y_circle, levels_mag[0], color='gray', linestyle='--', alpha=0.5)

    # Plot the axes at the bottom level
    ax.plot([-80, 80], [0, 0], levels_mag[0], color='gray', linestyle='--', alpha=0.5)
    ax.plot([0, 0], [-80, 80], levels_mag[0], color='gray', linestyle='--', alpha=0.5)

    # Plot the pressure levels along the z-axis
    ax.plot([0, 0], [0, 0], [levels_mag[0], levels_mag[-1]], color='black', linewidth=2)

    # Plot wind vectors from the z-axis (origin) to (u, v) at each level
    u_knots = u.to(units.knots).magnitude
    v_knots = v.to(units.knots).magnitude

    # Check for array length mismatch. If so, print an error and stop.
    if len(levels_mag) != len(u_knots) or len(levels_mag) != len(v_knots):
        print("Error: levels, u, and v arrays must have the same length.")
        return

    #for i in range(len(levels_mag)):   
        #ax.quiver(0, 0, levels_mag[i], u_knots[i], v_knots[i], 0, arrow_length_ratio=0.1, color='blue')

    # Connect the vector tips with a line
    for lvl in range(len(levels)):
        if levels[lvl] > 700 * units.hPa:
            c = 'red'
            mask_red = levels > 600 * units.hPa
            ax.plot(u_knots[mask_red], v_knots[mask_red], levels_mag[mask_red], color=c, linewidth=2)
        elif 500 * units.hPa < levels[lvl] <= 700 * units.hPa:
            c = 'green'
            mask_green = (levels < 700 * units.hPa) & (levels > 450 * units.hPa)
            ax.plot(u_knots[mask_green], v_knots[mask_green], levels_mag[mask_green], color=c, linewidth=2)
        elif levels[lvl] <= 500 * units.hPa:
            c = 'purple'
            mask_purple = levels < 500 * units.hPa
            ax.plot(u_knots[mask_purple], v_knots[mask_purple], levels_mag[mask_purple], color=c, linewidth=2)

    label_points = {
    700 * units.hPa: '3km',
    500 * units.hPa: '6km',
    977 * units.hPa: '1km'
}

# Find the indices closest to the specified pressure levels and plot/label
    for pressure, label in label_points.items():
        # Find the index of the level closest to the target pressure
        idx = np.argmin(np.abs(levels - pressure))
        pressure_at_idx = levels_mag[idx]
        u_at_idx = u_knots[idx]
        v_at_idx = v_knots[idx]

        # Plot a red dot at the point
        ax.scatter(u_at_idx, v_at_idx, pressure_at_idx, color='black', s=50)

        # Add a text label slightly offset from the point
        ax.text(u_at_idx + 5, v_at_idx + 5, pressure_at_idx, label, color='black')
    
    # Set axis labels
    ax.set_xlabel('Eastward Wind (knots)')
    ax.set_ylabel('Northward Wind (knots)')
    ax.set_zlabel('Pressure (hPa)')

    # Set plot title
    ax.set_title(title)

    # Invert the z-axis to represent pressure decreasing upwards
    ax.invert_zaxis()

    plt.show()

three_D_hodograph(uw, vw, pl)

'''
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

x = (-5, 5, 0.25)
y = (-5, 5, 0.25)

x,y = np.meshgrid(x,y)
z = np.sin(np.sqrt(x**2+y**2))

ax.plot_wireframe(x, y, z,  color='black')
plt.show()
'''