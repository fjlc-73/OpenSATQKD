from external.cascade.key import Key
from external.cascade.reconciliation import Reconciliation
from external.cascade.mock_classical_channel import MockClassicalChannel
from typing import Tuple

def cascade(
    alice_bitstring: str,
    bob_bitstring: str,
    estimated_qber: float,
    protocol: str
) -> Tuple[Key, float, int, int]:
    """
    Perform information reconciliation using the specified cascade variant (e.g., original, biconf, etc).

    Args:
        alice_bitstring (str): Alice's key.
        bob_bitstring (str): Bob's key.
        estimated_qber (float): Estimated Quantum Bit Error Rate.
        protocol (str): Name of the cascade protocol variant to use.

    Returns:
        Tuple[Key, float, int, int]: A tuple containing:
            - reconciled_key (Key): The corrected key shared between Alice and Bob.
            - efficiency (float): Efficiency of the reconciliation process.
            - ask_parity_bits (int): Number of parity bits Alice sends.
            - reply_parity_bits (int): Number of parity bits Bob replies with.
    """
    try:
        alice_key = Key(bitstring=alice_bitstring)
        bob_key = Key(bitstring=bob_bitstring)

        channel = MockClassicalChannel(alice_key)
        reconciliation = Reconciliation(protocol, channel, bob_key, estimated_qber)

        reconciled_key = reconciliation.reconcile()

        return (
            reconciled_key,
            reconciliation.stats.efficiency,
            reconciliation.stats.ask_parity_bits,
            reconciliation.stats.reply_parity_bits
        )
    
    except Exception as e:
        raise RuntimeError(f"[Cascade Error] Failed to reconcile keys: {e}")


