#### Software-Repo

## Overview
This repository serves as my personal collection of software projects, scripts, and tools that I am currently developing or have worked on.
It also works as a hub for various frelance softwares that I've developed under commision. Each utility is primarily focused on meteorological
visulization or some form of data interpretation.

## Key Projects
Here are the main notable projects contained within this repository:
1. Hodograph.py
    A Python script designed to plot hodographs in three dimentions compared to their typical two dimentional plotting. This tool helps analyze
    the vertical atmospheric trends and wind shifts in a more three dimentional perspective.

2. SkewTSoftware/Skew-T Plotting
    This script is part of a software suite for generating Skew-T diagrams and their thermodynamic profiles. Additionally this suite offers
    excel interpretation that can plot latitude and longitude coordinates on a map. To gather the data the user can either interface with
    Wyoming Upper Air API or provide their own data.

3. GraphingSoftware/Excel_plotting.py
    A utility script for plotting data directly from Excel files. This project provides a convenient way to visualize tabular data stored in
    '.xlsx' or '.xls' files without manual data entry into other plotting tools.

## Installation
1. **Clone the repository:**
```
git clone https://github.com/nb101bn/Weather-Prediction-AI.git`
cd Weather-Prediction-AI
```

2. **Create a virtual environment:**
```
python -m venv {environment name}`
 # On Windows:`
 .\venv\Scripts\activate`
 # On macOS/Linux`
 source {environment name}/bin/activate
``` 
*Replace '{Environment name}' with your desired name for the virtual environment.*

3. **Install the required dependencies:**
```
pip install -r requirements.txt
```

## Usage
Each project within this repository is largely independent. To use specific scripts, navigate to its directory and run it directly. For example:
```
# To run the Hodograph plotting script
cd Software-Repo
python Hodograph.py

# To run the Skew-T plotting script
cd Software-Repo/SkewTSoftware
python "Skew-T Plotting.py" # Note: quotes for spaces in filename

# To run the Excel plotting script
cd Software-Repo/GraphingSoftware
python Excel_Plotting.py
```
**note:** Ensure you have activaed your virtual environmentbefore running any scripts.

## Contact
[nb101bn](https://github.com/nb101bn)