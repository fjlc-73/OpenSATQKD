import matlab.engine

def bb84_key_rate(
    ec_efficiency: float,
    depolarization_error: float,
    transmittance: float,
    percentage_for_qber: float,
    photons: int
) -> float:
    """
    Compute the key rate for the BB84 protocol using openQKSsecurity's Solver.

    Args:
        ec_efficiency (float): Error correction efficiency (e.g., 1.15).
        depolarization_error (float): Depolarization probability (0–1).
        transmittance (float): Overall optical channel transmittance.
        percentage_for_qber (float): Fraction of photons used for QBER estimation.
        photons (int): Total number of signals sent (photons).

    Returns:
        float: The secret key rate computed by the solver.
    """
    eng = matlab.engine.start_matlab()
    
    try:
        # Initialize QKD input object
        eng.eval("qkdInput = QKDSolverInput();", nargout=0)

        # Add fixed parameters
        parameters = {
            "misalignmentAngle": 0,
            "pz": 0.5,
            "transmittance": transmittance,
            "fEC": ec_efficiency,
            "depolarization": depolarization_error,
            "alphabetSize": 2,
            "epsilonPE": 0.25e-9,
            "epsilonPA": 0.25e-9,
            "epsilonEC": 0.25e-9,
            "epsilonBar": 0.25e-9,
            "numSignals": photons,
            "pTest": percentage_for_qber,
            "tExp": -7
        }

        for param, val in parameters.items():
            eng.eval(f"qkdInput.addFixedParameter('{param}', {val});", nargout=0)

        # Attach modules
        eng.eval("qkdInput.setDescriptionModule(QKDDescriptionModule(@BasicBB84LossyDescriptionFunc));", nargout=0)
        eng.eval("qkdInput.setChannelModule(QKDChannelModule(@BasicBB84LossyChannelFunc));", nargout=0)
        eng.eval("qkdInput.setKeyRateModule(QKDKeyRateModule(@BasicKeyRateFunc));", nargout=0)
        eng.eval("qkdInput.setOptimizerModule(QKDOptimizerModule(@coordinateDescentFunc, struct('verboseLevel',0)));", nargout=0)
        eng.eval("qkdInput.setMathSolverModule(QKDMathSolverModule(@FW2StepSolver, struct('initMethod', 1, 'maxIter', 10, 'maxGap', 1e-6, 'blockDiagonal', true)));", nargout=0)
        eng.eval('qkdInput.setGlobalOptions(struct("errorHandling", 3, "verboseLevel", 0, "cvxSolver", "SDPT3", "cvxPrecision", "high"));', nargout=0)

        # Run solver
        eng.eval("results = MainIteration(qkdInput);", nargout=0)
        key_rate = float(eng.eval("results.keyRate;"))

        return key_rate

    except Exception as e:
        raise RuntimeError(f"Failed to compute key rate: {e}")

    finally:
        eng.quit()



def decoy_key_rate(
    ec_efficiency: float,
    depolarization_error: float,
    transmittance: float,
    percentage_for_qber: float,
    photons: int,
    dark_rate: float,
    signal_intensity: float,
    decoy_intensity: float
) -> float:
    """
    Compute the key rate for BB84 with decoy states using openQKSsecurity's Solver.

    Args:
        ec_efficiency (float): Error correction efficiency (e.g. 1.15).
        depolarization_error (float): Depolarization probability.
        transmittance (float): Overall optical channel transmittance.
        percentage_for_qber (float): Fraction of photons used for QBER estimation.
        photons (int): Total number of signals sent (photons).
        dark_rate (float): Dark count probability.
        signal_intensity (float): Intensity of the signal state.
        decoy_intensity (float): Intensity of the decoy state.

    Returns:
        float: The secret key rate computed by the solver.
    """
    eng = matlab.engine.start_matlab()

    try:
        eng.eval("qkdInput = QKDSolverInput();", nargout=0)

        # Set fixed parameters
        params = {
            "misalignmentAngle": 0,
            "pz": 0.5,
            "transmittance": transmittance,
            "fEC": ec_efficiency,
            "depolarization": depolarization_error,
            "alphabetSize": 2,
            "epsilonPE": 0.25e-9,
            "epsilonPA": 0.25e-9,
            "epsilonEC": 0.25e-9,
            "epsilonBar": 0.25e-9,
            "numSignals": photons,
            "pTest": percentage_for_qber,
            "tExp": -7,
            "darkCountRate": dark_rate,
            "GROUP_decoys_1": signal_intensity,
            "GROUP_decoys_2": decoy_intensity,
            "GROUP_decoys_3": 0.001  # vacuum decoy
        }

        for param, value in params.items():
            eng.eval(f"qkdInput.addFixedParameter('{param}', {value});", nargout=0)

        # Description and channel modules
        eng.eval("qkdInput.setDescriptionModule(QKDDescriptionModule(@BasicBB84LossyDescriptionFunc));", nargout=0)
        eng.eval("qkdInput.setChannelModule(QKDChannelModule(@BasicBB84WCPDecoyChannelFunc));", nargout=0)

        # Key rate module with options
        eng.eval('keyRateOptions = struct("decoyTolerance", 1e-14, "decoySolver", "SDPT3", "decoyForceSep", true);', nargout=0)
        eng.eval("qkdInput.setKeyRateModule(QKDKeyRateModule(@BasicBB84WCPDecoyKeyRateFunc, keyRateOptions));", nargout=0)

        # Optimizer and solver
        eng.eval("qkdInput.setOptimizerModule(QKDOptimizerModule(@coordinateDescentFunc, struct('verboseLevel',0)));", nargout=0)
        eng.eval("solverOpts = struct('initMethod', 1, 'maxIter', 10, 'maxGap', 1e-6, 'blockDiagonal', true);", nargout=0)
        eng.eval("qkdInput.setMathSolverModule(QKDMathSolverModule(@FW2StepSolver, solverOpts));", nargout=0)

        # Global solver options
        eng.eval('qkdInput.setGlobalOptions(struct("errorHandling", ErrorHandling.CatchWarn, "verboseLevel", 0, "cvxSolver", "SDPT3"));', nargout=0)

        # Run the solver and retrieve result
        eng.eval("results = MainIteration(qkdInput);", nargout=0)
        key_rate = float(eng.eval("results.keyRate;"))

        return key_rate

    except Exception as e:
        raise RuntimeError(f"Failed to compute decoy key rate: {e}")

    finally:
        eng.quit()

