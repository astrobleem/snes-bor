# TEXT-1 — inherited DrawString reliability / observation defect

TEXT-1 was positively reproduced before G14 at `e5d3583f52407fdb0ea180bb90d1d293d6afc7a4`:

- `game_g1_text.py`: FAIL twice
- `game_g5_menus.py`: FAIL twice
- `game_g10_ending_credits.py`: FAIL twice

The current G14 tree reproduces the same DrawString-class failures. This is
not a G14 regression and the checks remain exact; they are not relabeled PASS.

Known-good portions are DrawNumber, font palette, priority bits, state
transitions, gameplay, and G14 presentation. G14 did separately expose and
fix a real single-`TextStaging` collision between P1/P2 HUD text.

A representative raw G1 row contained words such as `2554 2539 2520 ...`,
while the numeric row correctly contained `2531 2530 2532 2534` (`1024`).

Classification: source/observation boundary unresolved, predating G14. TEXT-1
blocks final release-quality presentation, does not invalidate accepted G13
gameplay, and does not block G14 behavioral acceptance once G14-specific
presentation/regressions pass.

G14 policy remains P1 selectable normally and P2 fixed LEO with explicit
player-facing presentation. G15 campaign audit may proceed with TEXT-1 open,
but final campaign/release acceptance must not claim presentation-complete
until TEXT-1 is resolved or independently proven verifier-only.
