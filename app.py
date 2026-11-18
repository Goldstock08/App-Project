"""0DTE week. Streamlit reruns this whole file on every click.

The formulas live in pricing.py and the week lives in game.py. This file only
reads inputs, calls those functions, and draws the page. State that has to
survive a click sits in st.session_state.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from game import Game
from pricing import STEPS_PER_SESSION, bs_greeks, session_year_fraction

st.set_page_config(page_title="0DTE Week", page_icon="📈", layout="wide")

STAKE_LABELS = {"25%": 0.25, "50%": 0.5, "100%": 1.0}
SHORT_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri")

# Measures the browser window. Chart specs keep fixed dataset names so a
# half-hour step updates the points in place instead of building a new chart.
_fit_component = components.declare_component(
    "fit_page",
    path=str(Path(__file__).resolve().parent / "components" / "fit_page"),
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 4.5rem; padding-bottom: 0.3rem; min-height: 100vh; box-sizing: border-box; }
    div[data-testid="stVerticalBlock"] { gap: 0.35rem; }
    div[data-testid="stCustomComponentV1"] { height: 0; margin: 0; overflow: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


def money(value: float) -> str:
    return f"{value:,.2f}"


def breakeven(right: str, strike: float, premium: float) -> float:
    if right == "call":
        return strike + premium
    return strike - premium


def expiry_delta(right: str, spot: float, strike: float) -> float:
    """Payoff step. At the strike the step is drawn through one half."""
    if spot == strike:
        return 0.5 if right == "call" else -0.5
    if right == "call":
        return 1.0 if spot > strike else 0.0
    return -1.0 if spot < strike else 0.0


def hold_selection(key: str, allowed: tuple[str, ...], fallback: str) -> None:
    """Keep a segmented control from clearing when its current choice is clicked again."""
    if key not in st.session_state:
        return
    value = st.session_state[key]
    if value in allowed:
        st.session_state[f"{key}_last"] = value
        return
    st.session_state[key] = st.session_state.get(f"{key}_last", fallback)


def chosen_contract() -> str:
    value = st.session_state.get("contract") or "call"
    return value if value in ("call", "put") else "call"


def chosen_stake() -> tuple[str, float]:
    label = st.session_state.get("stake_ui") or "25%"
    if label not in STAKE_LABELS:
        label = "25%"
    return label, STAKE_LABELS[label]


def page_viewport() -> int:
    """Browser window height in pixels. 900 until the page reports its own size."""
    measured = _fit_component(default={"height": 900}, key="fit_page")
    if isinstance(measured, dict) and measured.get("height"):
        return int(measured["height"])
    return 900


def fit_page(viewport_height: int) -> tuple[int, int]:
    """Pixel heights for the spot row and the Greek chart.

    viewport_height is the browser window in pixels. The reserved band is the
    header, the week strip, the status line, the captions, and a collapsed
    method section. The spot row gets a bit more than half of what remains.
    """
    reserved = 292
    room = max(320, int(viewport_height) - reserved)
    spot = max(180, int(room * 0.56))
    greek = max(140, room - spot)
    return spot, greek


def show_chart(spec: dict, chart_key: str) -> None:
    """Draw a chart whose dataset names stay fixed when the points change."""
    st.vega_lite_chart(spec, use_container_width=True, key=chart_key)


def delta_cliff(
    right: str,
    strike: float,
    rate: float,
    sigma: float,
    steps_left: int,
    spot: float,
    height: int,
) -> dict:
    grid = np.linspace(strike * 0.85, strike * 1.15, 121)
    if steps_left <= 0:
        deltas = [expiry_delta(right, float(level), strike) for level in grid]
    else:
        time_left = session_year_fraction(steps_left)
        deltas = [
            bs_greeks(float(level), strike, rate, sigma, time_left, right)["delta"]
            for level in grid
        ]
    return {
        "height": height,
        "layer": [
            {
                "data": {"name": "curve"},
                "mark": {"type": "line"},
                "encoding": {
                    "x": {"field": "Spot", "type": "quantitative", "title": "Underlying"},
                    "y": {"field": "Delta", "type": "quantitative", "title": "Delta"},
                    "tooltip": [
                        {"field": "Spot", "type": "quantitative", "format": ".2f"},
                        {"field": "Delta", "type": "quantitative", "format": ".3f"},
                    ],
                },
            },
            {
                "data": {"name": "now"},
                "mark": {"type": "rule", "strokeDash": [6, 4], "color": "#e45756"},
                "encoding": {"x": {"field": "Spot", "type": "quantitative"}},
            },
        ],
        "datasets": {
            "curve": pd.DataFrame({"Spot": grid, "Delta": deltas}),
            "now": pd.DataFrame({"Spot": [spot]}),
        },
    }


def spot_chart(
    clocks: list[str],
    spots: list[float],
    strike: float,
    line: float,
    height: int,
) -> dict:
    return {
        "height": height,
        "layer": [
            {
                "data": {"name": "path"},
                "mark": {"type": "line", "point": True},
                "encoding": {
                    "x": {
                        "field": "Clock",
                        "type": "nominal",
                        "sort": None,
                        "axis": {"title": None},
                    },
                    "y": {
                        "field": "Spot",
                        "type": "quantitative",
                        "title": "Spot",
                        "scale": {"zero": False, "padding": 30},
                    },
                    "tooltip": [
                        {"field": "Clock", "type": "nominal"},
                        {"field": "Spot", "type": "quantitative", "format": ".2f"},
                    ],
                },
            },
            {
                "data": {"name": "guides"},
                "mark": {"type": "rule", "strokeDash": [6, 4]},
                "encoding": {
                    "y": {"field": "Level", "type": "quantitative"},
                    "color": {
                        "field": "Guide",
                        "type": "nominal",
                        "scale": {
                            "domain": ["Strike", "Breakeven"],
                            "range": ["#f58518", "#54a24b"],
                        },
                        "legend": {"orient": "top", "title": None, "direction": "horizontal"},
                    },
                },
            },
        ],
        "datasets": {
            "path": pd.DataFrame({"Clock": clocks, "Spot": spots}),
            "guides": pd.DataFrame(
                {"Level": [strike, line], "Guide": ["Strike", "Breakeven"]}
            ),
        },
    }


def greek_frame_from_levels(clock: str, delta: float, gamma: float, vega: float, theta: float) -> pd.DataFrame:
    """One row per Greek. Versus open is 1 at the first clock on the frame."""
    return pd.DataFrame(
        {
            "Clock": [clock, clock, clock, clock],
            "Greek": ["Delta", "Gamma", "Vega", "Theta"],
            "Versus open": [1.0, 1.0, 1.0, 1.0],
            "Level": [delta, gamma, vega, theta],
        }
    )


def greek_frame_from_path(game: Game) -> pd.DataFrame:
    """Delta, gamma, vega, and theta divided by their 09:30 values.

    Vega level is per volatility point. Theta level is per half-hour.
    Rows with no Black-Scholes quote (the 16:00 payoff) are left out.
    """
    usable = [snap for snap in game.path if snap.delta is not None]
    if not usable:
        return pd.DataFrame(columns=["Clock", "Greek", "Versus open", "Level"])
    origin = usable[0]
    series = (
        ("Delta", "delta", 1.0),
        ("Gamma", "gamma", 1.0),
        ("Vega", "vega", 100.0),
        ("Theta", "theta_per_step", 1.0),
    )
    rows = []
    for snap in usable:
        for name, attr, scale in series:
            level = getattr(snap, attr) / scale
            base = getattr(origin, attr) / scale
            rows.append(
                {
                    "Clock": snap.clock,
                    "Greek": name,
                    "Versus open": level / base,
                    "Level": level,
                }
            )
    return pd.DataFrame(rows)


def greek_chart(frame: pd.DataFrame, height: int) -> dict:
    low = min(0.75, float(frame["Versus open"].min()) * 0.9)
    high = max(1.25, float(frame["Versus open"].max()) * 1.1)
    return {
        "height": height,
        "layer": [
            {
                "data": {"name": "span"},
                "mark": {"type": "rule", "opacity": 0},
                "encoding": {
                    "y": {
                        "field": "Versus open",
                        "type": "quantitative",
                        "scale": {"zero": False},
                    }
                },
            },
            {
                "data": {"name": "guide"},
                "mark": {"type": "rule", "strokeDash": [4, 4], "color": "#888"},
                "encoding": {
                    "y": {"field": "Versus open", "type": "quantitative", "scale": {"zero": False}}
                },
            },
            {
                "data": {"name": "series"},
                "mark": {"type": "line", "point": True},
                "encoding": {
                    "x": {
                        "field": "Clock",
                        "type": "nominal",
                        "sort": None,
                        "axis": {"title": None},
                    },
                    "y": {
                        "field": "Versus open",
                        "type": "quantitative",
                        "title": "Versus 09:30",
                        "scale": {"zero": False},
                    },
                    "color": {
                        "field": "Greek",
                        "type": "nominal",
                        "legend": {"orient": "bottom", "title": None, "direction": "horizontal"},
                    },
                    "tooltip": [
                        {"field": "Greek", "type": "nominal"},
                        {"field": "Clock", "type": "nominal"},
                        {
                            "field": "Versus open",
                            "type": "quantitative",
                            "format": ".2f",
                            "title": "Versus 09:30",
                        },
                        {"field": "Level", "type": "quantitative", "format": ".4f", "title": "Level"},
                    ],
                },
            },
        ],
        "datasets": {
            "span": pd.DataFrame({"Versus open": [low, high]}),
            "guide": pd.DataFrame({"Versus open": [1.0]}),
            "series": frame,
        },
    }


def path_frame(game: Game) -> pd.DataFrame:
    rows = []
    for snap in game.path:
        rows.append(
            {
                "Clock": snap.clock,
                "Spot": snap.spot,
                "Mark": snap.mark,
                "Profit vs premium": snap.pnl,
                "Delta": snap.delta,
                "Gamma": snap.gamma,
                "Theta per half-hour": snap.theta_per_step,
                "Vega per vol point": None if snap.vega is None else snap.vega / 100,
                "Minutes left": snap.steps_left * 30,
            }
        )
    return pd.DataFrame(rows)


def history_frame(game: Game) -> pd.DataFrame:
    rows = []
    for day in game.history:
        rows.append(
            {
                "Day": day.day_name,
                "Side": day.right,
                "Open": day.open_spot,
                "Strike": day.strike,
                "Premium": day.premium,
                "Breakeven": breakeven(day.right, day.strike, day.premium),
                "Close": day.close_spot,
                "Payoff": day.payoff,
                "Stake (USD)": day.stake,
                "Profit (USD)": day.profit,
                "Bankroll (USD)": day.cash_after,
            }
        )
    return pd.DataFrame(rows)


def week_line(game: Game) -> str:
    parts = []
    for index, name in enumerate(SHORT_DAYS):
        if index < len(game.history):
            parts.append(f"**{name} {game.history[index].profit:+,.0f}**")
        elif game.phase != "week_over" and index == game.day_index:
            parts.append(f"**{name}**")
        else:
            parts.append(name)
    return "  ·  ".join(parts)


def status_line(game: Game) -> str:
    if game.phase == "choose":
        return f"{game.day_name} open  ·  spot {game.spot:,.2f}  ·  strike will be the open"
    if game.phase == "week_over" and not game.path:
        return "Week over"
    last = game.path[-1] if game.path else None
    if last is None:
        return game.day_name
    if game.phase == "settled":
        return (
            f"{game.day_name} {game.right} settled  ·  close {last.spot:,.2f}  ·  "
            f"profit {game.history[-1].profit:+,.2f}"
        )
    if game.phase == "week_over":
        return f"Week over  ·  close {last.spot:,.2f}  ·  bankroll {money(game.bankroll)}"
    return (
        f"{game.day_name} {game.right}  ·  {last.clock}  ·  "
        f"step {game.steps_taken} of {STEPS_PER_SESSION}  ·  {last.steps_left * 30} min left"
    )


def draw_pairs(pairs: list[tuple[str, str]]) -> None:
    for left, right in zip(pairs[0::2], pairs[1::2]):
        left_col, right_col = st.columns(2)
        left_col.caption(left[0])
        left_col.markdown(f"**{left[1]}**")
        right_col.caption(right[0])
        right_col.markdown(f"**{right[1]}**")


def quote_numbers(right: str, quote: dict[str, float], stake_fraction: float, bankroll: float) -> None:
    line = breakeven(right, quote["strike"], quote["premium"])
    units = bankroll * stake_fraction / quote["premium"]
    theta_step = quote["theta"] * session_year_fraction(1)
    draw_pairs(
        [
            ("Premium", f"{quote['premium']:,.4f}"),
            ("Breakeven", f"{line:,.2f}"),
            ("Units", f"{units:,.1f}"),
            ("P&L", "0.00"),
            ("Delta", f"{quote['delta']:,.3f}"),
            ("Gamma", f"{quote['gamma']:,.4f}"),
            ("Vega", f"{quote['vega'] / 100:,.4f}"),
            ("Theta / 30m", f"{theta_step:,.4f}"),
        ]
    )


def position_numbers(game: Game) -> None:
    last = game.path[-1]
    assert game.premium is not None and game.strike is not None and game.units is not None
    line = breakeven(game.right, game.strike, game.premium)
    if last.delta is None:
        greek_pairs = [("Delta", "expired"), ("Gamma", "expired"), ("Vega", "expired"), ("Theta / 30m", "expired")]
    else:
        greek_pairs = [
            ("Delta", f"{last.delta:,.3f}"),
            ("Gamma", f"{last.gamma:,.4f}"),
            ("Vega", f"{last.vega / 100:,.4f}"),
            ("Theta / 30m", f"{last.theta_per_step:,.4f}"),
        ]
    draw_pairs(
        [
            ("Premium", f"{game.premium:,.4f}"),
            ("Breakeven", f"{line:,.2f}"),
            ("Mark", f"{last.mark:,.4f}"),
            ("P&L", f"{last.pnl:,.2f}"),
            *greek_pairs,
        ]
    )


def run_action(game: Game) -> None:
    if game.phase == "choose":
        if st.button("Buy at the open", type="primary"):
            label, fraction = chosen_stake()
            game.start_day(chosen_contract(), fraction)
            st.session_state["locked_stake"] = label
        return
    if game.phase == "playing":
        label = "Settle at 16:00" if game.steps_taken == STEPS_PER_SESSION - 1 else "Advance 30 minutes"
        if st.button(label, type="primary"):
            game.advance()
        return
    if game.phase == "settled" and st.button("Next morning", type="primary"):
        game.next_day()


if "game" not in st.session_state:
    st.session_state.game = Game(100.0, 0.20, 0.04, 1)

with st.sidebar:
    st.header("Assumptions")
    st.caption(
        "These lock in when you start a new week. The random moves use this volatility, "
        "so the option is fair before luck. Starting cash is 10,000, hypothetical."
    )
    monday_open = st.number_input("Monday open", min_value=0.01, value=100.0, step=1.0)
    vol_pct = st.number_input("Volatility (% per year)", min_value=0.1, value=20.0, step=1.0)
    rate_pct = st.number_input("Risk-free rate (% per year)", value=4.0, step=0.5)
    seed = st.number_input("Random seed", min_value=0, max_value=1_000_000_000, value=1, step=1)
    st.caption(
        "European, no dividend, constant volatility, no bid-ask, no overnight gap. "
        "One session is 1/252 of a year, split into 13 half-hours."
    )
    if st.button("Start a new week"):
        st.session_state.game = Game(
            float(monday_open),
            float(vol_pct) / 100,
            float(rate_pct) / 100,
            int(seed),
        )

game = st.session_state.game
spot_height, greek_height = fit_page(page_viewport())

head_days, head_equity, head_multiple, head_button = st.columns([4.2, 1.3, 1.1, 1.7])
days_box = head_days.empty()
equity_box = head_equity.empty()
multiple_box = head_multiple.empty()
with head_button:
    run_action(game)
days_box.markdown(week_line(game))
equity_box.markdown(f"**{money(game.equity())}**")
multiple_box.markdown(f"**{game.equity() / game.starting_bankroll:.2f}x**")
st.caption(status_line(game))

left, stage = st.columns([1.05, 3.3], gap="small")

with left:
    if game.phase == "choose":
        hold_selection("contract", ("call", "put"), "call")
        hold_selection("stake_ui", tuple(STAKE_LABELS), "25%")
        contract_args = {"key": "contract", "width": "stretch"}
        stake_args = {"key": "stake_ui", "width": "stretch"}
        if "contract" not in st.session_state:
            contract_args["default"] = "call"
        if "stake_ui" not in st.session_state:
            stake_args["default"] = "25%"
        st.segmented_control("Contract", ["call", "put"], **contract_args)
        st.segmented_control("Stake", list(STAKE_LABELS), **stake_args)
        right = chosen_contract()
        stake_label, stake_fraction = chosen_stake()
        quote = game.preview(right)
        quote_numbers(right, quote, stake_fraction, game.bankroll)
        if stake_fraction == 1.0:
            st.caption("The whole bankroll. A worthless expiry ends the week.")
        view_right = right
        view_strike = game.spot
        view_line = breakeven(right, game.spot, quote["premium"])
        view_clocks = ["09:30"]
        view_spots = [game.spot]
        view_steps = STEPS_PER_SESSION
        view_spot = game.spot
        greek_data = greek_frame_from_levels(
            "09:30",
            quote["delta"],
            quote["gamma"],
            quote["vega"] / 100,
            quote["theta"] * session_year_fraction(1),
        )
    else:
        locked = st.session_state.get("locked_stake", "")
        st.markdown(f"**{game.right}**  ·  {locked}")
        position_numbers(game)
        last = game.path[-1]
        view_right = game.right
        view_strike = game.strike
        view_line = breakeven(game.right, game.strike, game.premium)
        view_clocks = [snap.clock for snap in game.path]
        view_spots = [snap.spot for snap in game.path]
        view_steps = last.steps_left
        view_spot = last.spot
        greek_data = greek_frame_from_path(game)

with stage:
    spot_col, cliff_col = st.columns(2, gap="small")
    with spot_col:
        st.caption("Spot, strike, and breakeven")
        show_chart(
            spot_chart(view_clocks, view_spots, view_strike, view_line, spot_height),
            "spot_chart",
        )
    with cliff_col:
        cliff_note = "Payoff step" if view_steps == 0 else "Delta across spot"
        st.caption(cliff_note)
        show_chart(
            delta_cliff(
                view_right,
                view_strike,
                game.r,
                game.sigma,
                view_steps,
                view_spot,
                spot_height,
            ),
            "cliff_chart",
        )
    st.caption(
        "Delta, gamma, vega, and theta on one scale: each divided by its 09:30 value. "
        "1.00 means unchanged. The dashed line is 1.00. Lines stop at 15:30, when the quote ends."
    )
    if not greek_data.empty:
        show_chart(greek_chart(greek_data, greek_height), "greek_chart")

if game.phase == "week_over" and game.bankroll <= 0:
    st.caption("The last expiry paid nothing, and that stake was the rest of the bankroll.")

with st.expander("Method and numbers"):
    st.markdown(
        "The price is the Black-Scholes-Merton call or put with no dividend. "
        "Each click draws a standard normal Z and moves the underlying by"
    )
    st.latex(
        r"\log(S_{\mathrm{new}}/S)=(r-\tfrac{1}{2}\sigma^{2})\Delta t+\sigma\sqrt{\Delta t}\,Z"
    )
    st.markdown(
        "using the same volatility that set the premium, and Δt = 1/(252 × 13). "
        "At 16:00 a call pays max(S − K, 0) and a put pays max(K − S, 0). "
        "Cash left is the unspent bankroll plus units times that payoff. "
        "Vega on the chart is per volatility point. Theta is per half-hour."
    )
    if game.path:
        st.dataframe(path_frame(game), hide_index=True, width="stretch")
    if game.history:
        st.dataframe(history_frame(game), hide_index=True, width="stretch")
