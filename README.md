# OpenSATQKD

This repository contains the source code for **OpenSATQKD**, a framework for modeling and evaluating satellite QKD missions. The simulator calculates all key quantities from realistic experimental parameters and open-source tools (no precomputed data or proprietary software needed). OpenSATQKD integrates orbital propagation, free-space link losses, optical hardware characterization, noisy quantum channel simulation, post-processing, and secret key rate estimation in a single platform. It’s designed to support mission planning, performance studies, and educational demonstrations in satellite-based quantum communication.

---

## Installation

**Requirements:**

- Python 3.10 or above (we recommend using Conda to create a virtual environment)
- Linux is recommended (Libradtran is only officially supported in Linux). Windows can work via WSL.
- MATLAB (with CVX and QETLAB libraries) and the MATLAB Python API

**Steps:**

1. **Clone the repository:**
```bash
git clone https://github.com/fjlc-73/OpenSATQKD.git
cd OpenSATQKD
git submodule update --init --recursive
```
2. **Create and activate a virtual environment:**
 ```bash
conda create -n opensatqkd python=3.10.18
conda activate opensatqkd
```
3. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```
4. **Install [libRadtran](https://github.com/LSSTDESC/libradtranpy) and its Python wrapper** following the instructions on the GitHub page.
5. **Install [openQKDsecurity](https://github.com/Optical-Quantum-Communication-Theory/openQKDsecurity)** for MATLAB-based computations:
   - Install MATLAB libraries **CVX** and **QETLAB**.
   - Install the MATLAB Python API by opening MATLAB and running:
```matlab
cd (fullfile(matlabroot,'extern','engines','python'))
system('python -m pip install .')
```
6. **Other external dependencies:**
   - [Cascade Python](https://github.com/brunorijsman/cascade-python) is used but not included as a submodule because minor modifications were made for compatibility with this project.
  

## Running the Simulator

1. **Activate the virtual environment.**
2. **Set the `PYTHONPATH` environment variable to the project root folder:**
```bash
env:PYTHONPATH="C:\path\to\project_root"
```
3. **Navigate to the simulator folder:**
```bash
cd C:\path\to\project_root\simulator
```
4. **Run the GUI:**
```bash
python main.py
```
**Optional:** Recreate Micius experiments  
To do this, click **Load Preset** in the GUI and select any pass from the `micius_data` folder (`.json` files).
> **⚠️ Note:** To automatically recreate past mission passes with realistic weather, make sure to enable the optional automatic weather feature by setting up the Copernicus CDS and ADS API keys as described below.
> 
**Optional:** Recreate passes from past missions using automatic weather  
To use this feature, you need API access from Copernicus Climate and Atmosphere Data Stores:

1. Create an account at [Copernicus CDS](https://cds.climate.copernicus.eu/), accept the terms of use for [ERA5 Single Levels](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=download), and get your API key from your profile.  
2. Create an account at [Copernicus ADS](https://ads.atmosphere.copernicus.eu/), accept the terms for [CAMS Global Reanalysis EAC4](https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4?tab=download), and get your API key.  
3. Create a `.env` file in the project root and add your keys as:
```text
CDS_API_KEY=<your_cds_api_key>
ADS_API_KEY=<your_ads_api_key>
```


## Running the Educational Component

1. Open **two separate PowerShell windows**.
2. In both, navigate to the educational folder:
```bash
cd C:\path\to\project_root\educational
```
3. **Set the `PYTHONPATH` environment variable to the project root folder:**
```bash
env:PYTHONPATH="C:\path\to\project_root"
```
4. **In the first window, run the ground station simulation:**
```bash
python ground.py"
```
5. **In the second window, run the satellite simulation:**
```bash
python satellite.py
```
> **Note:** Simulation parameters can be modified in `config_educ.py` located inside the `educational` folder before running the scripts.

### Finding public TLE data
We recommend using [Space-Track](https://www.space-track.org) for satellite TLE data. An account is required to access TLE information.


