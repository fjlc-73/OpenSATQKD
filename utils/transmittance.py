
import numpy as np
import math
from scipy.special import erfinv
from scipy.integrate import quad
from libradtranpy import libsimulateVisible
from concurrent.futures import ThreadPoolExecutor
import math

from utils.weather import obtain_atmospheric_parameters

def simulate_for_zenith(zenith, water_vapour, ozone, pressure, aod_500, angstrom_exponent, cloud, model, alt):
    wl, transm = libsimulateVisible.ProcessSimulation(
        zenith,
        water_vapour,
        ozone,
        pressure,
        aod_500,
        angstrom_exponent,
        model,
        'as',
        cloud,
        alt
    )
    return wl, transm

def atmospheric_transmittance(auto, model: str, date, lat, lon, alt, wav, zenith_arr, water_vapour, ozone, pressure, aod_500, cloud, angstrom_exponent=1.4) -> float:

    if auto:
        # Get atmospheric parameters once
        water_vapour, ozone, pressure, aod_500, angstrom_exponent = obtain_atmospheric_parameters(
            date, lat, lon
        )

    # Convert zenith angles to airmass (secant of zenith)
    airmass_arr = 1 / np.cos(np.deg2rad(zenith_arr))

    # Prepare arguments for parallel calls
    args = [(a, water_vapour, ozone, pressure, aod_500, angstrom_exponent, cloud, model, alt) for a in airmass_arr]

    with ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda p: simulate_for_zenith(*p), args))

    # Use the wl from first result for indexing wavelength
    wl_ref = results[0][0]
    index = np.argmin(np.abs(wl_ref - wav))

    # Extract transmittances at desired wavelength
    transmittances = [transm[index] for wl, transm in results]

    return np.array(transmittances)




def geometric_eff(rec_ap: float, send_ap: float, beam_div: float, range: float) -> float:
    """
    Calculate the geometric efficiency of a communication link between a transmitter and receiver.

    Parameters:
    - rec_ap (float): Receiver aperture diameter (in meters).
    - send_ap (float): Transmitter aperture diameter (in meters).
    - beam_div (float): Beam divergence (in radians).
    - range (float): Distance between transmitter and receiver (in kilometers).

    Returns:
    - float: Geometric efficiency of the system.
    """
    return (rec_ap / (send_ap + (beam_div * range * 1000))) ** 2

def pointing_error_rss(zenith_angle_deg, acc_min, acc_max):
    """
    Compute total pointing error (μrad) based on zenith angle (deg)
    using a smooth empirical model.
    """
    # Convert to radians
    z = np.radians(zenith_angle_deg)
    
    # Smooth ramp function
    f = np.sin(z) ** 2  # exponent = 2 for moderate roll-off

    # Total pointing error (RSS)
    theta_pointing = acc_min + (acc_max - acc_min) * f

    return theta_pointing*1e-6


def pointing_loss( beam_divergence: float, acc_min, acc_max, zenith) -> float:
    """
    Calculate the pointing loss of a communication link between a transmitter and receiver.

    Parameters:
    - pointing_accuracy (float): The pointing accuracy in radians.
    - beam_divergence (float): The full transmitting divergence angle in radians.

    Returns:
    - float: Pointing loss as a value between 0 and 1, where 1 means no loss.
    """
    perror = pointing_error_rss(zenith, acc_min, acc_max)
    ploss = math.exp(-2 * (perror/ (beam_divergence/2)) ** 2)
    return ploss


def cn2_hufnagel_valley(h: float, A0: float, H_OGS: float, v_wind: float = 21.0) -> float:
    """
    Calculate the refractive index structure constant \( C_n^2(h) \) at altitude \( h \) using the Hufnagel-Valley model.
    
    Parameters:
        h (float)      : Altitude at which \( C_n^2 \) is calculated [meters].
        A0 (float)     : Ground-level \( C_n^2 \) value [m^(-2/3)].
        H_OGS (float)  : Ground station altitude [meters].
        v_wind (float) : RMS wind speed [m/s] (default is 21 m/s).
    
    Returns:
        float: \( C_n^2(h) \) at altitude \( h \) [m^(-2/3)].
    """
    
    # Term 1: Height and ground station dependent
    term1 = A0 * np.exp((H_OGS - h) / 100) * np.exp(-H_OGS / 700)

    # Term 2: Wind speed dependent
    term2 = 5.49e-53 * (v_wind / 27)**2 * h**10 * np.exp(-h / 1000)

    # Term 3: Exponential decay with height
    term3 = 2.7e-16 * np.exp(-h / 1500)

    # Return the total value of C_n^2(h)
    return term1 + term2 + term3

def rytov_variance_hv(wavelength: float, H_OGS: float, H_Turb: float, zenith_angle_deg: float, A0: float, v_wind: float) -> float:
    """
    Calculate the Rytov variance using the Hufnagel-Valley model and numerical integration.

    The Rytov variance is used in the study of optical turbulence and provides a measure of 
    the strength of turbulence-induced variations in the optical wavefront.

    Parameters:
        wavelength (float)       : Optical wavelength [m].
        H_OGS (float)           : Ground station altitude [m].
        H_Turb (float)          : Turbulence layer top altitude [m].
        zenith_angle_deg (float): Zenith angle [degrees].
        A0 (float)              : Ground-level C_n^2 [m^(-2/3)].
        v_wind (float)          : RMS wind speed [m/s].

    Returns:
        float: Rytov variance (σ_R^2), dimensionless.
    """

    # Wave number
    k = 2 * np.pi / wavelength

    # Convert zenith angle to radians and calculate sec(zeta)
    zeta_rad = np.deg2rad(zenith_angle_deg)
    sec_zeta = 1 / np.cos(zeta_rad)
    
    # Define the integrand function: C_n^2(h) * (h - H_OGS)^(5/6)
    def integrand(h):
        if h <= H_OGS:
            return 0  # To avoid invalid values below the ground station altitude
        return cn2_hufnagel_valley(h, A0, H_OGS, v_wind) * (h - H_OGS)**(5/6)
    
    # Perform numerical integration from H_OGS to H_Turb
    integral, _ = quad(integrand, H_OGS, H_Turb)
    
    # Calculate Rytov variance
    sigma_R2 = 2.24 * k**(7/6) * sec_zeta**(11/6) * integral
    
    return sigma_R2

def intensity_scintillation_index(sigma_R_squared: float) -> float:
    """Calculate intensity scintillation index σ_I².

    Parameters:
        sigma_R_squared (float): Rytov variance (σ_R^2).

    Returns:
        float: Intensity scintillation index (σ_I^2).
    """
    # First term in the scintillation index calculation
    term1 = 0.49 * sigma_R_squared / (1 + 1.11 * np.sqrt(sigma_R_squared)**(12/5))**(7/6)
    
    # Second term in the scintillation index calculation
    term2 = 0.51 * sigma_R_squared / (1 + 0.69 * np.sqrt(sigma_R_squared)**(12/5))**(5/6)
    
    # Calculate and return the intensity scintillation index
    return np.exp(term1 + term2) - 1

def intensity_scale(wavelength:float, elevation_angle_deg:float, min_elevation_angle:float, turbulence_height:float=12000) -> float:
    """
    Calculate characteristic intensity scale (ρ_I) based on the wavelength, 
    turbulence layer height, and zenith angle.

    Parameters:
        wavelength (float): Wavelength of the optical signal in meters.
        turbulence_height (float): Height of the turbulence layer in meters.
        elevation_angle_deg (float): Zenith angle in degrees.

    Returns:
        float: Characteristic intensity scale ρ_I.
    """
    # Calculate denominator for intensity scale formula
    angle_factor = (elevation_angle_deg / 90) ** 2 + (min_elevation_angle / 90) ** 2
    
    # Compute characteristic intensity scale ρ_I
    rho_I = 1.5 * np.sqrt((wavelength / (2 * np.pi)) * (turbulence_height / angle_factor))
    
    return rho_I

def aperture_averaging_factor(aperture_diameter:float, rho_I:float) -> float:
    """
    Calculate the aperture averaging factor (A(D_r))

    Parameters:
        aperture_diameter (float): Aperture diameter in meters.
        rho_I (float): Characteristic intensity scale ρ_I in meters.

    Returns:
        float: Aperture averaging factor A(D_r).
    """
    # Compute the aperture averaging factor A(D_r)
    factor = 1 + 1.062 * (aperture_diameter / (2 * rho_I)) ** 2
    aperture_avg_factor = factor ** (-7 / 6)
    
    return aperture_avg_factor

def power_scintillation_index(wavelength:float, aperture_diameter:float, elevation_angle_deg:float, min_elevation_angle:float,
                               altitude_ground_station:float, turbulence_height:float=20000, 
                               wind_speed:float=21, cn2_ground_level:float=1.7e-14)->float:
    """
    Calculate the power scintillation index.

    Parameters:
        wavelength (float): Wavelength in meters (e.g., 1550 nm for optical communications).
        aperture_diameter (float): Aperture diameter of the receiver in meters.
        elevation_angle_deg (float): Zenith angle in degrees (the angle between the line of sight and the zenith).
        altitude_ground_station (float): Altitude of the ground station in meters.
        turbulence_height (float): Altitude of the turbulence layer in meters (default: 20,000 meters).
        wind_speed (float): RMS wind speed in m/s (default: 20 m/s).
        cn2_ground_level (float): Ground-level C_n^2 value in m^(-2/3) (default: 1.7e-14).

    Returns:
        float: Power scintillation index, which quantifies signal strength fluctuations.
    """
    # Step 1: Calculate Rytov variance (σ_R^2)
    sigma_R_squared = rytov_variance_hv(wavelength, altitude_ground_station, turbulence_height, 
                                        90 - elevation_angle_deg, cn2_ground_level, wind_speed)
    
    # Step 2: Calculate intensity scintillation index (σ_I^2) from Rytov variance
    sigma_I_squared = intensity_scintillation_index(sigma_R_squared)
    
    # Step 3: Calculate characteristic intensity scale (ρ_I)
    rho_I = intensity_scale(wavelength, elevation_angle_deg, min_elevation_angle)
    
    # Step 4: Calculate aperture averaging factor (A(D_r))
    aperture_avg_factor = aperture_averaging_factor(aperture_diameter, rho_I)
    
    # Step 5: Return power scintillation index (A(D_r) * σ_I^2)
    return aperture_avg_factor * sigma_I_squared

def scintillation_loss(wavelength:float, aperture:float, theta_deg:float, min_elevation_angle:float, altitude_ground_station:float, p0:float=0.01)->float:
    """
    Calculate the scintillation loss due to atmospheric turbulence.

    Parameters:
        wavelength (float): Wavelength in meters (e.g., 1550 nm for optical communications).
        aperture (float): Aperture diameter of the receiver in meters.
        theta_deg (float): Elevation angle in degrees.
        min_elevation_angle (float): Minimum elevation angle for communication (degrees)
        altitude_ground_station (float): Altitude of the ground station in meters.
        p0 (float, optional): Probability of a photon detection. Default is 0.01.

    Returns:
        float: Scintillation loss (dimensionless) in linear scale.
    """
    
    # Step 1: Calculate the power scintillation index
    sigma_P_squared = power_scintillation_index(wavelength, aperture, theta_deg, min_elevation_angle, altitude_ground_station)
    
    # Step 2: Calculate the terms needed for noise (scintillation loss calculation)
    term1 = erfinv(2 * p0 - 1) * np.sqrt(2 * np.log(sigma_P_squared + 1))
    term2 = 0.5 * np.log(sigma_P_squared + 1)
    
    # Step 3: Calculate the noise 
    noise = 4.343 * (term1 - term2)
    
    # Step 4: Return the scintillation loss in linear scale
    return 10**(noise / 10)


