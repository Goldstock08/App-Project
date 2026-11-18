# PLAN.md

The team's working plan. Agents read and update this file, so a new session can pick up where
the last one stopped. Keep it short; replace old content instead of adding to it.

## Current goal
A local Monday–Friday 0DTE game: half-hour clicks, a compounding bankroll, and the Greeks along the path.

## Decisions so far
- 2026-11-18: One session is 1/252 of a year, split into 13 half-hours. Moves use the same volatility as the price. The strike is that morning's spot. The stake is 25, 50, or 100 percent of the bankroll. The next morning opens at today's close. Starting cash is 10,000, hypothetical.
- 2026-11-18: Charts keep fixed dataset names and a stable key, so a half-hour step updates the lines in place. `fit_page` sizes the spot row and the Greek chart to the browser window.

## Next steps
1. The team adds names, runs the critic, and decides whether to deploy.

## Open questions
- Whether the group wants a coarser clock for the live demo.
