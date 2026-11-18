"""Pricing formulas for the app.

Keep this file free of Streamlit code so every function can be tested with pytest.
Units: S and K in index points or dollars, r and sigma as decimals per year
(0.05, not 5), T in years. Theta is per year. Vega is per 1.00 of volatility
(not per vol point).

One trading session is 1/252 of a year, split into 13 half-hours. That clock is
a modeling choice: a half-hour here is 1/(252*13) of a year, not 30 calendar minutes.
"""
from math import erf, exp, log, pi, sqrt

TRADING_DAYS_PER_YEAR = 252
STEPS_PER_SESSION = 13


def norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function N(x)."""
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def norm_pdf(x: float) -> float:
    """Standard normal density n(x)."""
    return exp(-0.5 * x * x) / sqrt(2.0 * pi)


def session_year_fraction(steps_left: int) -> float:
    """Year-fraction left in the session. A full session is 1/252; one step is 1/(252*13)."""
    if steps_left < 0:
        raise ValueError("steps_left cannot be negative")
    return steps_left / (TRADING_DAYS_PER_YEAR * STEPS_PER_SESSION)


def bs_d1_d2(S: float, K: float, r: float, sigma: float, T: float) -> tuple[float, float]:
    """Black-Scholes-Merton d1 and d2 (no dividends)."""
    if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
        raise ValueError("S, K, sigma and T must be positive")
    d1 = (log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt(T))
    return d1, d1 - sigma * sqrt(T)


def bs_call(S: float, K: float, r: float, sigma: float, T: float) -> float:
    """European call price under Black-Scholes-Merton (no dividends)."""
    d1, d2 = bs_d1_d2(S, K, r, sigma, T)
    return S * norm_cdf(d1) - K * exp(-r * T) * norm_cdf(d2)


def bs_put(S: float, K: float, r: float, sigma: float, T: float) -> float:
    """European put price under Black-Scholes-Merton (no dividends)."""
    d1, d2 = bs_d1_d2(S, K, r, sigma, T)
    return K * exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)


def intrinsic(right: str, S: float, K: float) -> float:
    """Expiry payoff of one European call or put. Units: same as S and K."""
    if S <= 0 or K <= 0:
        raise ValueError("S and K must be positive")
    if right == "call":
        return max(S - K, 0.0)
    if right == "put":
        return max(K - S, 0.0)
    raise ValueError("right must be 'call' or 'put'")


def option_price(right: str, S: float, K: float, r: float, sigma: float, T: float) -> float:
    """Black-Scholes price, or intrinsic value when no time is left."""
    if T < 0:
        raise ValueError("T cannot be negative")
    if T == 0:
        return intrinsic(right, S, K)
    if right == "call":
        return bs_call(S, K, r, sigma, T)
    if right == "put":
        return bs_put(S, K, r, sigma, T)
    raise ValueError("right must be 'call' or 'put'")


def bs_greeks(S: float, K: float, r: float, sigma: float, T: float, right: str) -> dict[str, float]:
    """Delta, gamma, vega, and theta of a European call or put with no dividends.

    Theta is dV/dt (calendar time), per year, so a long option's theta is negative.
    Vega is dV/dσ for σ in decimal form: the price change for a 1.00 move in volatility.
    Gamma is d²V/dS², per 1 point of the underlying.
    """
    if right not in ("call", "put"):
        raise ValueError("right must be 'call' or 'put'")
    d1, d2 = bs_d1_d2(S, K, r, sigma, T)
    pdf = norm_pdf(d1)
    discount = exp(-r * T)
    gamma = pdf / (S * sigma * sqrt(T))
    vega = S * pdf * sqrt(T)
    theta = -S * pdf * sigma / (2.0 * sqrt(T))
    if right == "call":
        delta = norm_cdf(d1)
        theta -= r * K * discount * norm_cdf(d2)
    else:
        delta = norm_cdf(d1) - 1.0
        theta += r * K * discount * norm_cdf(-d2)
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta}
