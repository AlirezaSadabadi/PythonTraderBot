"""Generate a simple sample trade database + test HTML report
for SP2L_Advanced_Bot_Optimized_DB_UI.

Run:  python make_test_DB_UI.py
Out:  SP2L_Advanced_Bot_Optimized_DB_UI_log.json
      SP2L_Advanced_Bot_Optimized_DB_UI_report.html
"""

import io
import json
import os
import random
import sys
from datetime import datetime, timedelta

SRC = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "SP2L_Advanced_Bot_Optimized_DB_UI.py"
)
sys.path.insert(0, os.path.dirname(SRC))

# Load only the top of the real bot (imports + logging engine)
# so the report uses the exact same code path as production.
source = io.open(SRC, encoding="utf-8").read()
head = source.split("# MT5 INITIALIZE")[0]

ns = {"__name__": "__test__", "__file__": SRC}
exec(compile(head, SRC, "exec"), ns)

log_event = ns["log_event"]
ns["log_settings"].update({
    "symbol": "XAUUSD",
    "timeframe": "M1",
    "spike_candle_size": 1.5,
    "pgap_points": 100,
    "max_sl_distance_points": 1000,
    "tp_r": 1.0,
    "use_second_entry": True,
    "second_entry_volume_multiplier": 2.0,
    "use_ema_filter": True,
    "ema_period": 60,
    "use_trend_filter": True,
    "max_opposite_moves": 1,
    "use_range_filter": False,
    "adx_period": 14,
    "min_adx": 20.0,
    "use_adx_rising_filter": False,
    "use_session_filter": False,
    "session_timezone": "America/New_York",
    "magic": 8,
    "second_entry_magic": 9,
    "lot": 0.01,
    "loop_seconds": 0.5,
    "broker_point": 0.01,
    "digits": 2,
})

ns["log_account"].update({
    "login": 5551234,
    "server": "TestBroker-Demo",
    "leverage": 100,
    "balance": 10000.0,
    "equity": 10042.35,
    "profit": 42.35,
})

log_event("bot_start")
log_event("account_info", **dict(ns["log_account"]))

random.seed(7)

ticket = 9000
day = datetime(2026, 10, 5, 8, 0, 0)

for i in range(12):

    direction = random.choice(["BUY", "SELL"])
    second = random.choice([False, False, True])
    risk = round(random.uniform(1.0, 3.5), 2)
    price = round(random.uniform(2600.0, 2680.0), 2)
    sl = round(price - risk, 2) if direction == "BUY" else round(price + risk, 2)
    tp = round(price + risk, 2) if direction == "BUY" else round(price - risk, 2)
    win = random.random() > 0.42
    profit = round(risk * (1 if win else -1) * 100, 2)

    ticket += 1
    setup_time = str(day)
    log_event(
        "pending_setup",
        symbol="XAUUSD",
        direction=direction,
        setup_time=setup_time,
        sl=sl,
        spike_body=round(risk / 2, 2),
    )

    day += timedelta(seconds=45)
    entry_time = str(day)

    log_event(
        "order_opened",
        label="first_entry",
        symbol="XAUUSD",
        direction=direction,
        magic=8,
        ticket=ticket,
        volume=0.01,
        signal_entry=price,
        sl=sl,
        tp=tp,
        risk=risk,
        second_entry=round(price - risk / 2 if direction == "BUY"
                           else price + risk / 2, 2),
        setup_time=setup_time,
        entry_time=entry_time,
        spike_body=round(risk / 2, 2),
    )

    if second:
        ticket += 1
        log_event(
            "order_opened",
            label="second_entry",
            symbol="XAUUSD",
            direction=direction,
            magic=9,
            ticket=ticket,
            volume=0.02,
            signal_entry=round(price - risk / 2 if direction == "BUY"
                               else price + risk / 2, 2),
            sl=sl,
            tp=tp,
            trigger_price=price,
            pullback_touched=True,
            setup_time=setup_time,
            entry_time=entry_time,
        )
        log_event(
            "second_position_closed",
            label="second_entry",
            symbol="XAUUSD",
            magic=9,
            ticket=ticket,
            profit=round(profit / 2, 2),
            close_time=str(day + timedelta(minutes=random.randint(3, 40))),
            comment="tp/sl (test data)",
        )
        ticket -= 1

    day += timedelta(minutes=random.randint(5, 60))
    log_event(
        "position_closed",
        label="first_entry",
        symbol="XAUUSD",
        direction=direction,
        magic=8,
        ticket=ticket,
        profit=profit,
        close_time=str(day),
        comment="tp/sl (test data)",
    )

    day += timedelta(minutes=random.randint(10, 90))

ns["status"] = False
ns["buy"] = False
ns["sell"] = False

# Force the real exit handler so the report is produced
# exactly like on Ctrl+C.
ns["html_exported"]["done"] = False
ns["_on_process_exit"]()

print()
print("Open the report in a browser:")
print(" ", ns["HTML_EXPORT_PATH"])
