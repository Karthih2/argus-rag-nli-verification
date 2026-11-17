"""Temperature scaling for NLI logits (spec 10.2)."""

import numpy as np
from scipy.optimize import minimize_scalar

T_BOUNDS = (0.1, 10.0)


def fit_temperature(logits: np.ndarray, labels: np.ndarray) -> float:
    """T that minimises the negative log-likelihood of the gold labels under softmax(logits / T)."""

    def nll(t: float) -> float:
        z = logits / t
        z = z - z.max(axis=1, keepdims=True)
        log_probs = z - np.log(np.exp(z).sum(axis=1, keepdims=True))
        return float(-log_probs[np.arange(len(labels)), labels].mean())

    return round(float(minimize_scalar(nll, bounds=T_BOUNDS, method="bounded").x), 4)
