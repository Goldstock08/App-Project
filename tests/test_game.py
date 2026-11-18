"""Checks for the week engine.

The replay uses one seed twice. The bankroll check is cash accounting:
unspent bankroll plus units times the intrinsic payoff. The one-step check
rebuilds the risk-neutral draw from that same seed.
"""
from math import exp, sqrt

import numpy as np
import pytest

from game import Game, clock_label
from pricing import intrinsic, session_year_fraction


def _play_day(game: Game, right: str = "call", stake: float = 0.25) -> None:
    game.start_day(right, stake)
    while game.phase == "playing":
        game.advance()


def test_clock_runs_from_open_to_close():
    assert clock_label(0) == "09:30"
    assert clock_label(1) == "10:00"
    assert clock_label(13) == "16:00"


def test_one_step_matches_risk_neutral_draw():
    sigma, rate, spot = 0.20, 0.04, 100.0
    game = Game(spot, sigma, rate, seed=3)
    game.start_day("call", 0.5)
    shock = float(np.random.default_rng(3).standard_normal())
    dt = session_year_fraction(1)
    expected = spot * exp((rate - 0.5 * sigma**2) * dt + sigma * sqrt(dt) * shock)
    game.advance()
    assert game.spot == pytest.approx(expected)
    assert game.path[1].clock == "10:00"
    assert game.path[0].pnl == pytest.approx(0, abs=1e-9)


def test_same_seed_replays_the_same_day():
    def closes(seed: int) -> list[float]:
        game = Game(100.0, 0.20, 0.04, seed=seed)
        _play_day(game, "call", 0.5)
        return [snap.spot for snap in game.path]

    assert closes(42) == pytest.approx(closes(42))
    assert len(closes(42)) == 14


def test_bankroll_equals_unspent_cash_plus_payoff():
    game = Game(100.0, 0.20, 0.04, seed=11)
    game.start_day("put", 1.0)
    premium = game.premium
    while game.phase == "playing":
        game.advance()
    result = game.history[-1]
    payoff = intrinsic("put", result.close_spot, result.strike)
    assert result.payoff == pytest.approx(payoff)
    assert game.bankroll == pytest.approx(game.unspent + game.units * payoff, abs=1e-6)
    assert result.profit == pytest.approx(game.bankroll - result.day_start_bankroll)
    assert premium == pytest.approx(result.premium)


def test_locked_premium_matches_the_morning_quote():
    game = Game(100.0, 0.20, 0.04, seed=1)
    quote = game.preview("call")
    game.start_day("call", 0.25)
    assert game.premium == pytest.approx(quote["premium"])
    assert game.strike == pytest.approx(quote["strike"])
    with pytest.raises(RuntimeError):
        game.start_day("put", 0.25)


def test_next_morning_opens_at_the_close():
    game = Game(100.0, 0.20, 0.04, seed=5)
    _play_day(game, "call", 0.25)
    close = game.spot
    assert game.phase == "settled"
    assert game.history[0].day_name == "Monday"
    game.next_day()
    assert game.phase == "choose"
    assert game.day_name == "Tuesday"
    assert game.spot == pytest.approx(close)
    assert game.path == []


def test_five_sessions_end_the_week():
    game = Game(100.0, 0.20, 0.04, seed=1)
    for expected in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday"):
        assert game.phase == "choose"
        assert game.day_name == expected
        _play_day(game, "call", 0.25)
        if game.phase == "settled":
            game.next_day()
    assert game.phase == "week_over"
    assert [day.day_name for day in game.history] == [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
    ]
    assert game.bankroll > 0
