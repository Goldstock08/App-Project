"""Monday-to-Friday 0DTE game. No Streamlit code.

Each morning the player buys an at-the-money European call or put. Each step
moves the clock forward half an hour and draws one risk-neutral return from
the same volatility that priced the option. At 16:00 the option pays intrinsic
value. Tuesday opens at Monday's close. There is no overnight gap.
"""
from dataclasses import dataclass
from math import exp, sqrt

import numpy as np

from pricing import (
    STEPS_PER_SESSION,
    bs_greeks,
    intrinsic,
    option_price,
    session_year_fraction,
)

DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
STARTING_BANKROLL = 10_000.0


def clock_label(steps_taken: int) -> str:
    """Session clock. Step 0 is 09:30 and step 13 is 16:00."""
    if not 0 <= steps_taken <= STEPS_PER_SESSION:
        raise ValueError("steps_taken is outside the session")
    minutes = 9 * 60 + 30 + steps_taken * 30
    hour, minute = divmod(minutes, 60)
    return f"{hour:02d}:{minute:02d}"


@dataclass
class Snapshot:
    steps_taken: int
    steps_left: int
    clock: str
    year_fraction: float
    spot: float
    mark: float
    pnl: float
    delta: float | None
    gamma: float | None
    vega: float | None
    theta: float | None
    theta_per_step: float | None


@dataclass
class DayResult:
    day_name: str
    right: str
    strike: float
    stake: float
    units: float
    premium: float
    open_spot: float
    close_spot: float
    payoff: float
    day_start_bankroll: float
    cash_after: float
    profit: float


class Game:
    def __init__(
        self,
        spot_open: float,
        sigma: float,
        r: float,
        seed: int,
        bankroll: float = STARTING_BANKROLL,
    ):
        if spot_open <= 0 or sigma <= 0:
            raise ValueError("spot and volatility must be positive")
        self.monday_open = float(spot_open)
        self.spot = float(spot_open)
        self.sigma = float(sigma)
        self.r = float(r)
        self.seed = int(seed)
        self.bankroll = float(bankroll)
        self.starting_bankroll = float(bankroll)
        self.rng = np.random.default_rng(self.seed)
        self.day_index = 0
        self.phase = "choose"
        self.right: str | None = None
        self.strike: float | None = None
        self.stake_fraction: float | None = None
        self.stake: float | None = None
        self.units: float | None = None
        self.premium: float | None = None
        self.unspent: float | None = None
        self.day_start_bankroll: float | None = None
        self.open_spot: float | None = None
        self.steps_taken = 0
        self.path: list[Snapshot] = []
        self.history: list[DayResult] = []

    @property
    def day_name(self) -> str:
        if self.day_index >= len(DAY_NAMES):
            return DAY_NAMES[-1]
        return DAY_NAMES[self.day_index]

    def equity(self) -> float:
        """Marked cash: unspent bankroll plus the live option value."""
        if self.phase == "playing" and self.path and self.units is not None and self.unspent is not None:
            return self.unspent + self.units * self.path[-1].mark
        return self.bankroll

    def preview(self, right: str) -> dict[str, float]:
        """At-the-money quote for this morning, before the player locks a bet."""
        if self.phase != "choose":
            raise RuntimeError("The morning quote is only available before the bet is locked")
        price, greeks = _quote(right, self.spot, self.spot, self.r, self.sigma, STEPS_PER_SESSION)
        return {"premium": price, "strike": self.spot, **greeks}

    def start_day(self, right: str, stake_fraction: float) -> None:
        if self.phase != "choose":
            raise RuntimeError("This day's bet is already locked")
        if self.bankroll <= 0:
            self.phase = "week_over"
            raise RuntimeError("The bankroll is zero")
        if right not in ("call", "put"):
            raise ValueError("right must be 'call' or 'put'")
        if not 0 < stake_fraction <= 1:
            raise ValueError("stake fraction must be between 0 and 1")

        self.right = right
        self.stake_fraction = float(stake_fraction)
        self.strike = self.spot
        self.open_spot = self.spot
        self.day_start_bankroll = self.bankroll
        self.steps_taken = 0
        premium, _ = _quote(right, self.spot, self.strike, self.r, self.sigma, STEPS_PER_SESSION)
        self.premium = premium
        self.stake = self.bankroll * stake_fraction
        self.units = self.stake / self.premium
        self.unspent = self.bankroll - self.stake
        self.phase = "playing"
        self.path = [self._snapshot(self.spot)]

    def advance(self) -> None:
        if self.phase != "playing":
            raise RuntimeError("Start the day before advancing the clock")
        if self.steps_taken >= STEPS_PER_SESSION:
            raise RuntimeError("The session is already over")
        dt = session_year_fraction(1)
        shock = float(self.rng.standard_normal())
        drift = (self.r - 0.5 * self.sigma**2) * dt
        diffusion = self.sigma * sqrt(dt) * shock
        self.spot = self.spot * exp(drift + diffusion)
        self.steps_taken += 1
        self.path.append(self._snapshot(self.spot))
        if self.steps_taken >= STEPS_PER_SESSION:
            self.settle()

    def settle(self) -> None:
        if self.phase != "playing" or self.steps_taken != STEPS_PER_SESSION:
            raise RuntimeError("Settle only at the 16:00 close")
        assert self.right is not None and self.strike is not None
        assert self.units is not None and self.unspent is not None
        assert self.premium is not None and self.day_start_bankroll is not None
        assert self.open_spot is not None and self.stake is not None
        payoff = intrinsic(self.right, self.spot, self.strike)
        cash = self.unspent + self.units * payoff
        if cash <= 1e-8:
            cash = 0.0
        self.history.append(
            DayResult(
                day_name=self.day_name,
                right=self.right,
                strike=self.strike,
                stake=self.stake,
                units=self.units,
                premium=self.premium,
                open_spot=self.open_spot,
                close_spot=self.spot,
                payoff=payoff,
                day_start_bankroll=self.day_start_bankroll,
                cash_after=cash,
                profit=cash - self.day_start_bankroll,
            )
        )
        self.bankroll = cash
        if self.day_index >= 4 or self.bankroll <= 0:
            self.phase = "week_over"
        else:
            self.phase = "settled"

    def next_day(self) -> None:
        if self.phase != "settled":
            raise RuntimeError("Settle the day before the next morning")
        self.day_index += 1
        self.path = []
        self.right = None
        self.strike = None
        self.stake_fraction = None
        self.stake = None
        self.units = None
        self.premium = None
        self.unspent = None
        self.day_start_bankroll = None
        self.open_spot = None
        self.steps_taken = 0
        if self.day_index >= 5 or self.bankroll <= 0:
            self.phase = "week_over"
        else:
            self.phase = "choose"

    def _snapshot(self, spot: float) -> Snapshot:
        assert self.right is not None and self.strike is not None
        assert self.units is not None and self.premium is not None
        steps_left = STEPS_PER_SESSION - self.steps_taken
        year_fraction = session_year_fraction(steps_left)
        if steps_left == 0:
            mark = intrinsic(self.right, spot, self.strike)
            delta = gamma = vega = theta = theta_per_step = None
        else:
            mark, greeks = _quote(
                self.right, spot, self.strike, self.r, self.sigma, steps_left
            )
            delta = greeks["delta"]
            gamma = greeks["gamma"]
            vega = greeks["vega"]
            theta = greeks["theta"]
            theta_per_step = theta * session_year_fraction(1)
        return Snapshot(
            steps_taken=self.steps_taken,
            steps_left=steps_left,
            clock=clock_label(self.steps_taken),
            year_fraction=year_fraction,
            spot=spot,
            mark=mark,
            pnl=self.units * (mark - self.premium),
            delta=delta,
            gamma=gamma,
            vega=vega,
            theta=theta,
            theta_per_step=theta_per_step,
        )


def _quote(
    right: str, spot: float, strike: float, r: float, sigma: float, steps_left: int
) -> tuple[float, dict[str, float]]:
    year_fraction = session_year_fraction(steps_left)
    price = option_price(right, spot, strike, r, sigma, year_fraction)
    greeks = bs_greeks(spot, strike, r, sigma, year_fraction, right)
    return price, greeks
