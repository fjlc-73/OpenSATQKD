import datetime
import logging
import numpy as np
import math
import time
import matplotlib.pyplot as plt

from utils.satellite_passes import predict_pass, pass_details, keep_percentage_symmetrically
from utils.transmittance import atmospheric_transmittance, geometric_eff, scintillation_loss, pointing_loss
from utils.qkd_protocols import parallel_bb84_simulation, parallel_decoy_simulation, get_mismatched_indices, discard_bits
from utils.parameter_estimation import randomly_select_bits, calculate_qber
from utils.error_correction import cascade
from utils.privacy_amplification import circulant, circulant_seed, toeplitz, toeplitz_seed
from utils.key_rate import bb84_key_rate, decoy_key_rate
from utils.weather import classify_climate

def run_qkd_simulation(config):
    start_time = time.time()
    total_uplink_data = 0
    total_downlink_data = 0
    int_size_bits = 32
    float_size_bits = 32
    pass_end = None


    date_start = datetime.datetime.strptime(config["date_start"], "%d/%m/%Y %H:%M:%S")
    date_start = date_start.replace(tzinfo=datetime.timezone.utc)


    pass_start, _ , _ = predict_pass(
        "Alice",
        config["ground_latitude"],
        config["ground_longitude"],
        config["ground_altitude"],
        config["satellite_tle"],
        config["min_elevation_angle_start"],
        date_start,
    )

    _ , pass_end , _ = predict_pass(
        "Alice",
        config["ground_latitude"],
        config["ground_longitude"],
        config["ground_altitude"],
        config["satellite_tle"],
        config["min_elevation_angle_end"],
        date_start,
    )

    time_quantum_comm = (pass_end - pass_start).total_seconds()

    

    range_km, elevation, satlat, satlon = pass_details(
        "Alice",
        config["ground_latitude"],
        config["ground_longitude"],
        config["ground_altitude"],
        config["satellite_tle"],
        pass_start,
        int(time_quantum_comm),
    )

    if config["limit_option"]=="qkd_time":
        time_quantum_comm = time_quantum_comm*config["qkd_time"]
        range_km = keep_percentage_symmetrically(range_km, config["qkd_time"])
        elevation = keep_percentage_symmetrically(elevation, config["qkd_time"])
        satlat = keep_percentage_symmetrically(satlat, config["qkd_time"])
        satlon = keep_percentage_symmetrically(satlon, config["qkd_time"])
    else:
        mask = range_km <= config["max_range"]  
        range_km = range_km[mask]
        elevation = elevation[mask]
        satlat = satlat[mask]
        satlon = satlon[mask]
        time_quantum_comm = len(range_km)
 
    total_pulses_sent = config["weak_coherent_pulse_rate"] * 1e6 * int(time_quantum_comm)
    if config["qkd_protocol"] == "decoy_state":
        total_photons_sent = int(total_pulses_sent * (
            config["signal_prob"] * (1 - math.exp(-config["signal_mean_photon_num"]))
        ))
    else:
        total_photons_sent = total_pulses_sent
    real_photon_rate = total_photons_sent / int(time_quantum_comm)

    zenith = 90 - elevation

    
    yield f"""
==============================
◎ SATELLITE PASS DETAILS
==============================
• Start Time     : {pass_start.strftime('%d/%m/%Y %H:%M:%S')}
• End Time       : {pass_end.strftime('%d/%m/%Y %H:%M:%S')}
• Quantum Comm Time   : {time_quantum_comm:.2f} s
• Max Elevation: {max(elevation):.2f}°
• Shortest Slant Range: {min(range_km):,.2f} km
"""

    if config["weather_auto"]:
        climate = classify_climate(config["ground_latitude"], config["ground_longitude"], pass_start, config["ground_altitude"])
    else:
        climate = config["climate_model"]

    logging.disable(logging.CRITICAL)
    cloud = config["cloud_depth"]
    if config["weather_auto"]:
        water_vapour, ozone, pressure, aod_500 = None, None, None, None
    else:
        water_vapour = config["precipitable_water"]
        ozone = config["ozone_depth"]
        pressure = config["ground_pressure"]
        aod_500 = config["aerosol_depth"]
    atmos_transmit = atmospheric_transmittance(config["weather_auto"],climate, pass_start,config["ground_latitude"], config["ground_longitude"], config["ground_altitude"]/1000, config["photon_wavelength"], zenith, water_vapour, ozone, pressure, aod_500, cloud)
    logging.disable(logging.NOTSET)

    geometric_transmit = np.array([
        geometric_eff(
            config["receiving_telescope_aperture"],
            config["sending_telescope_aperture"],
            config["beam_divergence"],
            slant
        ) for slant in range_km
    ])
    scintillation_transmit = np.array([
        scintillation_loss(config["photon_wavelength"] * 1e-9, config["receiving_telescope_aperture"], angle, min(config["min_elevation_angle_start"],config["min_elevation_angle_end"]), config["ground_altitude"])
        for angle in elevation
    ])
    
    pointing_transmit = np.array([
        pointing_loss(
            config["beam_divergence"],
            config["point_acc_min"],
            config["point_acc_max"],
            z    
        )
        for z in zenith
    ])
    photons_reach_detector_per_sec = real_photon_rate * atmos_transmit * geometric_transmit * scintillation_transmit * pointing_transmit * config["detector_efficiency"] * config["optical_efficiency"]
    photons_measured_per_sec = np.minimum(config["detector_maximum_count_rate"] * 1e6, photons_reach_detector_per_sec)


    yield ("sat_coords", satlat, satlon, elevation, range_km, photons_measured_per_sec)
    total_photons_arrived = int(np.sum(photons_measured_per_sec))
    
    avg_transmittance = np.mean(geometric_transmit * scintillation_transmit * atmos_transmit * pointing_transmit* config["detector_efficiency"]) * config["optical_efficiency"]
    
    shots = 1 if total_photons_arrived < 1e6 else 10 ** (math.floor(math.log10(total_photons_arrived)) - 5)


    if config["qkd_protocol"] == "decoy_state":
        num_dark_counts = int(config["dark_count_rate"] * total_pulses_sent * config["time_window"] * 1e-9)
        total_photons_arrived += num_dark_counts

    yield f"""
==============================
* PHOTON TRANSMISSION STATS
==============================
• Total Signal States Sent     : {total_photons_sent:,.0f}
• Geometric Avg Loss     : {-10 * math.log10(np.mean(geometric_transmit)):.2f} dB
• Atmospheric Avg Loss    : {-10 * math.log10(np.mean(atmos_transmit)):.2f} dB
• Scintillation Avg Loss   : {-10 * math.log10(np.mean(scintillation_transmit)):.2f} dB
• Pointing Avg Loss   : {-10 * math.log10(np.mean(pointing_transmit)):.2f} dB
• Total Avg Channel Loss    : {-10 * math.log10(avg_transmittance):.2f} dB
• Detected Signal Photons: {total_photons_arrived:,.0f}
"""

    if config["qkd_protocol"] == "decoy_state":
        alice_bitstring, alice_bases, bob_bases, bob_bitstring = parallel_decoy_simulation(500, total_photons_arrived // (500 * shots), config["depolarization_error"], num_dark_counts, shots)
    else:
        alice_bitstring, alice_bases, bob_bases, bob_bitstring = parallel_bb84_simulation(total_photons_arrived // (500 * shots), config["depolarization_error"], shots)

    
    mismatched_indices = get_mismatched_indices(alice_bases, bob_bases)
    alice_bitstring = discard_bits(alice_bitstring, mismatched_indices)
    bob_bitstring = discard_bits(bob_bitstring, mismatched_indices)
    sifted_key_length = len(alice_bitstring)
    
    yield f"""
==============================
# BASIS RECONCILIATION
==============================
• Mismatched Bases     : {np.size(mismatched_indices):,}
• Sifted Key Length    : {sifted_key_length:,} bits
"""

    total_uplink_data += len(alice_bases)
    total_downlink_data += len(mismatched_indices) * int_size_bits

    string_to_estimate_qber, indices_to_estimate_qber = randomly_select_bits(alice_bitstring, config["percentage_estimate_qber"])
    estimated_qber = calculate_qber(''.join([bob_bitstring[i] for i in indices_to_estimate_qber]), indices_to_estimate_qber, string_to_estimate_qber)

    alice_bitstring = discard_bits(alice_bitstring, indices_to_estimate_qber)
    bob_bitstring = discard_bits(bob_bitstring, indices_to_estimate_qber)

    total_downlink_data += len(string_to_estimate_qber)
    total_downlink_data += len(indices_to_estimate_qber) * int_size_bits
    total_uplink_data += float_size_bits
    
    yield f"""
==============================
≈ QBER ESTIMATION
==============================
• Estimated QBER       : {estimated_qber:.4%}
• Bits Used for QBER   : {len(string_to_estimate_qber):,} bits
• Sifted Key (Post-QBER): {len(alice_bitstring):,} bits
"""
    

    reconciled_key, efficiency, ask_bits, reply_bits = cascade(alice_bitstring, bob_bitstring, estimated_qber, config["cascade"])
    


    efficiency = max(efficiency, 1)

    reconciled_key = [int(bit) for bit in str(reconciled_key)]

    total_downlink_data += ask_bits
    total_uplink_data += reply_bits

    compare_hash_length = math.ceil(math.log(1 / ((1/4)*1e-10)))

    if config["two_universal"] == "toeplitz":
        seed_val = toeplitz_seed(reconciled_key, compare_hash_length)
        compare_key = toeplitz(reconciled_key, compare_hash_length, seed_val) == toeplitz(alice_bitstring, compare_hash_length, seed_val)
    else:
        seed_val = circulant_seed(reconciled_key)
        compare_key = circulant(reconciled_key, compare_hash_length, seed_val) == circulant(alice_bitstring, compare_hash_length, seed_val)
   

    total_downlink_data += len(seed_val)
     
    if not compare_key:
        raise RuntimeError("Protocol aborted: error correction verification failed")
    
    yield f"""
==============================
⇆ ERROR CORRECTION
==============================
• Error Correction Success: ✔
• Cascade Variant Used : {config["cascade"].capitalize()}
• Efficiency             : {efficiency:.2f}
"""
    
    if config["qkd_protocol"] == "decoy_state":
        safe_key_perc = decoy_key_rate(
            efficiency,
            estimated_qber,
            avg_transmittance,
            config["percentage_estimate_qber"],
            total_photons_sent,
            1 - math.exp(-config["dark_count_rate"] * config["time_window"] * 1e-9),
            config["signal_mean_photon_num"],
            config["decoy_mean_photon_num"]
        )
    else:
        safe_key_perc = bb84_key_rate(efficiency, estimated_qber, avg_transmittance, config["percentage_estimate_qber"], total_photons_sent)
    
    sifted_key_rate = sifted_key_length / (time_quantum_comm * 1000)

    time_needed_classical_comm = total_uplink_data / (config["uplink_bandwidth"] * 1e6) + total_downlink_data / (config["downlink_bandwidth"] * 1e6)
    
    yield f"""
==============================
✪ FINAL RESULTS
==============================
• Avg Sifted Key Rate       : {sifted_key_rate:.2f} kHz
• Secure Key            : {safe_key_perc * total_photons_sent:,.0f} bits
• Total Uplink Bits     : {total_uplink_data:,}
• Total Downlink Bits   : {total_downlink_data:,}
• Estimated Classical Comm Time   : {time_needed_classical_comm:.2f} seconds
• Simulation Time       : {(time.time()-start_time)/60:.2f} minutes
"""

    yield "\n✔ **QKD Simulation Complete**"
    
if __name__ == "__main__":
    print("This script is not meant to be run directly. Run main.py")


