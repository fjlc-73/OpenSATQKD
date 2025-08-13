import random
from typing import List, Tuple
import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import (
    NoiseModel,
    depolarizing_error,
)
import time
import multiprocessing
from itertools import chain
from concurrent.futures import ProcessPoolExecutor


BASE_CHOICES = ['Z', 'X']
BIT_CHOICES = ['0', '1']

def random_base_string(n: int) -> str:
    """Generate a random string of length n with measurement bases ('Z' or 'X')."""
    return ''.join(random.choices(BASE_CHOICES, k=n))

def random_bitstring(n: int) -> str:
    """Generate a random bitstring of length n composed of '0' and '1'."""
    return ''.join(random.choices(BIT_CHOICES, k=n))
    
def encode(bits: str, bases: str, verbose: bool = False) -> QuantumCircuit:
    """
    Encode a bitstring using the specified bases (Z or X) into a quantum circuit.

    Parameters:
        bits (str): The bitstring ('0' or '1') to encode.
        bases (str): The basis string ('Z' or 'X') for each bit.
        verbose (bool): If True, print detailed encoding steps.

    Returns:
        QuantumCircuit: The encoded quantum circuit.
    """
    if len(bits) != len(bases):
        raise ValueError("Bits and bases must be of the same length.")

    n = len(bits)
    qc = QuantumCircuit(n, n)
    
    if verbose:
        print("\n🚀 Photon Transmission:")
        print("═════════════════════════════════════════════════════════════════")
        print(f"{'Photon':<8} | {'Bit':<5} | {'Basis':<10} | {'Quantum State Sent'}")
        print("-" * 65)

    for i in range(n):
        bit = bits[i]
        basis = bases[i]

        if verbose:
            state = "|+⟩" if basis == 'X' and bit == '0' else "|−⟩" if basis == 'X' else "|1⟩" if bit == '1' else "|0⟩"
            print(f"{i + 1:<8} | {bit:<5} | {'Z (⊕)' if basis == 'Z' else 'X (⊗)':<10} | {state}")

        if bit == '1':
            qc.x(i)

        if basis == 'X':
            qc.h(i)

    return qc

def measure(
    alice_circuit: QuantumCircuit,
    bases: str,
    noise_model: NoiseModel,
    shots: int = 1,
    verbose: bool = False
) -> str:
    """
    Simulate Bob measuring qubits using the specified bases.

    Parameters:
        alice_circuit (QuantumCircuit): The quantum circuit from Alice.
        bases (str): Measurement bases for each qubit ('Z' or 'X').
        noise_model (NoiseModel): Qiskit noise model to simulate realistic conditions.
        shots (int): Number of measurement repetitions.
        verbose (bool): If True, prints detailed measurement process.

    Returns:
        str: Measured bitstring.
    """
    n = len(bases)
    bob_circuit = alice_circuit.copy()

    # Apply Hadamard gates for X-basis measurements
    for i in range(n):
        if bases[i] == 'X':
            bob_circuit.h(i)

    # Add measurement
    bob_circuit.measure(range(n), range(n))

    # Simulate with noise
    sim = AerSimulator(noise_model=noise_model)
    result = sim.run(bob_circuit, shots=shots, memory=True).result()
    memory = result.get_memory()  # List[str]

    # Reverse each bitstring to match qubit order
    measured_bits = ''.join(bit for bitstring in memory for bit in bitstring[::-1])

    if verbose:
        print("\n📊 Measurement Results:")
        print("══════════════════════════════════════════════════")
        print(f"{'Photon':<8} | {'Basis':<10} | {'Measured Bit'}")
        print("-" * 45)
        for i in range(n):
            basis_symbol = 'Z (⊕)' if bases[i] == 'Z' else 'X (⊗)'
            print(f"{i + 1:<8} | {basis_symbol:<10} | {measured_bits[i]}")
        print("══════════════════════════════════════════════════")


    return measured_bits

def simulate_bb84(N: int, error_rate: float, shots: int) -> Tuple[str, str, str, str]:
    """
    Simulate the BB84 quantum key distribution protocol.

    Args:
        N (int): Number of photons (qubits) sent.
        error_rate (float): Depolarizing error probability (0-1).
        shots (int): Number of simulation repetitions.

    Returns:
        Tuple[str, str, str, str]: 
            - Alice's bitstring,
            - Alice's basis choices,
            - Bob's basis choices,
            - Bob's bitstring.
    """
    # Generate random bases and bits for Alice and Bob
    alice_bases = random_base_string(N)
    bob_bases = random_base_string(N)    
    alice_bitstring = random_bitstring(N)

    # Create Alice's encoding circuit
    alice_circuit = encode(alice_bitstring, alice_bases)

    # Add depolarizing noise model to the circuit
    noise_model = NoiseModel()
    dep_error = depolarizing_error(error_rate, 1)
    noise_model.add_all_qubit_quantum_error(dep_error, ["h", "x"])

    # Simulate Bob's measurement
    bob_measurement_result = measure(alice_circuit, bob_bases, noise_model, shots)
    bob_bitstring = ''.join(bob_measurement_result)

    return alice_bitstring * shots, alice_bases * shots, bob_bases * shots, bob_bitstring

def parallel_bb84_simulation(repetitions: int, error: float, shots: int) -> Tuple[str, str, str, str]:
    """
    Run multiple BB84 simulations in parallel.

    Args:
        repetitions (int): Number of simulations to run.
        error (float): Depolarizing error rate.
        shots (int): Number of shots per simulation.

    Returns:
        Tuple[str, str, str, str]: 
            - Concatenated Alice bitstring,
            - Concatenated Alice basis string,
            - Concatenated Bob basis string,
            - Concatenated Bob bitstring.
    """
    num_processes = max(multiprocessing.cpu_count() // 2, 1)
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.starmap(simulate_bb84, [(500, error, shots)] * repetitions)

    alice_bitstring = ''.join(chain.from_iterable(result[0] for result in results))
    alice_bases = ''.join(chain.from_iterable(result[1] for result in results))
    bob_bases = ''.join(chain.from_iterable(result[2] for result in results))
    bob_bitstring = ''.join(chain.from_iterable(result[3] for result in results))

    return alice_bitstring, alice_bases, bob_bases, bob_bitstring


def parallel_decoy_simulation(
    circuit,
    repetitions: int, 
    error: float, 
    num_dark: int, 
    shots: int
) -> Tuple[str, str, str, str]:
    """
    Run BB84 simulations in parallel and inject dark counts.

    Args:
        repetitions (int): Number of simulation runs.
        error (float): Depolarizing error rate.
        num_dark (int): Number of dark count (false detections) to inject.
        shots (int): Number of shots per simulation.

    Returns:
        Tuple[str, str, str, str]: 
            - Combined Alice bitstring,
            - Combined Alice basis string,
            - Combined Bob basis string,
            - Combined Bob bitstring, including decoys.
    """
    with ProcessPoolExecutor() as executor:
        # Submit all jobs
        futures = [executor.submit(simulate_bb84, circuit, error, shots) for _ in range(repetitions)]
        
        # Gather results as they complete
        results = [f.result() for f in futures]

    # Flatten lists
    alice_bitstring = list(chain.from_iterable(result[0] for result in results))
    alice_bases = list(chain.from_iterable(result[1] for result in results))
    bob_bases = list(chain.from_iterable(result[2] for result in results))
    bob_bitstring = list(chain.from_iterable(result[3] for result in results))

    # Inject decoy (dark count) entries at random positions
    total_length = len(alice_bitstring)
    insert_indices = sorted(random.sample(range(total_length + num_dark), num_dark))

    for idx in reversed(insert_indices):  # Reverse for stable insert
        alice_bitstring.insert(idx, random.choice('01'))
        alice_bases.insert(idx, random.choice('XZ'))
        bob_bases.insert(idx, random.choice('XZ'))
        bob_bitstring.insert(idx, random.choice('01'))

    return ''.join(alice_bitstring), ''.join(alice_bases), ''.join(bob_bases), ''.join(bob_bitstring)


def get_mismatched_indices(alice_bases: str, bob_bases: str, verbose: bool = False) -> List[int]:
    """
    Identify indices where Alice and Bob used different measurement bases.

    Parameters:
        alice_bases (str): Alice's basis string (e.g., 'ZXXZ...').
        bob_bases (str): Bob's basis string (e.g., 'ZXZX...').
        verbose (bool): If True, print a comparison table.

    Returns:
        List[int]: Indices where the bases do not match.
    """
    if len(alice_bases) != len(bob_bases):
        raise ValueError("Alice's and Bob's basis strings must be of equal length.")

    mismatched = []

    if verbose:
        print("\n📊 Basis Comparison:")
        print("══════════════════════════════════════════════════")
        print(f"{'Index':<6} {'Ground':<8} {'Satellite':<8} {'Match'}")
        print("-" * 32)

    for i, (a, b) in enumerate(zip(alice_bases, bob_bases)):
        if a != b:
            mismatched.append(i)
        if verbose:
            match_symbol = '✔' if a == b else '❌'
            print(f"{i:<6} {a:<8} {b:<8} {match_symbol}")

    return mismatched

def discard_bits(bitstring: str, mismatched_indices: List[int]) -> str:
    """
    Remove bits from a bitstring at the specified mismatched indices.

    Parameters:
        bitstring (str): The original bitstring (e.g., '010110').
        mismatched_indices (List[int]): Indices to be discarded.

    Returns:
        str: A new bitstring with the mismatched bits removed.
    """
    mismatched_set = set(mismatched_indices)

    if not all(0 <= i < len(bitstring) for i in mismatched_set):
        raise ValueError("Mismatched indices contain out-of-range values.")

    return ''.join(bit for i, bit in enumerate(bitstring) if i not in mismatched_set)

def simulate_with_timeout(circuit, error, shots, repetitions, num_dark):
    """
    Simulate the BB84 protocol and inject decoy bits with timeout handling.
    
    This function is separated to be compatible with multiprocessing.
    """
    results = [simulate_bb84(circuit, error, shots) for _ in range(repetitions)]

    # Flatten lists
    alice_bitstring = list(chain.from_iterable(result[0] for result in results))
    alice_bases = list(chain.from_iterable(result[1] for result in results))
    bob_bases = list(chain.from_iterable(result[2] for result in results))
    bob_bitstring = list(chain.from_iterable(result[3] for result in results))

    # Inject decoy (dark count) entries at random positions
    total_length = len(alice_bitstring)
    insert_indices = sorted(random.sample(range(total_length + num_dark), num_dark))

    for idx in reversed(insert_indices):  # Reverse for stable insert
        alice_bitstring.insert(idx, random.choice('01'))
        alice_bases.insert(idx, random.choice('XZ'))
        bob_bases.insert(idx, random.choice('XZ'))
        bob_bitstring.insert(idx, random.choice('01'))

    return ''.join(alice_bitstring), ''.join(alice_bases), ''.join(bob_bases), ''.join(bob_bitstring)

def bench_parallel_decoy_simulation(
    circuit,
    repetitions: int, 
    error: float, 
    num_dark: int, 
    shots: int,
    timeout: int  # Timeout in seconds (default 5 minutes)
) -> Tuple[str, str, str, str]:
    """
    Run BB84 simulations in parallel and inject dark counts.

    Args:
        repetitions (int): Number of simulation runs.
        error (float): Depolarizing error rate.
        num_dark (int): Number of dark count (false detections) to inject.
        shots (int): Number of shots per simulation.
        timeout (int): Timeout duration in seconds (default 5 minutes).

    Returns:
        Tuple[str, str, str, str]: 
            - Combined Alice bitstring,
            - Combined Alice basis string,
            - Combined Bob basis string,
            - Combined Bob bitstring, including decoys.
    """
    

    pool = multiprocessing.Pool(processes=max(multiprocessing.cpu_count() // 2, 1))
    result = pool.apply_async(simulate_with_timeout, (circuit, error, shots, repetitions, num_dark))

    try:
        # Wait for result with timeout
        return result.get(timeout=timeout)  # This will raise TimeoutError if it exceeds the limit
    except multiprocessing.TimeoutError:
        print(f"Simulation exceeded the time limit of {timeout} seconds. Aborting.")
    finally:
        pool.close()
        pool.terminate()
        pool.join()
        return '', '', '', ''  # Return empty results to indicate failure



def benchmark_bb84():
    error = 0.01
    num_dark = 100
    qubits_target = 20_000_000
    trials = []

    # Set a 5-minute timeout for each test
    TIMEOUT_LIMIT = 300  # 5 minutes

    for circuit_size in [100, 200, 400, 600, 800, 1000, 1500, 2000, 3000, 5000]:
        for shots in [10, 50, 100, 250, 400, 750, 1000, 1500, 2000, 5000]:
            repetitions = qubits_target // (circuit_size * shots)
            if repetitions == 0:
                continue  # Skip invalid setups

            print(f"Testing: circuit_size={circuit_size}, shots={shots}, repetitions={repetitions}")
            start_time = time.time()

            try:
                # Run the simulation with the timeout
                result = bench_parallel_decoy_simulation(circuit_size, repetitions, error, num_dark, shots, timeout=TIMEOUT_LIMIT)


                duration = time.time() - start_time
                trials.append({
                    'circuit_size': circuit_size,
                    'shots': shots,
                    'repetitions': repetitions,
                    'time_seconds': duration
                })
                print(f"Completed in {duration:.2f} seconds\n")

            except Exception as e:
                print(f"Error during test with circuit_size={circuit_size}, shots={shots}: {e}")
                continue  # Skip if there's an error

    print("Benchmark results:")
    for t in sorted(trials, key=lambda x: x['time_seconds']):
        print(t)
        
if __name__ == "__main__":
    benchmark_bb84()
