import socket
import config_educ
import pickle
from utils.qkd_protocols import random_base_string, random_bitstring, encode, discard_bits, get_mismatched_indices
from utils.parameter_estimation import calculate_qber

# Configuration
host = '127.0.0.1'
port = 11555
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = (host, port)

def receive_data():
    try:
        data, address = client_socket.recvfrom(4096)
        return data.decode('utf-8'), address
    except Exception as e:
        print(f"[{e}] Did you run Ground Station Script first?")
        exit(1)

# ────────────────────────────────
print("\n📡 SATELLITE: Initiating communication with the ground station...")
client_socket.sendto("I want to send you photons".encode('utf-8'), server_address)
client_socket.settimeout(1) 

data, server_address = receive_data()
print(f"\n🌍 GROUND STATION: {data}")

# ────────────────────────────────
print("\n🚀 SENDING PHOTONS")
print("--------------------------------------------------")
satellite_bases = random_base_string(config_educ.PHOTON_COUNT)
satellite_bitstring = random_bitstring(config_educ.PHOTON_COUNT)
circuit = encode(satellite_bitstring, satellite_bases, verbose=True)

with open("queue.pkl", "wb") as f:
    pickle.dump(circuit, f)

client_socket.sendto("All photons sent".encode('utf-8'), server_address)
print("\n📤 SATELLITE -> GROUND STATION: All photons sent.")
print(f"\n🗝️ SATELLITE bitstring: {satellite_bitstring}")

# ────────────────────────────────
print("\n🔍 SIFTING STEP")
print("--------------------------------------------------")
data, server_address = receive_data()
print("\n📥 GROUND STATION -> SATELLITE: Received measurement bases.")

mismatched_indices = get_mismatched_indices(data, satellite_bases, verbose=True)
indices_str = ', '.join(map(str, mismatched_indices))
client_socket.sendto(indices_str.encode('utf-8'), server_address)
print(f"\n📤 SATELLITE -> GROUND STATION: Mismatched basis indices: {indices_str}")

satellite_bitstring = discard_bits(satellite_bitstring, mismatched_indices)
print(f"\n✅ Sifted SATELLITE bitstring: {satellite_bitstring}")

# ────────────────────────────────
print("\n📊 PARAMETER ESTIMATION STEP")
print("--------------------------------------------------")
data, server_address = receive_data()
print("\n📥 GROUND STATION -> SATELLITE: Received random bits for QBER estimation.")

data2, server_address = receive_data()
print("\n📥 GROUND STATION -> SATELLITE: Received corresponding indices.")

indices_to_estimate_qber = list(map(int, data2.split(', ')))
qber = calculate_qber(''.join([satellite_bitstring[i] for i in indices_to_estimate_qber]), indices_to_estimate_qber, data, verbose=True)

client_socket.sendto(str(qber).encode('utf-8'), server_address)
print(f"\n📤 SATELLITE -> GROUND STATION: Estimated QBER = {qber:.4f}")

# Remove revealed bits
print("\n✂️  Removing revealed bits for final key generation...")
indices_to_remove = set(indices_to_estimate_qber)
satellite_bitstring = ''.join(bit for i, bit in enumerate(satellite_bitstring) if i not in indices_to_remove)

# Final Key
print("\n🔐 FINAL SECRET KEY (SATELLITE SIDE)")
print("--------------------------------------------------")
print(f"\n🗝️  {satellite_bitstring}")
