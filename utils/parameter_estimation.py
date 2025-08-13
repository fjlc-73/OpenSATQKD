import random
from typing import List, Tuple

def randomly_select_bits(bitstring: str, percentage: float) -> Tuple[str, List[int]]:
    """Randomly selects a given percentage of bits from the bitstring.
    
    Parameters:
        bitstring (str): The original bitstring.
        percentage (float): The percentage of bits to select (0 to 1).
    
    Returns:
        Tuple[str, List[int]]: The selected bitstring and the indices of selected bits.
    """
    # Ensure at least 1 bit is selected and calculate number of bits to select
    num_bits_to_select = max(1, int(len(bitstring) * percentage))  
    chosen_indices = sorted(random.sample(range(len(bitstring)), num_bits_to_select))  # Randomly pick indices
    
    # Get the selected bits from the bitstring based on chosen indices
    selected_bits = ''.join(bitstring[i] for i in chosen_indices)  
    
    return selected_bits, chosen_indices

def calculate_qber(
    alice_selected_bitstring: str,
    chosen_indices: List[int],
    bob_selected_bitstring: str,
    verbose: bool = False
) -> float:
    """
    Calculate the Quantum Bit Error Rate (QBER).

    Parameters:
        alice_selected_bitstring (str): Bits from Alice used for comparison.
        chosen_indices (List[int]): Indices of the bits compared.
        bob_selected_bitstring (str): Corresponding bits from Bob.
        verbose (bool): If True, print comparison details.

    Returns:
        float: The QBER (fraction of mismatched bits).
    """
    if len(alice_selected_bitstring) != len(bob_selected_bitstring):
        raise ValueError("Bitstrings must be of the same length.")

    if not alice_selected_bitstring:
        return 0.0  # or raise an exception if QBER is undefined for empty input

    if verbose:
        print("\n📊 Partial Key Comparison:")
        print("══════════════════════════════════════════════════")
        print(f"{'Index':<6} {'Ground':<8} {'Satellite':<8} {'Match'}")
        print("-" * 32)
        for i, (a, b) in enumerate(zip(alice_selected_bitstring, bob_selected_bitstring)):
            match_symbol = '✔' if a == b else '❌'
            print(f"{chosen_indices[i]:<6} {a:<8} {b:<8} {match_symbol}")

    errors = sum(1 for a, b in zip(alice_selected_bitstring, bob_selected_bitstring) if a != b)
    return errors / len(alice_selected_bitstring)