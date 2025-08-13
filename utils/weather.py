from datetime import datetime, timedelta
import cdsapi
import xarray as xr
import numpy as np
from dotenv import load_dotenv
import os
import cdsapi

def round_to_nearest_3hour(dt):
    hour = dt.hour
    # Round to nearest multiple of 3
    rounded_hour = int(round(hour / 3.0)) * 3
    # Handle 24 case
    if rounded_hour == 24:
        dt += timedelta(days=1)
        rounded_hour = 0
    return dt.replace(hour=rounded_hour)

def round_to_nearest_hour(dt):
    # Add 30 minutes and truncate to hour
    return (dt + timedelta(minutes=30))

def classify_climate(lat:float, lon:float, dt:datetime, elevation:float=0)->str:
    """
    Classifies a location into a simplified climate category based on
    latitude, longitude, date, and elevation.
    
    ### Climate Classes:
        tp: Tropical
        ms: Midlatitude Summer
        mw: Midlatitude Winter
        ss: Subarctic Summer
        sw: Subarctic Winter
        us: US Standard

    ### Parameters:
    - lat (float): Latitude in degrees. Positive for Northern Hemisphere.
    - lon (float): Longitude in degrees. Negative for Western Hemisphere.
    - dt (datetime): Datetime object of current time.
    - elevation (float, optional): Elevation in meters above sea level. Default is 0.

    ### Returns:
    - string: Type of atmosphere according to classification.
    """
    
    month = dt.month
    abs_lat = abs(lat)

    # Determine if it's summer at the given latitude
    if lat >= 0:  
        is_summer = month in [4, 5, 6, 7, 8, 9] #Northern Hemisphere
    else:         
        is_summer = month in [10, 11, 12, 1, 2, 3] # Southern Hemisphere

    # Adjust latitude to reflect elevation impact on climate
    # Approximate: every 150m elevation ~ 1° poleward shift in climate
    elevation_adjustment = min(elevation / 150, 20)  # Cap adjustment to 20°
    effective_lat = abs_lat + elevation_adjustment

    # Determine if location is within continental U.S.
    is_us_region = (-125 <= lon <= -65) and (24 <= lat <= 50)

    # --- Classification Logic ---

    # Tropical zone: low latitude and low elevation
    if effective_lat < 23.5:
        if elevation >= 1500:
            return "ms" if is_summer else "mw"  # High-elevation tropics = temperate-like
        return "tp"  # Lowland tropics

    # US override: Use a standard classification for known U.S. region
    if is_us_region and 23.5 <= effective_lat < 50:
        return "us"

    # Midlatitude zones
    if 23.5 <= effective_lat < 50:
        return "ms" if is_summer else "mw"

    # Subarctic zone
    if effective_lat >= 50:
        return "ss" if is_summer else "sw"

    # Fallback (shouldn't be reached unless input is unusual)
    return "us"

def obtain_atmospheric_parameters(date, lat, lon):

    load_dotenv()

    # Fetch keys from environment variables
    cds_key = os.getenv("CDS_API_KEY")
    ads_key = os.getenv("ADS_API_KEY")

        # CDS Client
    cds = cdsapi.Client(
        url='https://cds.climate.copernicus.eu/api',
        key=cds_key
    )

    # ADS Client
    ads = cdsapi.Client(
        url='https://ads.atmosphere.copernicus.eu/api',
        key=ads_key
    )


    cds.retrieve(
        'reanalysis-era5-single-levels',
        {
            'product_type': 'reanalysis',
            'format': 'netcdf',
            'variable': [
                'surface_pressure',
                'total_column_water_vapour',
                'total_column_ozone',
                'total_cloud_cover',
            ],
            'date': date.strftime('%Y-%m-%d'),
            'time': round_to_nearest_hour(date).strftime('%-H:00'),
            'area': [lat+0.1, lon-0.1, lat-0.1, lon+0.1],  # small box around location
        },
        'era5_parameters.nc'
    )

    ds = xr.open_dataset("era5_parameters.nc")

    water_vapour = ds['tcwv'].values[0, 0, 0]  
    pressure = ds['sp'].values[0, 0, 0]/100
    ozone = ds['tco3'].values[0, 0, 0]/2.1415e-5
    #cloud = ds['tcc'].values[0, 0, 0]

    ads.retrieve(
        'cams-global-reanalysis-eac4',
        {
            'variable': [
                'total_aerosol_optical_depth_469nm',
                'total_aerosol_optical_depth_550nm',
                'total_aerosol_optical_depth_670nm',
                'total_aerosol_optical_depth_865nm',
                'total_aerosol_optical_depth_1240nm',
            ],
            'date': date.strftime('%Y-%m-%d'),
            'time': round_to_nearest_3hour(date).strftime('%H:00'),
            'format': 'netcdf',
            'type': 'analysis',
            'area': [lat + 0.1, lon - 0.1, lat - 0.1, lon + 0.1],
        },
        'cams_aerosols.nc'
    )
    ds = xr.open_dataset("cams_aerosols.nc")

    # Extract wavelengths and corresponding variable names
    wavelength_dict = {
        469: 'aod469',
        550: 'aod550',
        670: 'aod670',
        865: 'aod865',
        1240: 'aod1240'
    }

    # Extract available AODs
    wavelengths = []
    aods = []

    for wl, var in wavelength_dict.items():
        if var in ds:
            aod = ds[var].mean().item()
            if aod > 0:
                wavelengths.append(wl)
                aods.append(aod)

    wavelengths = np.array(wavelengths)
    aods = np.array(aods)

    # Fit Angstrom exponent
    log_wavelengths = np.log(wavelengths)
    log_aods = np.log(aods)
    slope, intercept = np.polyfit(log_wavelengths, log_aods, 1)
    angstrom_exponent = -slope

    # Interpolate AOD at 500nm
    aer_lambda0 = 500  # nm
    log_aod_500 = slope * np.log(aer_lambda0) + intercept
    aod_500 = np.exp(log_aod_500)

    return water_vapour, ozone, pressure, aod_500, angstrom_exponent
