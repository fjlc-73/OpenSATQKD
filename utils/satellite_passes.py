import datetime
from typing import Tuple
import numpy as np
from datetime import timedelta
from passpredict import Location, Observer, SGP4Propagator, TLE
from passpredict.observers import Observer

def predict_pass(
    observer_name: str,
    observer_lat: float,
    observer_long: float,
    observer_alt: float,
    two_line_element: str,
    min_elevation: float,
    date_start: datetime.datetime
) -> Tuple[datetime.datetime, datetime.datetime, float]:
    """
    Predict the next satellite pass for a given observer location and TLE data.

    Args:
        observer_name (str): Name of the observer location.
        observer_lat (float): Latitude of the observer in degrees.
        observer_long (float): Longitude of the observer in degrees.
        observer_alt (float): Altitude of the observer in meters.
        two_line_element (str): Satellite TLE string.
        min_elevation (float): Minimum elevation angle (degrees) for a valid pass.
        date_start (datetime): Start date and time to begin pass prediction.

    Returns:
        Tuple[datetime, datetime, float]: 
            - Acquisition of signal (AOS) time,
            - Loss of signal (LOS) time,
            - Duration of the pass in seconds.
    """
    location = Location(observer_name, observer_lat, observer_long, observer_alt)

    tle = TLE(0, two_line_element, "QKD")
    satellite = SGP4Propagator.from_tle(tle)
    observer = Observer(location, satellite)
    date_end = date_start + timedelta(days=1)



    overpass = observer.next_pass(
        date_start, 
        limit_date=date_end, 
        aos_at_dg=min_elevation, 
        tol=0.1, 
        visible_only=False,
        method='brute',
        time_step=5
    )

    aos_time = overpass.aos.dt
    los_time = aos_time + timedelta(seconds=overpass.duration)

    return aos_time, los_time, overpass.duration

def pass_details(
    observer_name: str,
    observer_lat: float,
    observer_long: float,
    observer_alt: float,
    two_line_element: str,
    pass_start: datetime.datetime,
    duration_comm: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute range and elevation data during a satellite pass.

    Args:
        observer_name (str): Name of the observer location.
        observer_lat (float): Latitude of the observer in degrees.
        observer_long (float): Longitude of the observer in degrees.
        observer_alt (float): Altitude of the observer in meters.
        two_line_element (str): TLE string (two lines concatenated or split).
        pass_start (datetime): Start time of satellite pass.
        duration_comm (int): Duration of the communication window in seconds.

    Returns:
        Tuple:
            - ranges (np.ndarray): Satellite ranges in km.
            - elevations (np.ndarray): Elevation angles in degrees.
            - latitudes (np.ndarray): Satellite latitudes during the pass.
            - longitudes (np.ndarray): Satellite longitudes during the pass.
    """
    tle = TLE(0, two_line_element, "QKD")
    satellite = SGP4Propagator.from_tle(tle)
    location = Location(observer_name, observer_lat, observer_long, observer_alt)
    observer = Observer(location, satellite)

    time_step = datetime.timedelta(seconds=1)
    satpos = satellite.get_position_detail(pass_start, duration_comm, time_step)

    ranges = []
    elevation = []
    longitude = satpos.longitude
    latitude = satpos.latitude
    
    for i in range(duration_comm):
        pt = observer.point(pass_start, visibility=True, aos_at_dg=0)
        ranges = ranges + [pt.range]
        elevation = elevation + [pt.elevation]
        pass_start = pass_start + time_step
    return (np.array(ranges, dtype=float), np.array(elevation, dtype=float), latitude, longitude)

def keep_percentage_symmetrically(arr, pct):
        k = int(round(len(arr) * pct))  # number of elements to keep
        to_remove = len(arr) - k
        left_remove = to_remove // 2
        right_remove = to_remove - left_remove

        return arr[left_remove : len(arr) - right_remove]
