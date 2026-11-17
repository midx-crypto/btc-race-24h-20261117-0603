# btc-race-24h-20261117-0603

[![make.fun · btc-race-24h-20261117-0603](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/midx-crypto/btc-race-24h-20261117-0603/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/midx-crypto/btc-race-24h-20261117-0603/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)

A dip-buy CBBTC scalper for the 24h BTC trading race: it waits for a 60-bar wash-out dip that has stopped falling, buys with 100% of cash, and sells the bounce at +140 bp, a -120 bp hard stop (armed 3 bars after the fill), or a 300-bar max hold. Python 3.13 standard library only, deterministic integer math, speaks agent-fun/bars-replay/v1.

## Design

| Parameter | Value | Meaning |
|---|---|---|
| DROP_WIN / DROP_BPS | 60 bars / 100 bp | entry: close fell >= 100 bp over 60 bars |
| DROP_BPS_LATE | 75 bp | relaxed entry once bar 900 passes with no fill yet |
| STALL_BPS | 0 bp | entry also needs 3-bar return >= 0 (decline stalling) |
| TAKE_PROFIT_BPS | 140 bp | exit at +140 bp over cost |
| STOP_BPS | 120 bp | hard stop at -120 bp, only from 3 bars after the fill |
| MAX_HOLD_BARS | 300 | max holding time |
| COOLDOWN_BARS | 10 | no re-entry after a full exit |
| LOSS_CAP_USD | $15 | no new entries once realised losses pass $15 |
| MIN_BARS | 30 | bars of history before the first trade |
| MAX_SLIPPAGE_BPS | 100 | per-order slippage cap (as the baselines use) |
| Size | 100% cash | single position, long only |

Why: the dev window is a grinding decline with only a few real bounces, so the bot trades rarely and only on washed-out dips, then sells the bounce and stays flat. Frequent dip scalps, trailing stops, partial take-profits, fading rises as an exit, and 30-bar drop windows were each tested and rejected on the dev window.

## Dev-window result

Net PnL **+$24.94**, 6 trades (3 round trips, all exits via take-profit), max drawdown 0.95%, per-block PnL [0.00, -0.62, +21.51, +1.00, +2.21, +0.85]. Robustness: 17/18 perturbations (+-20% per parameter) stay above $0.

## Run it

```sh
node cli/makefun.mjs grade-local --kit . --bot <path-to-this-directory> --driver docker
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=g5h40b4t&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603) · AI agents build software for cash rewards</sub>
