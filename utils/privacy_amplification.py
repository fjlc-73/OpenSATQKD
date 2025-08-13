from random import randint
from cryptomite import Circulant
from cryptomite import Toeplitz
from cryptomite.utils import next_prime
from typing import List

def toeplitz(alice_bitstring: str, output_length: int, seed: List[int]) -> List[int]:
    """
    Applies Toeplitz two universal hash function to extract a secure key from Alice's bitstring.

    Args:
        alice_bitstring (str): The original bitstring from Alice (e.g., "011010").
        output_length (int): Desired length of the extracted key.
        seed (List[int]): Seed used to generate the Toeplitz matrix.

    Returns:
        List[int]: Extracted secure key as a list of bits.
    """
    bit_input = [int(bit) for bit in alice_bitstring]

    hash_function = Toeplitz(len(bit_input), output_length)
    return hash_function.extract(bit_input, seed)


def circulant(alice_bitstring: str, output_length: int, seed: List[int]) -> List[int]:
    """
    Applies Circulant two universal hash function to extract a secure key from Alice's bitstring.

    Args:
        alice_bitstring (str): The original bitstring from Alice (e.g., "011010").
        output_length (int): Desired length of the extracted key.
        seed (List[int]): Seed used to generate the Circulant matrix.

    Returns:
        List[int]: Extracted secure key as a list of bits.
    """
    seed_bits = [int(b) for b in seed] if isinstance(seed, str) else seed
    seed_length = len(seed_bits)
    key_length = len(alice_bitstring)

    # Pad Alice's bitstring with '0's if it's shorter than required
    if seed_length > key_length + 1:
        padding_length = seed_length - key_length - 1
        alice_bitstring += '0' * padding_length

    input_bits = [int(bit) for bit in alice_bitstring]
    hash_function = Circulant(seed_length - 1, output_length)
    
    return hash_function.extract(input_bits, seed_bits)

def toeplitz_seed(alice_bitstring: str, output_length: int) -> List[int]:
    """
    Generates a random seed for Toeplitz two universal hash function.

    Args:
        alice_bitstring (str): Input bitstring from Alice.
        output_length (int): Desired output length of the hashed key.

    Returns:
        List[int]: A random binary seed of length (input_len + output_len - 1).
    """
    seed_length = len(alice_bitstring) + output_length - 1
    return [randint(0, 1) for _ in range(seed_length)]


def circulant_seed(alice_bitstring: str) -> List[int]:
    """
    Generates a random seed for Circulant two universal hash function.

    Args:
        alice_bitstring (str): Input bitstring from Alice.

    Returns:
        List[int]: A random binary seed of length equal to the next prime after len(alice_bitstring) + 1.
    """
    seed_length = next_prime(len(alice_bitstring) + 1)
    return [randint(0, 1) for _ in range(seed_length)]


def toeplitz_seed(alice_bitstring, output_length):
   return [randint(0, 1) for _ in range(len(alice_bitstring)+output_length-1)]
 
def circulant_seed(alice_bitstring):
   return [randint(0, 1) for _ in range(next_prime(len(alice_bitstring) + 1))]

 
