"""
Configuration file for BB84 Quantum Key Distribution Simulation.
"""

# --- Simulation Parameters ---
PHOTON_COUNT = 50  # Total number of qubits (photons) sent in the simulation

# --- Noise Configuration ---
DEPOLARIZATION_ERROR = 0.2  # Depolarizing error rate as a percentage (0-1)

# --- QBER Evaluation ---
QBER_SAMPLE_PERCENTAGE = 0.5  # Percentage of bits randomly selected to compute QBER (e.g., 0.1 = 10%)

