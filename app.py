"""0DTE week. Streamlit reruns this whole file on every click.

The formulas live in pricing.py and the week lives in game.py. This file only
reads inputs, calls those functions, and draws the page. State that has to
survive a click sits in st.session_state.
"""
import base64
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
_COMPONENT_DIR = Path(__file__).resolve().parent / "components"
_fit_component = components.declare_component(
    "fit_page",
    path=str(_COMPONENT_DIR / "fit_page"),
)
_cheer_component = components.declare_component(
    "cheer_big",
    path=str(_COMPONENT_DIR / "cheer"),
)

# Real photographs, cropped down. See assets/desk/SOURCES.txt for the license of each one.
_DESK = Path(__file__).resolve().parent / "assets" / "desk"


def _photo(name: str) -> str:
    kind = "png" if name.endswith(".png") else "jpeg"
    encoded = base64.b64encode((_DESK / name).read_bytes()).decode("ascii")
    return f"data:image/{kind};base64,{encoded}"


_DESK_CSS = """
    <svg width="0" height="0" style="position:absolute" aria-hidden="true">
      <filter id="pen">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="4" result="n"/>
        <feDisplacementMap in="SourceGraphic" in2="n" scale="1.15" xChannelSelector="R" yChannelSelector="G"/>
      </filter>
    </svg>
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Caveat:wght@600;700&family=Kalam:wght@400;700&display=swap');
    .stApp {
      background-color: #2a241f !important;
      background-image: none !important;
    }
    [data-testid="stHeader"] { background: rgba(48, 28, 14, 0.55); }
    [data-testid="stSidebar"] {
      background-color: #f7f4ee;
      background-image: url("LINED");
      background-size: cover;
      background-position: left top;
      border-right: 1px solid rgba(80, 50, 20, 0.35);
      color: #2a241c;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
      color: #2a241c;
      font-family: "Kalam", "Comic Sans MS", cursive;
    }
    [data-testid="stSidebar"] input {
      background: rgba(255, 252, 245, 0.82);
      color: #1a3a78;
      border: 1px solid #c3b49a;
      font-family: "Kalam", "Comic Sans MS", cursive;
    }
    .block-container {
      padding-top: 4.5rem;
      padding-bottom: 0.6rem;
      box-sizing: border-box;
      background-color: #6e3a1c;
      background-image:
        radial-gradient(ellipse 75% 42% at 50% 0%, rgba(255, 228, 190, 0.10), rgba(255, 228, 190, 0) 55%),
        url("WOOD");
      background-size: cover, cover;
      background-repeat: no-repeat, no-repeat;
      background-position: center top, center;
      border-radius: 3px;
      box-shadow:
        0 0 0 14px #7a4324,
        0 0 0 20px #3d2214,
        0 22px 34px rgba(0, 0, 0, 0.45);
    }
    div[data-testid="stVerticalBlock"] { gap: 0.35rem; }
    div[data-testid="stCustomComponentV1"] { height: 0; margin: 0; overflow: hidden; }
    div[data-testid="stHorizontalBlock"]:has(.term-sheet) { align-items: flex-start; }
    div[data-testid="stColumn"]:has(.term-sheet),
    div[data-testid="stColumn"]:has(.sheet-graph):not(:has(div[data-testid="stColumn"])),
    div[data-testid="stVerticalBlock"]:has(.greek-page):not(:has(div[data-testid="stColumn"])),
    div[data-testid="stHorizontalBlock"]:has(.week),
    [data-testid="stExpander"] details {
      color: #2a241c;
      border-radius: 2px;
      box-shadow:
        0 1px 0 rgba(255, 255, 255, 0.55) inset,
        0 10px 16px rgba(40, 22, 8, 0.32);
    }
    div[data-testid="stColumn"]:has(.term-sheet) {
      background-color: #f7f4ee;
      background-image: url("LINED");
      background-size: 560px auto;
      background-repeat: repeat;
      background-position: -70px top;
      padding: 0.55rem 0.75rem 0.7rem;
    }
    div[data-testid="stColumn"]:has(.sheet-graph):not(:has(div[data-testid="stColumn"])),
    div[data-testid="stVerticalBlock"]:has(.greek-page):not(:has(div[data-testid="stColumn"])) {
      background-color: #f6f4ee;
      background-image: url("GRAPH_WHITE");
      background-size: 800px 800px;
      background-repeat: repeat;
      background-position: top left;
      padding: 0.35rem 0.5rem 0.45rem;
      border: none !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.week) {
      background-color: #f4e2b2;
      background-image: url("KRAFT");
      background-size: 384px 384px;
      background-repeat: repeat;
      padding: 0.45rem 0.7rem 0.5rem;
    }
    [data-testid="stExpander"] details {
      background-color: #f4e2b2;
      background-image: url("KRAFT");
      background-size: 384px 384px;
      background-repeat: repeat;
    }
    div[data-testid="stColumn"]:has(.sheet-graph) [data-testid="stCaptionContainer"] p,
    div[data-testid="stVerticalBlock"]:has(.greek-page) [data-testid="stCaptionContainer"] p {
      color: #1a1208 !important;
      font-family: "Kalam", "Comic Sans MS", cursive;
      font-weight: 700 !important;
      font-size: 1.05rem;
    }
    div[data-testid="stColumn"]:has(.term-sheet) [data-testid="stCaptionContainer"] p,
    div[data-testid="stHorizontalBlock"]:has(.week) [data-testid="stCaptionContainer"] p,
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] p {
      color: #3a3228 !important;
      font-family: "Kalam", "Comic Sans MS", cursive;
    }
    div[data-testid="stColumn"]:has(.term-sheet) [data-testid="stMarkdown"] p {
      color: #1a3a78;
      font-family: "Kalam", "Comic Sans MS", cursive;
      font-size: 1.02rem;
    }
    [data-testid="stVegaLiteChart"] { background: transparent; }
    [data-testid="stVegaLiteChart"] svg text {
      font-weight: 700;
      fill: #1a1208;
    }
    .week { display: flex; gap: 0.45rem; flex-wrap: wrap; }
    .day, .day.up, .day.down {
      min-width: 3.5rem;
      padding: 0.2rem 0.5rem 0.28rem;
      border: none;
      border-radius: 1px;
      background-color: #f6e15a;
      background-image: url("STICKY");
      background-size: cover;
      line-height: 1.15;
      box-shadow: 1px 3px 4px rgba(40, 28, 8, 0.35);
    }
    .day:nth-child(odd) { transform: rotate(-2deg); }
    .day:nth-child(even) { transform: rotate(1.6deg); }
    .day .name {
      font-size: 0.72rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: #5a4a28;
      font-family: "Caveat", "Comic Sans MS", cursive;
    }
    .day .result {
      font-size: 0.95rem;
      font-weight: 700;
      color: #1a3a78;
      font-family: "Kalam", "Comic Sans MS", cursive;
    }
    .day.now { box-shadow: 0 0 0 2px #8a5a18, 1px 3px 4px rgba(40, 28, 8, 0.35); }
    .day.up .result { color: #1b7a45; }
    .day.down .result { color: #9b2d28; }
    .score .kicker {
      font-size: 0.78rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: #5c4630;
      font-family: "Caveat", "Comic Sans MS", cursive;
    }
    .score .cash {
      font-size: 1.55rem;
      font-weight: 700;
      color: #1a3a78;
      line-height: 1.05;
      font-family: "Kalam", "Comic Sans MS", cursive;
    }
    .score .mult {
      font-size: 1.55rem;
      font-weight: 700;
      line-height: 1.05;
      font-family: "Kalam", "Comic Sans MS", cursive;
    }
    .up { color: #1b7a45; font-weight: 700; }
    .down { color: #9b2d28; font-weight: 700; }
    .flat { color: #1a3a78; }
    .term-sheet {
      background-color: #f3dc6a;
      background-image: url("STICKY");
      background-size: cover;
      margin-top: 0.45rem;
      padding: 0.45rem 0.65rem 0.55rem;
      transform: rotate(-1.1deg);
      box-shadow: 2px 5px 8px rgba(50, 36, 8, 0.28);
      filter: url(#pen);
    }
    .term-sheet .kicker {
      font-size: 1rem;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      color: #6a5018;
      margin-bottom: 0.15rem;
      font-family: "Caveat", "Comic Sans MS", cursive;
    }
    .term-sheet .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.12rem 0.65rem;
      font-size: 0.92rem;
      line-height: 1.2;
      color: #3a2a10;
      font-family: "Caveat", "Comic Sans MS", cursive;
    }
    .term-sheet b { color: #2a1c08; font-weight: 700; }
    .on-wood {
      display: inline-block;
      background-color: #f4e2b2;
      background-image: url("KRAFT");
      background-size: 384px 384px;
      background-repeat: repeat;
      color: #2a241c;
      font-family: "Kalam", "Comic Sans MS", cursive;
      font-size: 1.05rem;
      margin: 0.1rem 0 0.3rem;
      padding: 0.12rem 0.6rem 0.16rem;
      box-shadow: 1px 2px 4px rgba(40, 22, 8, 0.28);
      transform: rotate(-0.4deg);
    }
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] p {
      color: #2a241c !important;
      font-family: "Kalam", "Comic Sans MS", cursive !important;
    }
    button[data-testid="stBaseButton-segmented_control"] {
      background: #fffdf8 !important;
      border: 2px solid #3a3228 !important;
      box-shadow: none !important;
    }
    button[data-testid="stBaseButton-segmented_control"] p {
      color: #1a2744 !important;
      font-family: "Kalam", "Comic Sans MS", cursive !important;
      font-weight: 700 !important;
    }
    button[data-testid="stBaseButton-segmented_control"]:hover {
      background: #efe2c4 !important;
    }
    button[data-testid="stBaseButton-segmented_controlActive"] {
      background: #1a3a78 !important;
      border: 2px solid #1a3a78 !important;
    }
    button[data-testid="stBaseButton-segmented_controlActive"] p {
      color: #f7f1e4 !important;
      font-family: "Kalam", "Comic Sans MS", cursive !important;
      font-weight: 700 !important;
    }
    .stApp:has(.week-report)::before {
      content: "";
      position: fixed;
      inset: 0;
      background: rgba(28, 18, 10, 0.5);
      z-index: 30;
    }
    div[data-testid="stVerticalBlock"]:has(.week-report):not(:has(div[data-testid="stHorizontalBlock"])) {
      position: fixed;
      z-index: 40;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
      width: min(38rem, 92vw);
      max-height: 78vh;
      overflow: auto;
      background-color: #f7f4ee;
      background-image: url("LINED");
      background-size: 560px auto;
      background-position: left top;
      padding: 0.9rem 1.1rem 0.7rem;
      box-shadow: 0 18px 40px rgba(20, 10, 4, 0.5);
    }
    .week-report .kicker {
      font-family: "Caveat", "Comic Sans MS", cursive;
      font-size: 1.8rem;
      color: #6a5018;
      line-height: 1;
    }
    .week-report p,
    .week-report .dayline {
      font-family: "Kalam", "Comic Sans MS", cursive;
      color: #1a2744;
      font-size: 1.05rem;
      margin: 0.2rem 0;
    }
    </style>
"""
for _token, _file in {
    "WOOD": "wood.jpg",
    "LINED": "lined.jpg",
    "STICKY": "sticky.jpg",
    "KRAFT": "kraft.png",
    "GRAPH_WHITE": "graph-white.png",
}.items():
    _DESK_CSS = _DESK_CSS.replace(_token, _photo(_file))

st.markdown(
    _DESK_CSS,
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


# Voice file, the big sign, and the line David actually says.
# Same close always picks the same joke. A different day can get a different one.
_JOKES = {
    "bust": (
        ("jimmy.wav", "NO COLLEGE", "No college for Jimmy."),
        ("crime.wav", "CRIME SCENE", "The account is a crime scene."),
    ),
    "wreck": (
        ("goes.wav", "THERE IT GOES", "There it goes."),
        ("mugged.wav", "MUGGED", "The market just mugged you."),
        ("fund.wav", "THE FUND", "There goes the college fund."),
    ),
    "nick": (
        ("top.wav", "OFF THE TOP", "Just a little off the top."),
    ),
    "push": (
        ("zero.wav", "CLOSE", "That was close."),
        ("nothing.wav", "NOTHING", "Flat. The most expensive nothing."),
        ("handshake.wav", "PUSH", "Push. Nobody got hurt."),
    ),
    "nibble_win": (
        ("lunch.wav", "LUNCH", "Lunch money, don't spend it all in one place."),
        ("pocket.wav", "POCKET", "Pocket change. Still green."),
        ("cocky.wav", "EASY", "Green. Do not get cocky."),
    ),
    "stacks": (
        ("stacks.wav", "FAT STACKS", "Fat stacks."),
        ("money.wav", "MONEY", "Money, money, money."),
        ("talking.wav", "TALKING", "Now we are talking."),
    ),
    "payday": (
        ("big.wav", "BIG MONEY", "Big money."),
        ("home.wav", "CAME HOME", "Fat stacks. The whole stake came home."),
        ("frame.wav", "SHE STAYS", "Maybe she won't leave you now."),
    ),
}


_BUCKETS = ("bust", "wreck", "nick", "push", "nibble_win", "stacks", "payday")


def _joke(game: Game, bucket: str) -> tuple[str, str, str]:
    """One unused line for this close. A later day in the week gets a different line."""
    picks = st.session_state.setdefault("voice_picks", {})
    week = st.session_state.week_id
    key = f"{week}:{len(game.history)}:{game.history[-1].day_name}"
    if key in picks:
        voice = picks[key]
        for options in _JOKES.values():
            for item in options:
                if item[0] == voice:
                    return item
    used = {
        voice
        for pick_key, voice in picks.items()
        if str(pick_key).startswith(f"{week}:") and pick_key != key
    }
    start = _BUCKETS.index(bucket)
    order = [bucket]
    for step in range(1, len(_BUCKETS)):
        if start - step >= 0:
            order.append(_BUCKETS[start - step])
        if start + step < len(_BUCKETS):
            order.append(_BUCKETS[start + step])
    for name in order:
        fresh = [item for item in _JOKES[name] if item[0] not in used]
        if fresh:
            choice = fresh[(game.seed + len(game.history)) % len(fresh)]
            picks[key] = choice[0]
            return choice
    choice = _JOKES[bucket][0]
    picks[key] = choice[0]
    return choice


def celebration(game: Game) -> tuple[str, str, str, str]:
    """Kind, headline, spoken line, and the voice file for a settled close.

    The joke follows the size of the day's profit against that morning's stake.
    """
    if not game.history or game.phase not in ("settled", "week_over"):
        return "", "", "", ""
    last = game.history[-1]
    stake = last.stake or 1.0
    if game.bankroll <= 0:
        voice, headline, line = _joke(game, "bust")
        return "explosion", headline, line, voice
    if last.profit <= -0.5 * stake:
        voice, headline, line = _joke(game, "wreck")
        return "sink", headline, line, voice
    if last.profit < -1e-6:
        voice, headline, line = _joke(game, "nick")
        return "sink", headline, line, voice
    if last.profit <= 1e-6:
        voice, headline, line = _joke(game, "push")
        return "push", headline, line, voice
    if last.profit >= stake:
        voice, headline, line = _joke(game, "payday")
        return "rocket", headline, line, voice
    if last.profit >= 0.5 * stake:
        voice, headline, line = _joke(game, "stacks")
        return "rocket", headline, line, voice
    voice, headline, line = _joke(game, "nibble_win")
    return "confetti", headline, line, voice


def cheer(game: Game) -> None:
    """Play the close once. A new week gets its own id so Monday can cheer again."""
    kind, headline, line, voice = celebration(game)
    token = ""
    if kind:
        token = f"{st.session_state.week_id}:{game.history[-1].day_name}:{voice}:8"
    _cheer_component(
        kind=kind,
        token=token,
        headline=headline,
        line=line,
        voice=voice,
        key="cheer",
    )


def term_sheet() -> str:
    """Short definitions, written on the quote page under vega and theta."""
    rows = (
        ("Call", "pays max(spot − strike, 0) at 16:00"),
        ("Put", "pays max(strike − spot, 0) at 16:00"),
        ("Strike", "fixed at this morning's open"),
        ("Premium", "price of one option at 09:30"),
        ("Breakeven", "spot where the payoff equals the premium"),
        ("Mark", "model value now. At 16:00 it is the payoff"),
        ("Units", "how many options the stake buys"),
        ("P&amp;L", "change in value since the open, all units"),
        ("Delta", "price change if the stock moves by 1"),
        ("Gamma", "how fast delta changes"),
        ("Vega", "price change for one volatility point"),
        ("Theta", "time decay over the next half-hour"),
    )
    cells = "".join(f"<div><b>{name}</b> {meaning}</div>" for name, meaning in rows)
    return f'<div class="term-sheet"><div class="kicker">Terms</div><div class="grid">{cells}</div></div>'


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
    reserved = 490
    room = max(320, int(viewport_height) - reserved)
    spot = max(180, int(room * 0.56))
    greek = max(140, room - spot)
    return spot, greek


_PAPER_CHART = {
    "axis": {
        "labelColor": "#1a1208",
        "titleColor": "#1a1208",
        "grid": False,
        "domainColor": "#3a3228",
        "labelFont": "Kalam, Comic Sans MS, cursive",
        "titleFont": "Kalam, Comic Sans MS, cursive",
        "labelFontSize": 15,
        "titleFontSize": 16,
        "labelFontWeight": "bold",
        "titleFontWeight": "bold",
    },
    "legend": {
        "labelColor": "#1a1208",
        "labelFont": "Kalam, Comic Sans MS, cursive",
        "labelFontSize": 15,
        "labelFontWeight": "bold",
    },
    "view": {"stroke": None},
}


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
        "background": "transparent",
        "height": height,
        "config": _PAPER_CHART,
        "layer": [
            {
                "data": {"name": "curve"},
                "mark": {"type": "line", "color": "#6a3b12", "strokeWidth": 2.6, "strokeCap": "round"},
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
                "mark": {"type": "rule", "strokeDash": [6, 4], "color": "#9b2d28"},
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
        "background": "transparent",
        "height": height,
        "config": _PAPER_CHART,
        "layer": [
            {
                "data": {"name": "path"},
                "mark": {"type": "line", "point": True, "color": "#1a3a78", "strokeWidth": 2.6, "strokeCap": "round"},
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
                            "range": ["#b45309", "#1f6b3a"],
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
        "background": "transparent",
        "height": height,
        "config": _PAPER_CHART,
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
                "mark": {"type": "rule", "strokeDash": [4, 4], "color": "#a89078"},
                "encoding": {
                    "y": {"field": "Versus open", "type": "quantitative", "scale": {"zero": False}}
                },
            },
            {
                "data": {"name": "series"},
                "mark": {"type": "line", "point": True, "strokeWidth": 2.4, "strokeCap": "round"},
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
                        "scale": {
                            "domain": ["Delta", "Gamma", "Theta", "Vega"],
                            "range": ["#1a3a78", "#6a3b12", "#9b2d28", "#1f6b3a"],
                        },
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


def week_board(game: Game) -> str:
    """Five day chips. Settled days take the color of that day's profit."""
    chips = []
    for index, name in enumerate(SHORT_DAYS):
        classes = ["day"]
        if index < len(game.history):
            profit = game.history[index].profit
            classes.append("up" if profit >= 0 else "down")
            detail = f"{profit:+,.0f}"
        elif game.phase != "week_over" and index == game.day_index:
            classes.append("now")
            detail = "live" if game.phase == "playing" else "open"
        else:
            detail = "—"
        chips.append(
            f'<div class="{" ".join(classes)}"><div class="name">{name}</div>'
            f'<div class="result">{detail}</div></div>'
        )
    return '<div class="week">' + "".join(chips) + "</div>"


def score_html(game: Game) -> tuple[str, str]:
    equity = game.equity()
    multiple = equity / game.starting_bankroll
    if multiple > 1:
        tone = "mult up"
    elif multiple < 1:
        tone = "mult down"
    else:
        tone = "mult flat"
    cash = (
        '<div class="score"><div class="kicker">Bankroll</div>'
        f'<div class="cash">{money(equity)}</div></div>'
    )
    mult = (
        '<div class="score"><div class="kicker">Multiple</div>'
        f'<div class="{tone}">{multiple:.2f}x</div></div>'
    )
    return cash, mult


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


def painted(label: str, text: str) -> str:
    if label != "P&L" or text in ("0.00", "expired"):
        return f"**{text}**"
    tone = "down" if text.startswith("-") else "up"
    return f'<span class="{tone}">{text}</span>'


def draw_pairs(pairs: list[tuple[str, str]]) -> None:
    for left, right in zip(pairs[0::2], pairs[1::2]):
        left_col, right_col = st.columns(2)
        left_col.caption(left[0])
        left_col.markdown(painted(left[0], left[1]), unsafe_allow_html=True)
        right_col.caption(right[0])
        right_col.markdown(painted(right[0], right[1]), unsafe_allow_html=True)


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


def show_week_report(game: Game) -> None:
    """A sheet that stays up after the week and recounts each day."""
    if not game.history:
        return
    lines = []
    for day in game.history:
        if day.profit > 1e-6:
            tone = "up"
        elif day.profit < -1e-6:
            tone = "down"
        else:
            tone = "flat"
        lines.append(
            f'<div class="dayline"><b>{day.day_name}</b> {day.right}. '
            f"Stake {money(day.stake)}. Close {day.close_spot:,.2f}. "
            f'<span class="{tone}">{day.profit:+,.2f}</span></div>'
        )
    multiple = game.bankroll / game.starting_bankroll
    if game.bankroll <= 0:
        ending = "The bankroll is gone."
    else:
        ending = f"Finished at {money(game.bankroll)}, {multiple:.2f} times the 10,000 start."
    if len(game.history) > 1:
        best = max(game.history, key=lambda day: day.profit)
        worst = min(game.history, key=lambda day: day.profit)
        note = (
            f"Best day {best.day_name} ({best.profit:+,.2f}). "
            f"Worst day {worst.day_name} ({worst.profit:+,.2f})."
        )
    else:
        note = ""
    st.markdown(
        '<div class="week-report"><div class="kicker">Week report</div>'
        "<p>Hypothetical. Each morning's stake came out of the bankroll.</p>"
        + "".join(lines)
        + f"<p><b>{ending}</b> {note}</p></div>",
        unsafe_allow_html=True,
    )
    if st.button("Fold the report"):
        st.session_state.hide_report = True
        st.rerun()


def run_action(game: Game) -> None:
    if game.phase == "choose":
        if st.button("Buy at the open", type="primary"):
            label, fraction = chosen_stake()
            game.start_day(chosen_contract(), fraction)
            st.session_state["locked_stake"] = label
            st.rerun()
        return
    if game.phase == "playing":
        label = "Settle at 16:00" if game.steps_taken == STEPS_PER_SESSION - 1 else "Advance 30 minutes"
        if st.button(label, type="primary"):
            game.advance()
            st.rerun()
        return
    if game.phase == "settled" and st.button("Next morning", type="primary"):
        game.next_day()
        st.rerun()


if "week_id" not in st.session_state:
    st.session_state.week_id = 1
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
        st.session_state.week_id += 1
        st.session_state.hide_report = False
        st.session_state.voice_picks = {}
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
cheer(game)
cash_html, multiple_html = score_html(game)
days_box.markdown(week_board(game), unsafe_allow_html=True)
equity_box.markdown(cash_html, unsafe_allow_html=True)
multiple_box.markdown(multiple_html, unsafe_allow_html=True)
st.markdown(f'<p class="on-wood">{status_line(game)}</p>', unsafe_allow_html=True)

left, stage = st.columns([1.22, 3.15], gap="small")

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
        st.markdown(term_sheet(), unsafe_allow_html=True)
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
        st.markdown(term_sheet(), unsafe_allow_html=True)

with stage:
    spot_col, cliff_col = st.columns(2, gap="small")
    with spot_col:
        st.markdown('<div class="chart-page sheet-graph"></div>', unsafe_allow_html=True)
        st.caption("Spot, strike, and breakeven")
        show_chart(
            spot_chart(view_clocks, view_spots, view_strike, view_line, spot_height),
            "spot_chart",
        )
    with cliff_col:
        st.markdown('<div class="chart-page sheet-graph"></div>', unsafe_allow_html=True)
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
    with st.container(border=True):
        st.markdown('<div class="greek-page"></div>', unsafe_allow_html=True)
        st.caption(
            "Delta, gamma, vega, and theta on one scale: each divided by its 09:30 value. "
            "1.00 means unchanged. The dashed line is 1.00. Lines stop at 15:30, when the quote ends."
        )
        if not greek_data.empty:
            show_chart(greek_chart(greek_data, greek_height), "greek_chart")

if game.phase == "week_over" and not st.session_state.get("hide_report"):
    with st.container():
        show_week_report(game)

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
