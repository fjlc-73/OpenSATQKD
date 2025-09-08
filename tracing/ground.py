import socket
import os
import config_educ
import pickle
from utils.qkd_protocols import random_base_string, measure, discard_bits
from utils.parameter_estimation import randomly_select_bits
from qiskit_aer.noise import NoiseModel, depolarizing_error

# Configuration
host = '0.0.0.0'
port = 11555
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = (host, port)
server_socket.bind(server_address)

# Helper function to receive data from the satellite
def receive_data():
    """Receives data from the satellite and handles potential errors."""
    try:
        data, client_address = server_socket.recvfrom(4096)
        return data.decode('utf-8'), client_address
    except Exception as e:
        print(f"[ERROR] Failed to receive data: {e}")
        return None, None

# ────────────────────────────────
print("\n🌍 GROUND STATION: Waiting for satellite communication...")
datos, client_address = receive_data()
server_socket.sendto("Ready to receive photons".encode('utf-8'), client_address)
print("\n📡 GROUND STATION: Ready to receive photons!")

# ────────────────────────────────
print("\n🚀 RECEIVING PHOTONS")
print("--------------------------------------------------")
ground_bases = random_base_string(config_educ.PHOTON_COUNT)

datos, client_address = receive_data()
print(f"\n📩 SATELLITE -> GROUND STATION: {datos}")

# Load the quantum circuit
with open("queue.pkl", "rb") as f:
    circuit = pickle.load(f)

# Add depolarizing noise model
noise_model = NoiseModel()
error = depolarizing_error(config_educ.DEPOLARIZATION_ERROR, 1)
noise_model.add_all_qubit_quantum_error(error, ["h", "x"])

# Measure circuit with noise
ground_bitstring = measure(circuit, ground_bases, noise_model, verbose=True)
os.remove("queue.pkl")

print(f"\n🗝️ GROUND STATION Bitstring: {ground_bitstring}")

# ────────────────────────────────
print("\n🔍 SIFTING STEP")
print("--------------------------------------------------")
server_socket.sendto(ground_bases.encode('utf-8'), client_address)

print(f"\n📤 GROUND STATION -> SATELLITE: Sent measurement bases")

datos, client_address = receive_data()
print("\n📩 SATELLITE -> GROUND STATION: Received mismatched indices.")

mismatched_indices = list(map(int, datos.split(', ')))
ground_bitstring = discard_bits(ground_bitstring, mismatched_indices)

print(f"\n✅ Sifted GROUND STATION Bitstring: {ground_bitstring}")

# ────────────────────────────────
print("\n📊 PARAMETER ESTIMATION STEP")
print("--------------------------------------------------")

string_to_estimate_qber, indices_to_estimate_qber = randomly_select_bits(ground_bitstring, config_educ.QBER_SAMPLE_PERCENTAGE)

server_socket.sendto(string_to_estimate_qber.encode('utf-8'), client_address)
print(f"\n📤 GROUND STATION -> SATELLITE: Sent random bits for QBER estimation:\n{string_to_estimate_qber}")

indices_str = ', '.join(map(str, indices_to_estimate_qber))
server_socket.sendto(indices_str.encode('utf-8'), client_address)
print(f"\n📤 GROUND STATION -> SATELLITE: Sent their corresponding indices:\n{indices_str}")

datos, client_address = receive_data()
qber = datos
print(f"\n📩 SATELLITE -> GROUND STATION: Estimated QBER = {qber}")

print("\n✂️  Removing revealed bits used in QBER estimation...")
indices_to_remove = set(indices_to_estimate_qber)
ground_bitstring = ''.join(bit for i, bit in enumerate(ground_bitstring) if i not in indices_to_remove)

# Final Key
print("\n🔐 FINAL SECRET KEY (GROUND STATION SIDE)")
print("--------------------------------------------------")
print(f"\n🗝️  {ground_bitstring}")
