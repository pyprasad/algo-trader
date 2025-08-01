# models/regime_model.py

import numpy as np
from hmmlearn.hmm import GaussianHMM

def detect_regime(price_series, n_states=3):
    """
    Detects market regime using a Hidden Markov Model (HMM).

    Parameters:
    - price_series: pd.Series of midprices (index = timestamp)
    - n_states: number of hidden states to model (default: 3)

    Returns:
    - str: regime label ("trending", "mean-reverting", or "volatile")
    """

    # 1. Compute log returns
    returns = np.log(price_series / price_series.shift(1)).dropna().values.reshape(-1, 1)

    # 2. Fit Gaussian HMM to the returns
    model = GaussianHMM(n_components=n_states, covariance_type="diag", n_iter=100)
    model.fit(returns)

    # 3. Predict current hidden state sequence
    hidden_states = model.predict(returns)

    # 4. Analyze state properties (e.g., volatility of each state)
    state_vols = [np.std(returns[hidden_states == i]) for i in range(n_states)]
    state_labels = np.argsort(state_vols)  # From low to high volatility

    # 5. Map current state to regime
    current_state = hidden_states[-1]
    if current_state == state_labels[0]:
        return "mean-reverting"
    elif current_state == state_labels[1]:
        return "trending"
    else:
        return "volatile"
