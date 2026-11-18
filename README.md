# 0DTE Week

MSF 8615 Derivatives, Villanova University · Team: [names]

**Live app:** [Streamlit link, once deployed]

> **Using this template.** On this page, click **Use this template → Create a new repository**
> (one per team), then invite your teammates. Work in that new repository, not here: a Codespace
> opened on the template itself saves your commits as a fork of the template, which is public.
> Then replace every [bracketed] placeholder below and delete this note.

## The question
If you buy a fairly priced at-the-money 0DTE call or put each morning and bet the cash again through Friday, what happens to the bankroll, and how do the Greeks change as the clock runs out?

## Inputs and outputs
- **Inputs:** call or put, a stake of 25%, 50%, or 100% of the hypothetical bankroll, and a click that advances the session 30 minutes. A new week also takes Monday's open, annual volatility, the risk-free rate, and a random seed.
- **Outputs:** the Black-Scholes mark, breakeven spot, profit versus premium, and the four Greeks at the current spot and time. One chart shows the spot against the strike and breakeven. One shows delta across spot. One shows delta, gamma, vega, and theta together, each divided by its value at 09:30. Friday's bankroll is the score.

## Data
No market file. Every price is a model value from the assumptions in the sidebar, and every underlying move is a draw from that same volatility. The bankroll is hypothetical. Label on screen: European, no dividend, constant volatility, no bid-ask, no overnight gap.

| File in `data/` | Source | Date and time saved | Terms of use: can it be public? |
|---|---|---|---|
| none | Model inputs only. Nothing was downloaded. | | |

- Save market data as dated files, for example `cboe_spx-options_2026-10-20.csv`, and show the date
  on screen.
- Licensed data (Bloomberg, FactSet, Risk.net, WRDS, ...) does not go into a public repository or
  into AI tools. Keep it in `data/licensed/` (ignored by git) and run your code on it yourself.
- Hypothetical inputs and stress scenarios are fine. Label them as such.

## Method
Each morning's option is struck at that morning's spot and priced with the Black-Scholes-Merton formula for a European call or put on a non-dividend underlying (Hull, Chapter 15; the worked example is the price check in `tests/test_pricing.py`). Delta, gamma, vega, and theta are the partial derivatives of that price. Theta is the derivative as calendar time moves forward, so it equals minus the derivative with respect to time left.

One session is 1/252 of a year, split into 13 half-hours. A click draws a standard normal Z and sets

log(S_new / S) = (r − ½ σ²) Δt + σ √Δt · Z

with Δt = 1/(252 × 13) and the same σ that set the premium. At 16:00 the option pays its intrinsic value. Cash left is the unspent bankroll plus the number of units times that payoff. The next morning opens at today's close. There is no overnight move.

Because the option is bought at the volatility used to draw the path, the bet is fair before luck. Breakeven still sits beyond the strike by the premium, so a long option often expires worthless. Letting the winnings ride is how a week ends at zero or at a large multiple of the 10,000 starting cash.

## Tests
Run `pytest`. Each test compares the code with a number checked independently:
- `tests/test_pricing.py`: Black-Scholes prices match Hull's Chapter 15 example; put-call parity holds. Greeks match a finite-difference bump of the same formula. The Black-Scholes PDE residual is about zero. At zero time left the price is the intrinsic payoff. One session is 1/252 of a year.
- `tests/test_game.py`: the same seed replays the same day; the first step matches the risk-neutral draw rebuilt from that seed; settled cash equals unspent bankroll plus units times intrinsic value; the next morning opens at the previous close.

The agent skill in `.agents/skills/check-the-numbers/` tells coding agents how to add checks like these.

## How to run
In a GitHub Codespace, or in VS Code on your laptop (first follow
[`docs/local-setup.md`](docs/local-setup.md); this also works where Codespaces are blocked):
```
pip install -r requirements.txt
pytest
streamlit run app.py
```
New to Streamlit? [`docs/streamlit.md`](docs/streamlit.md) explains how an app works (the script
reruns from top to bottom on every click), with caching, layout and deployment.

## Limitations
The path is a scenario, not an observed price. Volatility is constant, so there is no smile and no jump. The player is long and unhedged, with no bid-ask and with fractional units. A half-hour is one thirteenth of a trading day, not 30 calendar minutes. The score is one seeded week of a fair game, not evidence of an edge.

## AI use
[Short summary. Details in `AI_LOG.md`.]

## Team contributions
| Name | GitHub username | Main contributions |
|---|---|---|
| | | |

---

## Project objective: explain and verify
The team can explain what the app computes, why the method fits the question, and how each
displayed number was verified, and every member presents part of the group demo. The team is
responsible for the output, whoever or whatever wrote the code. The evidence: tests against
independent numbers (`tests/`) and `AI_LOG.md` (AI use, the critic's review, examiner practice),
scored against [`RUBRIC.md`](RUBRIC.md). Every member also makes at least one commit under their
own GitHub account (criterion 7).

## Files in this repository
| File | Who uses it | What it is for |
|---|---|---|
| `README.md` | You | This page: the question, data, method, checks, limitations and team |
| `AI_LOG.md` | You | How you used AI, the critic's findings and your fixes, and examiner practice |
| `RUBRIC.md` | You read it | How the app is graded |
| `AGENTS.md` | The agent | Standing rules it reads every session. Add a rule when it repeats a mistake |
| `PLAN.md` | The agent | Notes on the current task, so a new session can pick up where the last one stopped |
| `app.py`, `pricing.py`, `tests/`, `data/` | Code | The page, the formulas, the checks, the dated data files |
| `docs/` | You, when needed | Guides: [laptop setup](docs/local-setup.md), [coding agents](docs/agent-setup.md), [Streamlit](docs/streamlit.md), [git as a team](docs/git-and-teamwork.md) |

To read a `.md` file with its formatting: on github.com, click it. In a Codespace, right-click it
and choose **Open Preview** (Ctrl+Shift+V).

## Working with agents
Set up the agent you want with [`docs/agent-setup.md`](docs/agent-setup.md): GitHub Copilot (free
for students), Antigravity CLI, Codex or Claude Code. All of them read `AGENTS.md`. Use each tool's
built-in plan mode to plan a step. Two review helpers live in `.github/agents/`:
- `critic`: adversarial review in a new session; cannot edit files; findings go in `AI_LOG.md`
- `examiner`: asks practice questions for the group demo and scores them against `RUBRIC.md`

In Copilot, pick them from the agent menu. In other tools, start a new session and ask the agent
to read the file and follow it (`docs/agent-setup.md` has the prompt).

## Working as a team
See [`docs/git-and-teamwork.md`](docs/git-and-teamwork.md): pull before you start, one owner per
file, push when a piece of work is done, and what to do when git reports a merge conflict.
