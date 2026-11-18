"""Tests check our numbers against values we verified independently.

Replace or extend these with checks for your own formulas: a worked example (textbook,
DerivaGem, a hand calculation, a published figure), the data itself, another method, or an
identity. Name the source in a comment, as below.
"""
from math import exp

import pytest

from pricing import bs_call, bs_greeks, bs_put, intrinsic, option_price, session_year_fraction

# Hull, Options, Futures, and Other Derivatives (11th ed.), Ch. 15 worked example:
# S0 = 42, K = 40, r = 10%, sigma = 20%, T = 0.5 years -> c = 4.76, p = 0.81
S, K, R, SIGMA, T = 42.0, 40.0, 0.10, 0.20, 0.5


def test_call_matches_hull_example():
    assert bs_call(S, K, R, SIGMA, T) == pytest.approx(4.76, abs=0.005)


def test_put_matches_hull_example():
    assert bs_put(S, K, R, SIGMA, T) == pytest.approx(0.81, abs=0.005)


def test_put_call_parity():
    # c - p = S - K e^(-rT) must hold for European options on a non-dividend stock
    lhs = bs_call(S, K, R, SIGMA, T) - bs_put(S, K, R, SIGMA, T)
    rhs = S - K * exp(-R * T)
    assert lhs == pytest.approx(rhs, abs=1e-9)


def test_rejects_bad_inputs():
    with pytest.raises(ValueError):
        bs_call(S, K, R, -0.2, T)


def _price(right, spot, strike, rate, sigma, time):
    if right == "call":
        return bs_call(spot, strike, rate, sigma, time)
    return bs_put(spot, strike, rate, sigma, time)


def test_session_clock_splits_one_trading_day():
    # One session is 1/252 of a year. Thirteen half-hours fill that session.
    assert session_year_fraction(13) == pytest.approx(1 / 252)
    assert session_year_fraction(1) == pytest.approx(1 / (252 * 13))
    assert session_year_fraction(0) == 0


def test_expiry_payoff_is_intrinsic():
    assert intrinsic("call", 105, 100) == 5
    assert intrinsic("call", 95, 100) == 0
    assert intrinsic("put", 95, 100) == 5
    assert intrinsic("put", 105, 100) == 0
    assert option_price("call", 105, 100, R, SIGMA, 0) == 5
    assert option_price("put", 95, 100, R, SIGMA, 0) == 5


def test_greeks_match_finite_differences():
    # Another method: bump the Black-Scholes price. Theta is -dV/dT because
    # T is time left and theta is the derivative as calendar time moves forward.
    cases = [
        (42.0, 40.0, 0.10, 0.20, 0.5),
        (100.0, 100.0, 0.04, 0.20, 1 / 252),
    ]
    for spot, strike, rate, sigma, time in cases:
        for right in ("call", "put"):
            greeks = bs_greeks(spot, strike, rate, sigma, time, right)
            h_spot = spot * 1e-4
            up = _price(right, spot + h_spot, strike, rate, sigma, time)
            mid = _price(right, spot, strike, rate, sigma, time)
            down = _price(right, spot - h_spot, strike, rate, sigma, time)
            delta = (up - down) / (2 * h_spot)
            gamma = (up - 2 * mid + down) / h_spot**2
            h_vol = 1e-4
            vega = (
                _price(right, spot, strike, rate, sigma + h_vol, time)
                - _price(right, spot, strike, rate, sigma - h_vol, time)
            ) / (2 * h_vol)
            h_time = time * 1e-4
            theta = -(
                _price(right, spot, strike, rate, sigma, time + h_time)
                - _price(right, spot, strike, rate, sigma, time - h_time)
            ) / (2 * h_time)
            assert greeks["delta"] == pytest.approx(delta, rel=1e-4, abs=1e-5)
            assert greeks["gamma"] == pytest.approx(gamma, rel=1e-3, abs=1e-5)
            assert greeks["vega"] == pytest.approx(vega, rel=1e-4, abs=1e-5)
            assert greeks["theta"] == pytest.approx(theta, rel=1e-4, abs=1e-4)


def test_black_scholes_pde():
    # Identity: theta + 0.5 * sigma^2 * S^2 * gamma + r * S * delta - r * V = 0.
    cases = [
        (42.0, 40.0, 0.10, 0.20, 0.5),
        (100.0, 97.0, 0.04, 0.20, 1 / 252),
    ]
    for spot, strike, rate, sigma, time in cases:
        for right in ("call", "put"):
            greeks = bs_greeks(spot, strike, rate, sigma, time, right)
            value = _price(right, spot, strike, rate, sigma, time)
            residual = (
                greeks["theta"]
                + 0.5 * sigma**2 * spot**2 * greeks["gamma"]
                + rate * spot * greeks["delta"]
                - rate * value
            )
            assert residual == pytest.approx(0, abs=1e-6)


def test_call_delta_exceeds_put_delta_by_one():
    # Identity for European options with no dividend: delta_call - delta_put = 1.
    call = bs_greeks(S, K, R, SIGMA, T, "call")
    put = bs_greeks(S, K, R, SIGMA, T, "put")
    assert call["delta"] - put["delta"] == pytest.approx(1, abs=1e-12)
    assert call["gamma"] == pytest.approx(put["gamma"], abs=1e-12)
    assert call["vega"] == pytest.approx(put["vega"], abs=1e-12)
