# PLAN.md

The team's working plan. Agents read and update this file, so a new session can pick up where
the last one stopped. Keep it short; replace old content instead of adding to it.

## Current goal
A local Monday–Friday 0DTE game: half-hour clicks, a compounding bankroll, and the Greeks along the path.

## Decisions so far
- 2026-11-18: One session is 1/252 of a year, split into 13 half-hours. Moves use the same volatility as the price. The strike is that morning's spot. The stake is 25, 50, or 100 percent of the bankroll. The next morning opens at today's close. Starting cash is 10,000, hypothetical.
- 2026-11-18: Charts keep fixed dataset names and a stable key, so a half-hour step updates the lines in place. `fit_page` sizes the spot row and the Greek chart to the browser window.
- 2026-11-18: The desk uses a navy and gold theme. Day chips turn green or rose with that day's profit. The saved checkpoint before this look is the first git commit.
- 2026-11-18: The 16:00 close plays once, in trading language: PAID or PAYDAY with coins, UNDERWATER with a sinking ship, WIPED OUT with an explosion. The term sheet is a sticky note under vega and theta. The page sits on one continuous reddish desk top, grain running across, with a darker rim. The room around it is dark. The top strip and the method bar are a sharp manila grain at its own pixel size. The contract page is college-ruled paper. The three charts each sit on their own drawn sheet of graph paper, and the axis lettering is bold. The desk top is a sharper crop of the same reddish surface. A close speaks one deep-voice joke, a bit quicker than the first take, and a different line each day of the week. A losing close that used to show a sinking ship now shows an explosion animation. The same close keeps the same joke. A finished week leaves a report on the desk. Photo licenses are in assets/desk/SOURCES.txt.

## Next steps
1. The team adds names, runs the critic, and decides whether to deploy.

## Open questions
- Whether the group wants a coarser clock for the live demo.
