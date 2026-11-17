"""Dip-buy CBBTC scalper for make.fun btc-race-24h (agent-fun/bars-replay/v1).

Design: long only, one position, 100% cash. The dev window (1440 1-minute
cbBTC bars) is a grinding decline with only a few real bounces, so the bot
waits for a washed-out dip and sells the bounce; it stays flat the rest of
the time. All math is deterministic integer math; no clock, no environment,
no randomness, so two runs on the same bars produce the same orders.

Entry (flat only): the close has fallen at least DROP_BPS over the last
DROP_WIN bars AND the 3-bar return is at least STALL_BPS (the decline is
stalling, not still falling). Once bar 900 passes with no fill yet, the drop
threshold relaxes to DROP_BPS_LATE so a late shallow dip can still trade.
At least MIN_BARS of history before the first trade; no re-entry for
COOLDOWN_BARS bars after a full exit; no new entries once realised losses
pass LOSS_CAP_USD.

Exit (whichever comes first): take-profit at TAKE_PROFIT_BPS over cost,
hard stop at STOP_BPS under cost (armed only GRACE_BARS bars after the
fill, so a crash entry is not stopped out at the day's low), or
MAX_HOLD_BARS bars held. Returns are measured on value/cost at the close;
fills land at the next bar's open. Every order carries
MAX_SLIPPAGE_BPS, as the baselines do.

Deliberately NOT used (each tested and rejected on the dev window):
trailing stops, partial take-profits, fading rises as an exit, 30-bar
drop windows.

Dev-window result (kit's frozen window): net PnL about +$24.94, 6 trades
(3 round trips, all exits via take-profit), max drawdown about 0.95%.
"""

import json
import sys

# --- Tuned parameters (dev window: 1440 1-minute cbBTC bars) ---
DROP_WIN = 60
DROP_BPS = 100
DROP_BPS_LATE = 75
STALL_BPS = 0
TAKE_PROFIT_BPS = 140
STOP_BPS = 120
GRACE_BARS = 3
MAX_HOLD_BARS = 300
COOLDOWN_BARS = 10
LOSS_CAP_USD = 15
MIN_BARS = 30
MAX_SLIPPAGE_BPS = 100

SYMBOL = "CBBTC"
MIN_NOTIONAL = 1000000  # 1 USDC, in quote units (quote_scale 6)


class Bot:
    """Dip-buy scalper state. Closes are integer prices (price_scale 5);
    cash, cost and realised PnL are integer quote units (quote_scale 6)."""

    def __init__(self, cash):
        self.closes = []
        self.cash = cash
        self.qty = 0
        self.cost = 0
        self.entry_bar = -1
        self.buy_fills = 0
        self.cool_until = -1
        self.realized = 0
        self.warmup_bars = 0
        self._next = 1

    def _cid(self):
        cid = "o%d" % self._next
        self._next += 1
        return cid

    def decide(self, i):
        """Orders for the batch of bar i (i indexes self.closes)."""
        if i < MIN_BARS:
            return []
        c = self.closes[i]
        if self.qty > 0:
            val = self.qty * c // 10**7
            ret_bps = (val - self.cost) * 10000 // self.cost if self.cost > 0 else 0
            hold = i - self.entry_bar
            if (ret_bps >= TAKE_PROFIT_BPS
                    or (hold >= GRACE_BARS and ret_bps <= -STOP_BPS)
                    or hold >= MAX_HOLD_BARS):
                self.cool_until = i + COOLDOWN_BARS
                return [{"side": "sell", "client_id": self._cid(), "symbol": SYMBOL,
                         "qty": str(self.qty),
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
            return []
        if i <= self.cool_until:
            return []
        if self.realized <= -LOSS_CAP_USD * 1000000:
            return []
        if i < DROP_WIN:
            return []
        threshold = DROP_BPS_LATE if (i > 900 and self.buy_fills == 0) else DROP_BPS
        drop = (self.closes[i - DROP_WIN] - c) * 10000 // self.closes[i - DROP_WIN]
        if drop < threshold:
            return []
        up3 = (c - self.closes[i - 3]) * 10000 // self.closes[i - 3]
        if up3 < STALL_BPS:
            return []
        if self.cash < MIN_NOTIONAL:
            return []
        return [{"side": "buy", "client_id": self._cid(), "symbol": SYMBOL,
                 "notional_quote_units": str(self.cash),
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]


def run():
    """Speak agent-fun/bars-replay/v1: hello once, one reply per batch, then done.

    Each batch carries the bar that just closed, the fills of the orders
    sent on the previous batch, and the account. Orders decided on a batch
    fill at the next bar's open. Exactly one reply per batch, echoing its
    seq. Diagnostics go to stderr; stdout carries replies only.
    """
    bot = None
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        kind = msg.get("type")
        if kind == "hello":
            bot = Bot(int(msg["capital"]["quote_units"]))
            bot.warmup_bars = int(msg.get("warmup_bars", 0))
            continue
        if kind == "done":
            break
        if kind != "batch" or bot is None:
            continue
        seq = msg["seq"]
        buy_filled_here = False
        for f in msg.get("fills", []):
            if f.get("status") != "filled" or f.get("symbol") != SYMBOL:
                continue
            if f["side"] == "buy":
                bot.qty = int(f["qty"])
                bot.cost = int(f["notional_quote_units"])
                bot.buy_fills += 1
                buy_filled_here = True
            elif f["side"] == "sell":
                bot.realized += int(f["notional_quote_units"]) - bot.cost
                bot.qty = 0
                bot.cost = 0
        acct = msg.get("account", {})
        if "cash_quote_units" in acct:
            bot.cash = int(acct["cash_quote_units"])
        orders = []
        bar = None
        for b in msg.get("bars", []):
            if b.get("symbol") == SYMBOL:
                bar = b
                break
        if bar is not None:
            bot.closes.append(int(bar["c"]))
            i = len(bot.closes) - 1
            if buy_filled_here:
                bot.entry_bar = i
            if seq >= bot.warmup_bars:
                orders = bot.decide(i)
        sys.stdout.write(json.dumps({"type": "reply", "seq": seq, "orders": orders},
                                    separators=(",", ":")) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    run()
