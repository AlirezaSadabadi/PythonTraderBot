#!/usr/bin/env python
__author__ = "Alireza Sadabadi"
__copyright__ = "Copyright (c) 2026 Alireza Sadabadi. All rights reserved."
__credits__ = ["Alireza Sadabadi"]
__license__ = "Apache"
__version__ = "7.0"
__maintainer__ = "Alireza Sadabadi"
__email__ = "alirezasadabady@gmail.com"
__status__ = "Test"
__doc__ = "you can see the tutorials in https://youtube.com/@alirezasadabadi?si=d8o7LK_Ai1Hf68is"

import MetaTrader5 as mt5
from datetime import datetime, timezone, time, timedelta
import time as time_module
from zoneinfo import ZoneInfo
from Meta import *
from colorama import init as colorama_init
from colorama import Fore
from colorama import Style
import socket
import sys
import pandas as pd
import numpy as np
import json
import os
import atexit
import signal
from html import escape
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box as rich_box

colorama_init()

# ============================================================
# RICH CONSOLE UI
# ============================================================

console = Console()

STYLE_BUY = "bold green"
STYLE_SELL = "bold red"
STYLE_SETUP = "bold cyan"
STYLE_WARN = "bold yellow"
STYLE_SECOND = "bold magenta"


def value_panel(title, rows, style="cyan"):
    """Small two-column key/value panel used across the UI."""

    table = Table(
        box=rich_box.SIMPLE,
        show_header=False,
        border_style=style,
        padding=(0, 1),
    )

    table.add_column("field", style="grey70", no_wrap=True)
    table.add_column("value", justify="right")

    for field, value in rows:
        table.add_row(str(field), str(value))

    return Panel(
        table,
        title=title,
        title_align="left",
        border_style=style,
        padding=(1, 2),
    )


# ============================================================
# JSON ORDER LOG + HTML REPORT
#
# Every order-related event is appended to an in-memory list
# and immediately flushed to a JSON file next to this script,
# so a crash never loses already-logged orders.
#
# When the process exits (Ctrl+C) a self-contained HTML report
# is generated containing the settings, account info, current
# state and every single logged event / order.
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

JSON_LOG_PATH = os.path.join(
    BASE_DIR,
    "SP2L_Advanced_Bot_Optimized_DB_UI_log.json"
)

HTML_EXPORT_PATH = os.path.join(
    BASE_DIR,
    "SP2L_Advanced_Bot_Optimized_DB_UI_report.html"
)

BOT_STARTED_AT = datetime.now(
    timezone.utc
).strftime(
    "%Y-%m-%d %H:%M:%S"
)

BOT_START_PERF = time_module.perf_counter()

order_log = []
order_seq = {"value": 0}

log_settings = {}
log_account = {}
html_exported = {"done": False}


def _now_string():
    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def build_log_payload():
    return {
        "bot": "SP2L_Advanced_Bot_Optimized_DB_UI",
        "version": __version__,
        "started_at": BOT_STARTED_AT,
        "exported_at": _now_string(),
        "settings": log_settings,
        "account": log_account,
        "records": order_log,
    }


def log_event(event, **fields):
    """Append one event to the order log and flush to JSON."""

    order_seq["value"] += 1

    record = {
        "seq": order_seq["value"],
        "time": _now_string(),
        "event": event,
    }
    record.update(fields)

    order_log.append(record)

    try:
        with open(
            JSON_LOG_PATH,
            "w",
            encoding="utf-8"
        ) as log_file:
            json.dump(
                build_log_payload(),
                log_file,
                indent=2,
                default=str
            )
    except BaseException as e:
        print("JSON log write failed:", e)

    return record


def find_open_ticket(symbol, magic):
    """Return the MT5 ticket of an open position for magic."""

    try:
        positions = mt5.positions_get(symbol=symbol)

        if positions is None:
            return None

        for position in positions:

            if int(position.magic) == int(magic):
                return int(position.ticket)

    except BaseException as e:
        print("find_open_ticket exception:", e)

    return None


def get_position_close_info(position_ticket):
    """Resolve profit / close time of a closed MT5 position."""

    info = {
        "profit": None,
        "close_time": None,
        "comment": None
    }

    if position_ticket is None:
        return info

    try:
        now = datetime.now()

        deals = mt5.history_deals_get(
            now - timedelta(days=7),
            now
        )

        if deals is None:
            return info

        found = False
        total = 0.0

        for deal in deals:

            if int(deal.position_id) != int(position_ticket):
                continue

            if int(deal.entry) != int(mt5.DEAL_ENTRY_OUT):
                continue

            found = True

            total += float(deal.profit)
            total += float(
                getattr(deal, "commission", 0.0) or 0.0
            )
            total += float(
                getattr(deal, "swap", 0.0) or 0.0
            )

            info["close_time"] = str(
                datetime.fromtimestamp(int(deal.time))
            )
            info["comment"] = str(deal.comment)

        if found:
            info["profit"] = total

    except BaseException as e:
        print("get_position_close_info exception:", e)

    return info


def _kv_table(dictionary):
    rows = "".join(
        f"<tr><td class='key'>{escape(str(key))}</td>"
        f"<td>{escape(str(value))}</td></tr>"
        for key, value in dictionary.items()
    )
    return f"<table class='kv'>{rows}</table>"


REPORT_COLUMNS = [
    ("seq", "#"),
    ("time", "Time (UTC)"),
    ("event", "Event"),
    ("label", "Label"),
    ("symbol", "Symbol"),
    ("direction", "Dir"),
    ("magic", "Magic"),
    ("ticket", "Ticket"),
    ("volume", "Volume"),
    ("signal_entry", "Entry"),
    ("sl", "SL"),
    ("tp", "TP"),
    ("risk", "Risk"),
    ("profit", "Profit"),
]


def _render_rows(records):

    used_keys = set(key for key, _ in REPORT_COLUMNS)
    rows_html = []

    for record in records:

        extra = {
            key: value
            for key, value in record.items()
            if key not in used_keys
        }

        cells = []

        for key, _ in REPORT_COLUMNS:

            value = record.get(key, "-")

            if value is None:
                value = "-"

            cells.append(f"<td>{escape(str(value))}</td>")

        detail = (
            escape(json.dumps(extra, default=str))
            if extra
            else "-"
        )

        cells.append(f"<td class='details'>{detail}</td>")

        rows_html.append(
            "<tr>" + "".join(cells) + "</tr>"
        )

    return "".join(rows_html)


def _render_head():
    return "".join(
        f"<th>{escape(label)}</th>"
        for _, label in REPORT_COLUMNS
    ) + "<th>Details</th>"


def export_html_report(path=HTML_EXPORT_PATH):
    """Build the full self-contained HTML order report."""

    g = globals()

    orders = [
        record
        for record in order_log
        if record.get("event") == "order_opened"
    ]

    closed = [
        record
        for record in order_log
        if record.get("event") in (
            "position_closed",
            "second_position_closed"
        )
    ]

    profits = [
        record["profit"]
        for record in closed
        if isinstance(record.get("profit"), (int, float))
    ]

    final_account = dict(log_account)

    try:
        info = mt5.account_info()

        if info is not None:
            final_account = {
                "login": info.login,
                "server": info.server,
                "leverage": info.leverage,
                "balance": info.balance,
                "equity": info.equity,
                "profit": info.profit,
            }
    except BaseException:
        pass

    state = {
        "status": g.get("status"),
        "buy": g.get("buy"),
        "sell": g.get("sell"),
        "pending_setup": g.get("pending_setup"),
        "second_setup": g.get("second_setup"),
        "second_status": g.get("second_status"),
        "second_order_placed": g.get(
            "second_order_placed"
        ),
        "second_pullback_touched": g.get(
            "second_pullback_touched"
        ),
        "last_processed_candle": g.get(
            "last_processed_candle"
        ),
    }

    first_orders = [
        record
        for record in orders
        if record.get("label") == "first_entry"
    ]
    second_orders = [
        record
        for record in orders
        if record.get("label") == "second_entry"
    ]

    total_profit = sum(profits) if profits else None

    if total_profit is not None and total_profit >= 0:
        profit_html = (
            f"<span class='good'>{total_profit}</span>"
        )
    elif total_profit is not None:
        profit_html = (
            f"<span class='bad'>{total_profit}</span>"
        )
    else:
        profit_html = "-"

    stats_html = (
        f"<span class='badge'>Events: {len(order_log)}</span>"
        f"<span class='badge'>Orders: {len(orders)}</span>"
        f"<span class='badge'>First entries: {len(first_orders)}</span>"
        f"<span class='badge'>Second entries: {len(second_orders)}</span>"
        f"<span class='badge'>Buy orders: "
        f"{len([r for r in orders if r.get('direction') == 'BUY'])}</span>"
        f"<span class='badge'>Sell orders: "
        f"{len([r for r in orders if r.get('direction') == 'SELL'])}</span>"
        f"<span class='badge'>Closed: {len(closed)}</span>"
        f"<span class='badge'>Wins: "
        f"{len([p for p in profits if p > 0])}</span>"
        f"<span class='badge'>Losses: "
        f"{len([p for p in profits if p <= 0])}</span>"
        f"<span class='badge'>Total profit: {profit_html}</span>"
        f"<span class='badge'>Runtime: "
        f"{round(time_module.perf_counter() - BOT_START_PERF, 1)}s</span>"
    )

    html_text = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SP2L Advanced Bot DB_UI - Full Order Report</title>
<style>
body {{ background:#0f1216; color:#d7dde5;
 font-family:Segoe UI,Roboto,Arial,sans-serif; margin:24px; }}
h1 {{ font-size:22px; }}
h2 {{ font-size:16px; margin-top:28px; color:#7fd1ff;
 border-bottom:1px solid #26303a; padding-bottom:6px; }}
table {{ border-collapse:collapse; width:100%; margin-top:10px;
 font-size:13px; }}
th, td {{ border:1px solid #26303a; padding:6px 8px;
 text-align:left; vertical-align:top; word-break:break-word; }}
th {{ background:#171d24; color:#9fb3c8; }}
tr:nth-child(even) td {{ background:#131920; }}
table.kv {{ width:auto; min-width:460px; }}
td.key {{ color:#9fb3c8; width:280px; }}
td.details {{ font-size:11px; color:#8fa3b8; max-width:420px; }}
.good {{ color:#5ad38a; }}
.bad {{ color:#ff7b72; }}
.badge {{ display:inline-block; background:#171d24;
 border:1px solid #26303a; border-radius:10px;
 padding:3px 10px; margin:3px 6px 3px 0; font-size:12px; }}
details {{ margin-top:14px; }}
pre {{ background:#131920; border:1px solid #26303a;
 padding:12px; border-radius:6px; font-size:11px;
 overflow-x:auto; white-space:pre-wrap; word-break:break-word; }}
.meta {{ color:#9fb3c8; font-size:13px; }}
</style>
</head>
<body>
<h1>SP2L Advanced Bot DB_UI &mdash; Full Order Report</h1>
<p class="meta">
Generated: <b>{escape(_now_string())} UTC</b> |
Started: <b>{escape(BOT_STARTED_AT)} UTC</b> |
Version: <b>{escape(str(__version__))}</b>
</p>

<h2>Summary</h2>
<div>{stats_html}</div>

<h2>Bot settings</h2>
{_kv_table(log_settings)}

<h2>Account</h2>
{_kv_table(final_account)}

<h2>State at exit</h2>
{_kv_table(state)}

<h2>Orders ({len(orders)})</h2>
<table>
<thead><tr>{_render_head()}</tr></thead>
<tbody>{_render_rows(orders)}</tbody>
</table>

<h2>All events ({len(order_log)})</h2>
<table>
<thead><tr>{_render_head()}</tr></thead>
<tbody>{_render_rows(order_log)}</tbody>
</table>

<details>
<summary>Raw JSON log</summary>
<pre>{escape(json.dumps(build_log_payload(), indent=2, default=str))}</pre>
</details>

</body>
</html>
"""

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as report_file:
        report_file.write(html_text)

    return path


def _on_process_exit():
    """Ctrl+C / shutdown: export the HTML report once."""

    if html_exported["done"]:
        return

    html_exported["done"] = True

    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    except BaseException:
        pass

    try:
        report_path = export_html_report()

        console.print()
        console.print(
            Panel(
                f"[bold]JSON order log[/]: {JSON_LOG_PATH}\n"
                f"[bold]HTML report[/]: {report_path}",
                title="Shutdown detected (Ctrl+C)",
                border_style="green",
            )
        )

    except BaseException as e:
        print("HTML export failed:", e)


atexit.register(_on_process_exit)

# ============================================================
# MT5 INITIALIZE
# ============================================================

if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    mt5.shutdown()
    quit()


# ============================================================
# INTERNET CHECK
# ============================================================

def internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        ).connect((host, port))
        return True

    except socket.error:
        print("@", end="")
        sys.stdout.flush()
        return False


# ============================================================
# SETTINGS
# ============================================================

SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M1
NUMBER_OF_DATA = 500

SPIKE_CANDLE_SIZE = 1.5

PGAP_POINTS = 100
MAX_SL_DISTANCE_POINTS = 1000

# Use market-structure pivots for Stop Loss:
# BUY -> search backward for the first LowerLow before the spike.
# SELL -> search backward for the first HigherHigh before the spike.
# If False, use the original candle immediately before the spike.
USE_LOWERLOW_HIGHERHIGH_SL = False

TP_R = 1.0

# ------------------------------------------------------------
# Second entry
# ------------------------------------------------------------

USE_SECOND_ENTRY = False

SECOND_ENTRY_VOLUME_MULTIPLIER = 2.0

# ------------------------------------------------------------
# EMA filter
# ------------------------------------------------------------

USE_EMA_FILTER = True

EMA_PERIOD = 60

# ------------------------------------------------------------
# Trend structure filter
# ------------------------------------------------------------

USE_TREND_FILTER = True

MAX_OPPOSITE_MOVES = 1

# ------------------------------------------------------------
# Range / ADX filter
# ------------------------------------------------------------

USE_RANGE_FILTER = False

ADX_PERIOD = 14
MIN_ADX = 20.0

# ADX Rising filter
# Requires the latest closed candle ADX to be higher than the
# previous closed candle ADX.
USE_ADX_RISING_FILTER = False

# ------------------------------------------------------------
# New York session filter
# ------------------------------------------------------------

USE_SESSION_FILTER = False

SESSION_START_HOUR = 1
SESSION_END_HOUR = 5

SESSION_TIMEZONE = "America/New_York"

# ------------------------------------------------------------
# Trading
# ------------------------------------------------------------

MAGIC = 8
SECOND_ENTRY_MAGIC = 9
LOT = 0.01

LOOP_SECONDS = 0.5

# Number of candles fetched during the 0.5-second lightweight polling.
# The full NUMBER_OF_DATA history is fetched only when a new candle appears.
LIGHTWEIGHT_CANDLES = 2

# ============================================================
# SYMBOL INFORMATION
# ============================================================

symbol_info = mt5.symbol_info(SYMBOL)

if symbol_info is None:
    mt5.shutdown()
    raise RuntimeError(
        f"Could not get symbol information for {SYMBOL}"
    )

BROKER_POINT = float(symbol_info.point)
DIGITS = int(symbol_info.digits)

if BROKER_POINT <= 0:
    mt5.shutdown()
    raise RuntimeError("Invalid broker point.")

P_GAP_PRICE = PGAP_POINTS * BROKER_POINT

MAX_SL_DISTANCE_PRICE = (
    MAX_SL_DISTANCE_POINTS * BROKER_POINT
)


# ============================================================
# PRINT SETTINGS
# ============================================================

settings_table = Table(
    title="OPTIMIZED SP2L TRADER VER7.0 - DB_UI",
    box=rich_box.ROUNDED,
    border_style="cyan",
    header_style="bold yellow",
    show_lines=False,
)

settings_table.add_column("Setting", style="grey70")
settings_table.add_column("Value", justify="right")

for _setting_row in [
    ("Symbol", SYMBOL),
    ("Point", BROKER_POINT),
    ("Digits", DIGITS),
    ("Spike multiplier", SPIKE_CANDLE_SIZE),
    ("Gap points", PGAP_POINTS),
    ("Max SL points", MAX_SL_DISTANCE_POINTS),
    ("LowerLow/HH SL", USE_LOWERLOW_HIGHERHIGH_SL),
    ("TP", f"{TP_R}R"),
    ("Second entry", USE_SECOND_ENTRY),
    ("Second entry volume", SECOND_ENTRY_VOLUME_MULTIPLIER),
    ("EMA filter", USE_EMA_FILTER),
    ("EMA period", EMA_PERIOD),
    ("Trend filter", USE_TREND_FILTER),
    ("Max opposite moves", MAX_OPPOSITE_MOVES),
    ("Range filter", USE_RANGE_FILTER),
    ("ADX period", ADX_PERIOD),
    ("Minimum ADX", MIN_ADX),
    ("ADX rising filter", USE_ADX_RISING_FILTER),
    ("Session filter", USE_SESSION_FILTER),
    ("Session timezone", SESSION_TIMEZONE),
    (
        "Session",
        f"{SESSION_START_HOUR:02d}:00 - {SESSION_END_HOUR:02d}:00",
    ),
    ("Magic", MAGIC),
    ("Second entry magic", SECOND_ENTRY_MAGIC),
    ("Lot", LOT),
]:
    settings_table.add_row(
        str(_setting_row[0]),
        str(_setting_row[1]),
    )

console.print(settings_table)


# ============================================================
# SETTINGS SNAPSHOT FOR JSON / HTML REPORT
# ============================================================

log_settings.update({
    "symbol": SYMBOL,
    "timeframe": "M1",
    "number_of_data": NUMBER_OF_DATA,
    "spike_candle_size": SPIKE_CANDLE_SIZE,
    "pgap_points": PGAP_POINTS,
    "max_sl_distance_points": MAX_SL_DISTANCE_POINTS,
    "use_lowerlow_higherhigh_sl": USE_LOWERLOW_HIGHERHIGH_SL,
    "tp_r": TP_R,
    "use_second_entry": USE_SECOND_ENTRY,
    "second_entry_volume_multiplier": SECOND_ENTRY_VOLUME_MULTIPLIER,
    "use_ema_filter": USE_EMA_FILTER,
    "ema_period": EMA_PERIOD,
    "use_trend_filter": USE_TREND_FILTER,
    "max_opposite_moves": MAX_OPPOSITE_MOVES,
    "use_range_filter": USE_RANGE_FILTER,
    "adx_period": ADX_PERIOD,
    "min_adx": MIN_ADX,
    "use_adx_rising_filter": USE_ADX_RISING_FILTER,
    "use_session_filter": USE_SESSION_FILTER,
    "session_start_hour": SESSION_START_HOUR,
    "session_end_hour": SESSION_END_HOUR,
    "session_timezone": SESSION_TIMEZONE,
    "magic": MAGIC,
    "second_entry_magic": SECOND_ENTRY_MAGIC,
    "lot": LOT,
    "loop_seconds": LOOP_SECONDS,
    "lightweight_candles": LIGHTWEIGHT_CANDLES,
    "broker_point": BROKER_POINT,
    "digits": DIGITS,
})

log_event("bot_start")


# ============================================================
# EMA
# ============================================================

def calculate_ema(data):
    return (
        data["close"]
        .ewm(
            span=EMA_PERIOD,
            adjust=False
        )
        .mean()
    )


# ============================================================
# ADX
# ============================================================

def calculate_adx(data, period):

    high = data["high"]
    low = data["low"]
    close = data["close"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(
        np.where(
            (up_move > down_move) & (up_move > 0),
            up_move,
            0.0
        ),
        index=data.index
    )

    minus_dm = pd.Series(
        np.where(
            (down_move > up_move) & (down_move > 0),
            down_move,
            0.0
        ),
        index=data.index
    )

    previous_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    atr = tr.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    plus_di = (
        100
        *
        plus_dm.ewm(
            alpha=1 / period,
            adjust=False
        ).mean()
        /
        atr
    )

    minus_di = (
        100
        *
        minus_dm.ewm(
            alpha=1 / period,
            adjust=False
        ).mean()
        /
        atr
    )

    denominator = plus_di + minus_di

    dx = (
        100
        *
        (plus_di - minus_di).abs()
        /
        denominator.replace(0, np.nan)
    )

    adx = dx.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    return adx


# ============================================================
# NEW YORK SESSION
# ============================================================

NEW_YORK_TZ = ZoneInfo(SESSION_TIMEZONE)


def is_in_new_york_session(timestamp):

    if pd.isna(timestamp):
        return False

    ts = pd.Timestamp(timestamp)

    if ts.tzinfo is None:
        ts = ts.tz_localize("Etc/GMT-3")
    else:
        ts = ts.tz_convert("UTC")

    ny_time = ts.tz_convert(
        NEW_YORK_TZ
    ).time()

    start_time = time(
        SESSION_START_HOUR,
        0
    )

    end_time = time(
        SESSION_END_HOUR,
        0
    )

    return (
        start_time
        <=
        ny_time
        <
        end_time
    )


# ============================================================
# GET MARKET DATA
# ============================================================

def get_data(symbol):

    try:

        data = Meta.GetRates(
            symbol,
            NUMBER_OF_DATA,
            timeFrame=TIMEFRAME
        ).copy()

        if data.empty:
            print("No data received")
            return None

        data.columns = [
            str(c).lower()
            for c in data.columns
        ]

        required = [
            "open",
            "high",
            "low",
            "close"
        ]

        for col in required:

            if col not in data.columns:

                print(
                    f"Missing required column: {col}"
                )

                return None

        for col in required:

            data[col] = pd.to_numeric(
                data[col],
                errors="coerce"
            )

        data.dropna(
            subset=required,
            inplace=True
        )

        if not isinstance(
            data.index,
            pd.DatetimeIndex
        ):

            possible_time_columns = [
                "time",
                "datetime",
                "date",
                "local time"
            ]

            found_time = None

            for c in possible_time_columns:

                if c in data.columns:
                    found_time = c
                    break

            if found_time is not None:

                data[found_time] = pd.to_datetime(
                    data[found_time]
                )

                data.set_index(
                    found_time,
                    inplace=True
                )

        data.sort_index(
            inplace=True
        )

        data["EMA"] = calculate_ema(data)

        if USE_RANGE_FILTER or USE_ADX_RISING_FILTER:

            data["ADX"] = calculate_adx(
                data,
                ADX_PERIOD
            )

        else:

            data["ADX"] = np.nan

        return data

    except BaseException as e:

        print(
            "An exception has occurred in "
            f"OptimizedSP2LTrader.GetRates: {str(e)}"
        )

        return None


# ============================================================
# LIGHTWEIGHT LIVE DATA UPDATE
#
# The heavy NUMBER_OF_DATA download + indicator calculation is done
# only once per new M1 candle. During the forming candle we fetch only
# the latest 1-2 candles and update the cached dataframe in-place.
# This keeps the entry logic intrabar while avoiding a full 10,000-
# candle pandas rebuild every 0.5 second.
# ============================================================

def update_lightweight_data(symbol, data):

    try:

        latest = Meta.GetRates(
            symbol,
            LIGHTWEIGHT_CANDLES,
            timeFrame=TIMEFRAME
        ).copy()

        if latest.empty:
            return data, None

        latest.columns = [
            str(c).lower()
            for c in latest.columns
        ]

        required = [
            "open",
            "high",
            "low",
            "close"
        ]

        for col in required:
            if col not in latest.columns:
                return data, None

        for col in required:
            latest[col] = pd.to_numeric(
                latest[col],
                errors="coerce"
            )

        latest.dropna(
            subset=required,
            inplace=True
        )

        if not isinstance(
            latest.index,
            pd.DatetimeIndex
        ):
            possible_time_columns = [
                "time",
                "datetime",
                "date",
                "local time"
            ]

            found_time = None

            for c in possible_time_columns:
                if c in latest.columns:
                    found_time = c
                    break

            if found_time is not None:
                latest[found_time] = pd.to_datetime(
                    latest[found_time]
                )
                latest.set_index(
                    found_time,
                    inplace=True
                )

        latest.sort_index(inplace=True)

        if latest.empty:
            return data, None

        current_candle_time = latest.index[-1]

        # Update/append only the candles returned by the lightweight
        # request. Existing historical candles remain untouched.
        for idx, row in latest.iterrows():

            if idx in data.index:
                for col in required:
                    data.at[idx, col] = float(row[col])
            else:
                new_row = pd.DataFrame(
                    {
                        "open": [float(row["open"])],
                        "high": [float(row["high"])],
                        "low": [float(row["low"])],
                        "close": [float(row["close"])],
                        "EMA": [np.nan],
                        "ADX": [np.nan]
                    },
                    index=[idx]
                )
                if data.empty:
                    data = new_row
                else:
                    data = pd.concat(
                        [data, new_row],
                        axis=0
                    )

        data.sort_index(inplace=True)

        if len(data) > NUMBER_OF_DATA:
            data = data.iloc[-NUMBER_OF_DATA:].copy()

        # Keep EMA mathematically consistent with the existing EWM
        # while allowing the forming candle's close to change intrabar.
        if len(data) >= 2:

            current_idx = data.index[-1]
            previous_idx = data.index[-2]
            alpha = 2.0 / (EMA_PERIOD + 1.0)

            previous_ema = float(
                data.at[previous_idx, "EMA"]
            )

            if np.isfinite(previous_ema):
                data.at[current_idx, "EMA"] = (
                    alpha * float(data.at[current_idx, "close"])
                    +
                    (1.0 - alpha) * previous_ema
                )

        # ADX is calculated during the full refresh on a new candle.
        # It is intentionally NOT recalculated on every 0.5-second
        # poll because the ADX Rising filter uses closed candles,
        # whose ADX values do not change while the current candle forms.

        return data, current_candle_time

    except BaseException as e:

        print(
            "An exception has occurred in "
            f"OptimizedSP2LTrader.lightweight_update: {str(e)}"
        )

        return data, None


# ============================================================
# ENTRY FILTERS
# ============================================================

def entry_filters_are_valid(
    data,
    entry_pos,
    direction
):

    entry_idx = data.index[entry_pos]

    # --------------------------------------------------------
    # EMA FILTER
    # --------------------------------------------------------

    if USE_EMA_FILTER:

        entry_close = float(
            data.iloc[entry_pos]["close"]
        )

        entry_ema = float(
            data.iloc[entry_pos]["EMA"]
        )

        if not np.isfinite(entry_ema):
            return False

        if direction == "BUY":

            if entry_close <= entry_ema:
                return False

        else:

            if entry_close >= entry_ema:
                return False

    # --------------------------------------------------------
    # RANGE / ADX FILTER
    # --------------------------------------------------------

    if USE_RANGE_FILTER:

        entry_adx = float(
            data.iloc[entry_pos]["ADX"]
        )

        if not np.isfinite(entry_adx):
            return False

        if entry_adx < MIN_ADX:
            return False

    # --------------------------------------------------------
    # ADX RISING FILTER
    # --------------------------------------------------------

    if USE_ADX_RISING_FILTER:

        # The trigger candle is still forming. To match the realistic
        # backtest logic, compare the two latest CLOSED candles.
        if entry_pos < 2:
            return False

        current_closed_adx = float(
            data.iloc[entry_pos - 1]["ADX"]
        )

        previous_closed_adx = float(
            data.iloc[entry_pos - 2]["ADX"]
        )

        if not np.isfinite(current_closed_adx):
            return False

        if not np.isfinite(previous_closed_adx):
            return False

        if current_closed_adx <= previous_closed_adx:
            return False

    # --------------------------------------------------------
    # NEW YORK SESSION FILTER
    # --------------------------------------------------------

    if USE_SESSION_FILTER:

        if not is_in_new_york_session(
            entry_idx
        ):
            return False

    return True


# ============================================================
# TREND FILTER
# ============================================================

def buy_trend_is_valid(
    data,
    start_pos,
    entry_pos
):

    if not USE_TREND_FILTER:
        return True

    consecutive_opposite = 0

    for pos in range(
        start_pos + 1,
        entry_pos + 1
    ):

        current_high = float(
            data.iloc[pos]["high"]
        )

        previous_high = float(
            data.iloc[pos - 1]["high"]
        )

        if current_high > previous_high:

            consecutive_opposite = 0

        else:

            consecutive_opposite += 1

            if (
                consecutive_opposite
                >
                MAX_OPPOSITE_MOVES
            ):

                return False

    return True


def sell_trend_is_valid(
    data,
    start_pos,
    entry_pos
):

    if not USE_TREND_FILTER:
        return True

    consecutive_opposite = 0

    for pos in range(
        start_pos + 1,
        entry_pos + 1
    ):

        current_low = float(
            data.iloc[pos]["low"]
        )

        previous_low = float(
            data.iloc[pos - 1]["low"]
        )

        if current_low < previous_low:

            consecutive_opposite = 0

        else:

            consecutive_opposite += 1

            if (
                consecutive_opposite
                >
                MAX_OPPOSITE_MOVES
            ):

                return False

    return True


# ============================================================
# SETUP DETECTION
#
# Live-trader indexing follows the same index shift used when
# converting "Simple Backtest" into "Simple Trader":
#
#   -1 = latest candle
#   -2 = candle after spike
#   -3 = spike candle
#   -4 = candle before spike
#
# The current candle is used exactly as in the live trader style.
# ============================================================

def detect_buy_setup(data):

    if len(data) < 5:
        return False

    buy0 = (
        data["low"].iloc[-1]
        <
        data["low"].iloc[-2]
    )

    buy1 = (
        data["close"].iloc[-2]
        >
        data["close"].iloc[-3]
    )

    buy2 = (
        data["open"].iloc[-2]
        >
        data["open"].iloc[-3]
    )

    buy3 = (
        data["close"].iloc[-3]
        >
        data["close"].iloc[-4]
    )

    buy4 = (
        data["open"].iloc[-3]
        >
        data["open"].iloc[-4]
    )

    buy5 = (
        data["close"].iloc[-2]
        >
        data["open"].iloc[-2]
    )

    buy6 = (
        data["close"].iloc[-3]
        >
        data["open"].iloc[-3]
    )

    buy7 = (
        data["close"].iloc[-4]
        >
        data["open"].iloc[-4]
    )

    p_gap_buy = (
        data["low"].iloc[-2]
        >
        data["high"].iloc[-4]
        +
        P_GAP_PRICE
    )

    spike_buy = (

        (
            data["close"].iloc[-3]
            -
            data["open"].iloc[-3]
        )
        >
        SPIKE_CANDLE_SIZE
        *
        (
            data["close"].iloc[-2]
            -
            data["open"].iloc[-2]
        )

    ) & (

        (
            data["close"].iloc[-3]
            -
            data["open"].iloc[-3]
        )
        >
        SPIKE_CANDLE_SIZE
        *
        (
            data["close"].iloc[-4]
            -
            data["open"].iloc[-4]
        )

    ) & (

        (
            data["close"].iloc[-3]
            -
            data["open"].iloc[-3]
        )
        >
        SPIKE_CANDLE_SIZE
        *
        (
            data["close"].iloc[-1]
            -
            data["open"].iloc[-1]
        )
    )

    return (
        buy0
        & buy1
        & buy2
        & buy3
        & buy4
        & buy5
        & buy6
        & buy7
        & p_gap_buy
        & spike_buy
    )


def detect_sell_setup(data):

    if len(data) < 5:
        return False

    sell0 = (
        data["high"].iloc[-1]
        >
        data["high"].iloc[-2]
    )

    sell1 = (
        data["close"].iloc[-2]
        <
        data["close"].iloc[-3]
    )

    sell2 = (
        data["open"].iloc[-2]
        <
        data["open"].iloc[-3]
    )

    sell3 = (
        data["close"].iloc[-3]
        <
        data["close"].iloc[-4]
    )

    sell4 = (
        data["open"].iloc[-3]
        <
        data["open"].iloc[-4]
    )

    sell5 = (
        data["close"].iloc[-2]
        <
        data["open"].iloc[-2]
    )

    sell6 = (
        data["close"].iloc[-3]
        <
        data["open"].iloc[-3]
    )

    sell7 = (
        data["close"].iloc[-4]
        <
        data["open"].iloc[-4]
    )

    p_gap_sell = (
        data["high"].iloc[-2]
        <
        data["low"].iloc[-4]
        -
        P_GAP_PRICE
    )

    spike_sell = (

        (
            data["open"].iloc[-3]
            -
            data["close"].iloc[-3]
        )
        >
        SPIKE_CANDLE_SIZE
        *
        (
            data["open"].iloc[-2]
            -
            data["close"].iloc[-2]
        )

    ) & (

        (
            data["open"].iloc[-3]
            -
            data["close"].iloc[-3]
        )
        >
        SPIKE_CANDLE_SIZE
        *
        (
            data["open"].iloc[-4]
            -
            data["close"].iloc[-4]
        )

    ) & (

        (
            data["open"].iloc[-3]
            -
            data["close"].iloc[-3]
        )
        >
        SPIKE_CANDLE_SIZE
        *
        (
            data["open"].iloc[-1]
            -
            data["close"].iloc[-1]
        )
    )

    return (
        sell0
        & sell1
        & sell2
        & sell3
        & sell4
        & sell5
        & sell6
        & sell7
        & p_gap_sell
        & spike_sell
    )


# ============================================================
# PENDING SETUP
# ============================================================

def find_buy_sl_lower_low(data):
    """Find the nearest LowerLow at or before the candle before the spike.

    A LowerLow has a low strictly below the lows of the immediately
    older and immediately newer candles. Candle color is irrelevant.
    """
    # The spike is data.iloc[-3], so the candle immediately before it is -4.
    # Scan from that candle backward into older history.
    for pos in range(len(data) - 4, 0, -1):
        pivot_low = float(data["low"].iloc[pos])
        older_low = float(data["low"].iloc[pos - 1])
        newer_low = float(data["low"].iloc[pos + 1])

        if pivot_low < older_low and pivot_low < newer_low:
            return pivot_low

    return None


def find_sell_sl_higher_high(data):
    """Find the nearest HigherHigh at or before the candle before the spike.

    A HigherHigh has a high strictly above the highs of the immediately
    older and immediately newer candles. Candle color is irrelevant.
    """
    # The spike is data.iloc[-3], so the candle immediately before it is -4.
    # Scan from that candle backward into older history.
    for pos in range(len(data) - 4, 0, -1):
        pivot_high = float(data["high"].iloc[pos])
        older_high = float(data["high"].iloc[pos - 1])
        newer_high = float(data["high"].iloc[pos + 1])

        if pivot_high > older_high and pivot_high > newer_high:
            return pivot_high

    return None


def create_pending_buy(data):

    # The live setup corresponds to the backtest setup row.
    setup_time = data.index[-1]

    if USE_LOWERLOW_HIGHERHIGH_SL:
        sl = find_buy_sl_lower_low(data)

        if sl is None:
            print("BUY setup skipped: no LowerLow found before the spike.")
            return None
    else:
        # Original behavior: low of the candle immediately before the spike.
        sl = float(data["low"].iloc[-4])

    spike_body = abs(
        float(data["close"].iloc[-3])
        -
        float(data["open"].iloc[-3])
    )

    return {
        "direction": "BUY",
        "setup_time": setup_time,
        "setup_pos_time": setup_time,
        "sl": float(sl),
        "spike_body": spike_body,
        "second_entry_active": False
    }


def create_pending_sell(data):

    setup_time = data.index[-1]

    if USE_LOWERLOW_HIGHERHIGH_SL:
        sl = find_sell_sl_higher_high(data)

        if sl is None:
            print("SELL setup skipped: no HigherHigh found before the spike.")
            return None
    else:
        # Original behavior: high of the candle immediately before the spike.
        sl = float(data["high"].iloc[-4])

    spike_body = abs(
        float(data["open"].iloc[-3])
        -
        float(data["close"].iloc[-3])
    )

    return {
        "direction": "SELL",
        "setup_time": setup_time,
        "setup_pos_time": setup_time,
        "sl": float(sl),
        "spike_body": spike_body,
        "second_entry_active": False
    }


# ============================================================
# FIND FIRST VALID BUY ENTRY
#
# This is the live equivalent of the Optimized backtest's
# find_first_buy_entry(). It does NOT enter immediately when
# a setup is detected.
# ============================================================

def check_pending_buy(
    data,
    pending
):

    if len(data) < 2:
        return None

    sl = pending["sl"]

    current_low = float(
        data["low"].iloc[-1]
    )

    previous_low = float(
        data["low"].iloc[-2]
    )

    if current_low >= previous_low:
        return None

    risk = current_low - sl

    if risk <= 0:
        return None

    if risk > MAX_SL_DISTANCE_PRICE:
        return "INVALID"

    # Find the setup candle in the current data.
    try:
        start_pos = data.index.get_loc(
            pending["setup_pos_time"]
        )
    except KeyError:
        return None

    entry_pos = len(data) - 1

    if not buy_trend_is_valid(
        data,
        start_pos,
        entry_pos
    ):
        return None

    if not entry_filters_are_valid(
        data,
        entry_pos,
        "BUY"
    ):
        return None

    return {
        "direction": "BUY",
        "entry": current_low,
        "sl": sl,
        "risk": risk,
        "setup_time": pending["setup_time"],
        "entry_time": data.index[-1],
        "spike_body": pending["spike_body"]
    }


# ============================================================
# FIND FIRST VALID SELL ENTRY
# ============================================================

def check_pending_sell(
    data,
    pending
):

    if len(data) < 2:
        return None

    sl = pending["sl"]

    current_high = float(
        data["high"].iloc[-1]
    )

    previous_high = float(
        data["high"].iloc[-2]
    )

    if current_high <= previous_high:
        return None

    risk = sl - current_high

    if risk <= 0:
        return None

    if risk > MAX_SL_DISTANCE_PRICE:
        return "INVALID"

    try:
        start_pos = data.index.get_loc(
            pending["setup_pos_time"]
        )
    except KeyError:
        return None

    entry_pos = len(data) - 1

    if not sell_trend_is_valid(
        data,
        start_pos,
        entry_pos
    ):
        return None

    if not entry_filters_are_valid(
        data,
        entry_pos,
        "SELL"
    ):
        return None

    return {
        "direction": "SELL",
        "entry": current_high,
        "sl": sl,
        "risk": risk,
        "setup_time": pending["setup_time"],
        "entry_time": data.index[-1],
        "spike_body": pending["spike_body"]
    }


# ============================================================
# SECOND ENTRY
# ============================================================

def get_second_entry(
    direction,
    entry,
    risk
):

    if direction == "BUY":

        return entry - risk / 2

    return entry + risk / 2


# ============================================================
# TRADE STATE
# ============================================================

def get_trade_state(symbol, magic=MAGIC):

    resume = Meta.resume()

    if resume is None:
        return False, None

    if resume.shape[0] == 0:
        return False, None

    row = resume.loc[
        (resume["symbol"] == symbol)
        &
        (resume["magic"] == magic)
    ]

    if row.empty:
        return False, None

    return True, row


def get_second_trade_state(symbol):
    # The second entry has its own magic and its own state.
    # A pending order is tracked separately from an active position.
    position_exists, position_row = get_trade_state(
        symbol,
        SECOND_ENTRY_MAGIC
    )

    pending_exists = False
    pending_row = None

    try:
        orders = mt5.orders_get(symbol=symbol)

        if orders is not None:
            second_orders = [
                order
                for order in orders
                if int(order.magic) == SECOND_ENTRY_MAGIC
            ]

            if len(second_orders) > 0:
                pending_exists = True
                pending_row = second_orders[0]

    except BaseException as e:
        print(
            "An exception has occurred in "
            f"get_second_trade_state: {str(e)}"
        )

    return (
        position_exists,
        position_row,
        pending_exists,
        pending_row
    )


def cancel_second_pending_order(symbol, pending_row):
    if pending_row is None:
        return

    try:
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": int(pending_row.ticket),
            "symbol": symbol
        }

        result = mt5.order_send(request)

        if result is not None:
            print(
                "Second entry pending order removed:",
                result.comment
            )

    except BaseException as e:
        print(
            "An exception has occurred in "
            f"cancel_second_pending_order: {str(e)}"
        )


# ============================================================
# Optimized SP2L STRATEGY
#
# Returns:
#
#   preBuy
#   preSell
#   status
#   sl
#   tp
#   pending_setup
#   trade_setup
#
# pending_setup is deliberately kept separate from status.
# A pending setup is NOT an open position.
# ============================================================

def Strategy(
    symbol,
    preBuy,
    preSell,
    status,
    pending_setup,
    data=None
):

    sl = 0
    tp = 0
    trade_setup = None

    # Full market-data processing is performed by the main loop only
    # when a new candle appears. Between candles, the main loop passes
    # the cached data after updating only the latest candle.
    if data is None:
        data = get_data(symbol)

    if data is None:
        return (
            preBuy,
            preSell,
            status,
            sl,
            tp,
            pending_setup,
            trade_setup
        )

    # ========================================================
    # If a position is already open, do not search for another
    # setup.
    # ========================================================

    if status:

        return (
            preBuy,
            preSell,
            status,
            sl,
            tp,
            pending_setup,
            trade_setup
        )

    # ========================================================
    # PENDING SETUP
    #
    # This is the key difference from Simple Trader.
    # The setup waits for the first valid entry.
    # ========================================================

    if pending_setup is not None:

        direction = pending_setup["direction"]

        if direction == "BUY":

            result = check_pending_buy(
                data,
                pending_setup
            )

        else:

            result = check_pending_sell(
                data,
                pending_setup
            )

        if result == "INVALID":

            log_event(
                "setup_invalidated",
                symbol=symbol,
                direction=direction,
                reason="SL distance above "
                       "MAX_SL_DISTANCE_POINTS",
                setup_time=str(
                    pending_setup["setup_time"]
                ),
            )

            pending_setup = None

        elif result is not None:

            entry = result["entry"]
            sl = result["sl"]
            risk = result["risk"]

            if risk <= 0:
                pending_setup = None

            else:

                if direction == "BUY":

                    tp = (
                        entry
                        +
                        TP_R * risk
                    )

                else:

                    tp = (
                        entry
                        -
                        TP_R * risk
                    )

                second_entry = get_second_entry(
                    direction,
                    entry,
                    risk
                )

                trade_setup = {
                    "direction": direction,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "risk": risk,
                    "second_entry": second_entry,
                    "setup_time": result["setup_time"],
                    "entry_time": result["entry_time"],
                    "spike_body": result["spike_body"]
                }

                if direction == "BUY":
                    preBuy = True
                    preSell = False
                else:
                    preBuy = False
                    preSell = True

                status = True

                pending_setup = None

                return (
                    preBuy,
                    preSell,
                    status,
                    sl,
                    tp,
                    pending_setup,
                    trade_setup
                )

    # ========================================================
    # LOOK FOR A NEW SETUP
    #
    # A setup is only created here.
    # It is NOT an entry.
    # ========================================================

    buy = detect_buy_setup(data)
    sell = detect_sell_setup(data)

    if buy and not sell:

        pending_setup = create_pending_buy(
            data
        )

        if pending_setup is not None:
            console.print(
                f"\n[{STYLE_SETUP}]"
                f"BUY pending setup detected[/{STYLE_SETUP}]"
                f"  SL [bold]{pending_setup['sl']}[/]  "
                f"spike {pending_setup['spike_body']}"
            )

            log_event(
                "pending_setup",
                symbol=symbol,
                direction="BUY",
                setup_time=str(
                    pending_setup["setup_time"]
                ),
                sl=pending_setup["sl"],
                spike_body=pending_setup["spike_body"],
            )

    elif sell and not buy:

        pending_setup = create_pending_sell(
            data
        )

        if pending_setup is not None:
            console.print(
                f"\n[{STYLE_SETUP}]"
                f"SELL pending setup detected[/{STYLE_SETUP}]"
                f"  SL [bold]{pending_setup['sl']}[/]  "
                f"spike {pending_setup['spike_body']}"
            )

            log_event(
                "pending_setup",
                symbol=symbol,
                direction="SELL",
                setup_time=str(
                    pending_setup["setup_time"]
                ),
                sl=pending_setup["sl"],
                spike_body=pending_setup["spike_body"],
            )

    return (
        preBuy,
        preSell,
        status,
        sl,
        tp,
        pending_setup,
        trade_setup
    )


# ============================================================
# ACCOUNT INFORMATION
# ============================================================

accountInfo = mt5.account_info()

if accountInfo is not None:

    log_account.update({
        "login": accountInfo.login,
        "server": accountInfo.server,
        "leverage": accountInfo.leverage,
        "balance": accountInfo.balance,
        "equity": accountInfo.equity,
        "profit": accountInfo.profit,
    })

    console.print(
        value_panel(
            "Account",
            [
                ("Login", accountInfo.login),
                ("Server", accountInfo.server),
                ("Leverage", accountInfo.leverage),
                ("Balance", accountInfo.balance),
                ("Equity", accountInfo.equity),
                ("Profit", accountInfo.profit),
            ],
            style="green",
        )
    )

    log_event("account_info", **dict(log_account))

console.print(
    Panel(
        f"[bold]Run time:[/] "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        border_style="grey50",
        padding=(0, 1),
    )
)


# ============================================================
# SYMBOLS
# ============================================================

symbols_list = {
    SYMBOL: [SYMBOL, LOT],
}


# ============================================================
# INITIAL STATE
# ============================================================

buy = False
sell = False
status = False

pending_setup = None
second_setup = None
second_status = False
second_order_placed = False
# For second entry, price must first pull back through the level
# and then reclaim it before the trade is opened.
second_pullback_touched = False

# Used to prevent detecting the same live setup repeatedly.
last_setup_time = None

# Used to prevent processing the same live candle repeatedly.
last_processed_candle = None

# Ticket of the currently managed first-entry position.
# Used to resolve profit / close time when the position closes.
last_entry_ticket = {"ticket": None}

# Ticket of the currently managed second-entry position.
second_entry_ticket = {"ticket": None}

# ============================================================
# MAIN LOOP
#
# Architecture:
#   1) Poll every 0.5 second.
#   2) If the M1 candle changed -> perform the full data refresh.
#   3) If the same candle is still forming -> only refresh the latest
#      1-2 candles and run the lightweight pending/setup checks.
#
# IMPORTANT:
# Setup detection still runs every 0.5 second on the cached data because
# the strategy intentionally uses the CURRENT FORMING CANDLE. This is
# lightweight; the expensive 10,000-candle indicator rebuild happens
# only on a new candle.
# ============================================================

market_data_cache = {}

while True:

    loop_start_time = time_module.perf_counter()

    if internet() is True:

        for asset in symbols_list.keys():

            symbol = symbols_list[asset][0]
            lot = symbols_list[asset][1]

            selected = mt5.symbol_select(
                symbol
            )

            if not selected:

                console.print(
                    f"[bold red]ERROR[/bold red] - Failed to select "
                    f"'{symbol}' in MetaTrader 5 with error: "
                    f"{mt5.last_error()}"
                )

                continue

            # =================================================
            # CHECK EXISTING POSITION
            # =================================================

            position_exists, row = get_trade_state(
                symbol
            )

            # -------------------------------------------------
            # Stop loss / position closed
            # -------------------------------------------------

            if not position_exists and status:

                closed_direction = (
                    "BUY"
                    if buy
                    else (
                        "SELL"
                        if sell
                        else "?"
                    )
                )

                close_info = get_position_close_info(
                    last_entry_ticket["ticket"]
                )

                log_event(
                    "position_closed",
                    label="first_entry",
                    symbol=symbol,
                    direction=closed_direction,
                    magic=MAGIC,
                    ticket=last_entry_ticket["ticket"],
                    profit=close_info["profit"],
                    close_time=close_info["close_time"],
                    comment=close_info["comment"],
                )

                last_entry_ticket["ticket"] = None

                status = False
                buy = False
                sell = False
                pending_setup = None

                if USE_SECOND_ENTRY:
                    (
                        _second_position_exists,
                        _second_row,
                        _second_pending_exists,
                        _second_pending_row
                    ) = get_second_trade_state(symbol)

                    if (
                        _second_pending_exists
                        and
                        not _second_position_exists
                    ):
                        cancel_second_pending_order(
                            symbol,
                            _second_pending_row
                        )

                    if not _second_position_exists:
                        second_setup = None
                        second_status = False
                        second_order_placed = False
                        second_pullback_touched = False

                console.print(
                    f"[{STYLE_WARN}]Strategy - Position closed "
                    f"/ SL or TP hit![/{STYLE_WARN}]"
                    + (
                        f"  profit [bold]{close_info['profit']}[/]"
                        if close_info["profit"] is not None
                        else ""
                    )
                )

            # -------------------------------------------------
            # Abnormal open position
            # -------------------------------------------------

            elif position_exists and not status:

                console.print(
                    "[bold red]Abnormal position:[/bold red] "
                    "open MT5 position exists but the "
                    "local status key is False!!"
                )

                log_event(
                    "abnormal_position",
                    symbol=symbol,
                    magic=MAGIC,
                    note="Open MT5 position but "
                         "local status is False",
                )

            # =================================================
            # 0.5-SECOND LIGHTWEIGHT MARKET UPDATE
            #
            # This single small request also tells us whether the M1
            # candle changed. We avoid a second GetRates(0.5) request.
            # =================================================

            if symbol in market_data_cache:
                probe_data, current_candle_time = update_lightweight_data(
                    symbol,
                    market_data_cache[symbol]
                )
            else:
                probe_data, current_candle_time = update_lightweight_data(
                    symbol,
                    pd.DataFrame(
                        columns=["open", "high", "low", "close", "EMA", "ADX"]
                    )
                )

            if current_candle_time is None:
                continue

            # =================================================
            # FULL PROCESSING ONLY ON CANDLE CHANGE
            # =================================================

            new_candle = (
                symbol not in market_data_cache
                or last_processed_candle != current_candle_time
            )

            if new_candle:

                full_data = get_data(symbol)

                if full_data is None or full_data.empty:
                    continue

                market_data_cache[symbol] = full_data
                last_processed_candle = current_candle_time

                # --------------------------------------------
                # RICH CANDLE STATUS LINE (once per M1 candle)
                # --------------------------------------------

                _last_row = full_data.iloc[-1]

                _state = (
                    "POSITION OPEN"
                    if status
                    else (
                        "PENDING SETUP"
                        if pending_setup is not None
                        else "FLAT"
                    )
                )

                _state_style = (
                    "bold green"
                    if _state == "POSITION OPEN"
                    else (
                        "bold cyan"
                        if _state == "PENDING SETUP"
                        else "grey50"
                    )
                )

                _ema_value = _last_row.get("EMA")
                _ema_text = (
                    round(float(_ema_value), DIGITS)
                    if _ema_value is not None
                    and pd.notna(_ema_value)
                    else "-"
                )

                console.print(
                    f"[grey50]{current_candle_time}[/]  "
                    f"close [bold]"
                    f"{round(float(_last_row['close']), DIGITS)}[/]  "
                    f"EMA [bold cyan]{_ema_text}[/]  "
                    f"| state [{_state_style}]{_state}[/{_state_style}]"
                )

                # print(
                #     f"\nNEW CANDLE -> FULL PROCESSING: "
                #     f"{current_candle_time}"
                # )

            else:

                # probe_data already contains the latest intrabar OHLC
                # values and the lightweight EMA update.
                market_data_cache[symbol] = probe_data

            data = market_data_cache[symbol]

            # =================================================
            # STRATEGY
            #
            # Strategy receives cached data. Therefore it no longer
            # downloads/rebuilds NUMBER_OF_DATA every 0.5 second.
            # Pending entry and current-candle setup detection remain
            # active every 0.5 second.
            # =================================================

            (
                buy,
                sell,
                status,
                sl,
                tp,
                pending_setup,
                trade_setup
            ) = Strategy(
                symbol,
                buy,
                sell,
                status,
                pending_setup,
                data=data
            )

            # =================================================
            # EXECUTE ENTRY 1
            # =================================================

            if trade_setup is not None:

                direction = trade_setup["direction"]

                entry = trade_setup["entry"]
                sl = trade_setup["sl"]
                tp = trade_setup["tp"]

                _entry_style = STYLE_BUY if direction == "BUY" else STYLE_SELL

                console.print(
                    value_panel(
                        f"[{_entry_style}]"
                        f"VALID {direction} ENTRY[/{_entry_style}]",
                        [
                            ("Setup time", trade_setup["setup_time"]),
                            ("Entry time", trade_setup["entry_time"]),
                            ("Entry", round(entry, DIGITS)),
                            ("SL", round(sl, DIGITS)),
                            ("TP", round(tp, DIGITS)),
                            ("Risk", round(trade_setup["risk"], DIGITS)),
                            (
                                "Second",
                                round(trade_setup["second_entry"], DIGITS),
                            ),
                            ("Spike body", trade_setup["spike_body"]),
                        ],
                        style=(
                            "green" if direction == "BUY" else "red"
                        ),
                    )
                )

                # TP is calculated by Meta at the actual executable
                # Ask/Bid using the fixed SL and TP_R.
                # The original RiskReward() logic remains untouched.
                Meta.SetExecutionBasedTP(
                    enabled=True,
                    tp_r=TP_R,
                    signal_entry=entry
                )

                Meta.run(
                    symbol,
                    buy,
                    sell,
                    lot,
                    tp,
                    sl,
                    MAGIC,
                    stopLossPure=True
                )

                # --------------------------------------------
                # LOG FIRST-ENTRY ORDER
                # --------------------------------------------

                entry_ticket = find_open_ticket(
                    symbol,
                    MAGIC
                )

                last_entry_ticket["ticket"] = entry_ticket

                log_event(
                    "order_opened",
                    label="first_entry",
                    symbol=symbol,
                    direction=direction,
                    magic=MAGIC,
                    ticket=entry_ticket,
                    volume=lot,
                    signal_entry=entry,
                    sl=sl,
                    tp=tp,
                    risk=trade_setup["risk"],
                    second_entry=trade_setup[
                        "second_entry"
                    ],
                    setup_time=str(
                        trade_setup["setup_time"]
                    ),
                    entry_time=str(
                        trade_setup["entry_time"]
                    ),
                    spike_body=trade_setup[
                        "spike_body"
                    ],
                )

                # =================================================
                # SECOND ENTRY SETUP
                # =================================================

                if USE_SECOND_ENTRY:

                    second_setup = {
                        "direction": direction,
                        "entry": trade_setup["second_entry"],
                        "sl": sl,
                        # The second trade must use exactly the same TP
                        # level as the first trade. It is an absolute price,
                        # not a new TP_R calculation from the second entry.
                        # however, it'll update in meta by first entry new tp
                        "tp": tp,
                        "setup_time": trade_setup["setup_time"],
                        "entry_time": trade_setup["entry_time"]
                    }

                    # A new second-entry setup starts with no pullback
                    # having occurred yet.
                    second_pullback_touched = False

                    console.print(
                        value_panel(
                            f"[{STYLE_SECOND}]"
                            f"Second entry ENABLED"
                            f"[/{STYLE_SECOND}]",
                            [
                                (
                                    "Second entry price",
                                    round(
                                        second_setup["entry"],
                                        DIGITS,
                                    ),
                                ),
                                (
                                    "Second entry volume",
                                    lot
                                    * SECOND_ENTRY_VOLUME_MULTIPLIER,
                                ),
                                ("First trade TP", round(tp, DIGITS)),
                                ("Magic", SECOND_ENTRY_MAGIC),
                            ],
                            style="magenta",
                        )
                    )

                trade_setup = None

            # =================================================
            # MANAGE SECOND ENTRY ORDER / POSITION
            #
            # second_status is independent from the first-entry
            # status. The second trade uses SECOND_ENTRY_MAGIC=9.
            # =================================================

            if USE_SECOND_ENTRY:

                (
                    second_position_exists,
                    second_row,
                    second_pending_exists,
                    second_pending_row
                ) = get_second_trade_state(symbol)

                # ---------------------------------------------
                # Pending order -> active position
                # ---------------------------------------------
                if second_position_exists and not second_status:

                    second_status = True

                    second_entry_ticket["ticket"] = (
                        find_open_ticket(
                            symbol,
                            SECOND_ENTRY_MAGIC
                        )
                    )

                    console.print(
                        f"[{STYLE_SECOND}]Second entry position "
                        f"is ACTIVE (magic:{SECOND_ENTRY_MAGIC})"
                        f"[/{STYLE_SECOND}]"
                    )

                    if isinstance(second_setup, dict):
                        _second_signal = second_setup.get(
                            "entry"
                        )
                        _second_sl = second_setup.get(
                            "sl"
                        )
                        _second_tp = second_setup.get(
                            "tp"
                        )
                    else:
                        _second_signal = None
                        _second_sl = None
                        _second_tp = None

                    log_event(
                        "second_position_active",
                        label="second_entry",
                        symbol=symbol,
                        direction=second_setup.get(
                            "direction"
                        )
                        if isinstance(
                            second_setup,
                            dict
                        )
                        else None,
                        magic=SECOND_ENTRY_MAGIC,
                        ticket=second_entry_ticket[
                            "ticket"
                        ],
                        signal_entry=_second_signal,
                        sl=_second_sl,
                        tp=_second_tp,
                    )

                # ---------------------------------------------
                # Active second position -> closed
                # ---------------------------------------------
                elif (
                    not second_position_exists
                    and second_status
                ):

                    second_status = False
                    second_setup = None
                    second_order_placed = False
                    second_pullback_touched = False

                    second_close_info = (
                        get_position_close_info(
                            second_entry_ticket["ticket"]
                        )
                    )

                    console.print(
                        f"[{STYLE_WARN}]Second entry position "
                        f"closed / SL or TP hit "
                        f"(magic:{SECOND_ENTRY_MAGIC})"
                        f"[/{STYLE_WARN}]"
                        + (
                            f"  profit "
                            f"[bold]{second_close_info['profit']}[/]"
                            if second_close_info["profit"]
                            is not None
                            else ""
                        )
                    )

                    log_event(
                        "second_position_closed",
                        label="second_entry",
                        symbol=symbol,
                        magic=SECOND_ENTRY_MAGIC,
                        ticket=second_entry_ticket[
                            "ticket"
                        ],
                        profit=second_close_info[
                            "profit"
                        ],
                        close_time=second_close_info[
                            "close_time"
                        ],
                        comment=second_close_info[
                            "comment"
                        ],
                    )

                    second_entry_ticket["ticket"] = None

                # Keep the local flag synchronized with MT5.
                second_order_placed = (
                    second_position_exists
                    or
                    second_pending_exists
                )

                # ---------------------------------------------
                # SECOND ENTRY = PULLBACK + RECLAIM
                #
                # The second trade must NOT open merely because price
                # reaches/crosses second_entry. First price must move
                # through the second-entry level in the pullback
                # direction, and only after that may a reclaim of the
                # level trigger the market order.
                #
                # BUY  -> Ask must first go <= level, then reclaim > level.
                # SELL -> Bid must first go >= level, then reclaim < level.
                #
                # The TP is exactly the first trade TP.
                # ---------------------------------------------
                if (
                    second_setup is not None
                    and
                    not second_order_placed
                    and
                    not second_status
                ):

                    second_direction = second_setup["direction"]
                    second_entry = float(second_setup["entry"])
                    second_sl = float(second_setup["sl"])
                    second_tp = float(second_setup["tp"])
                    second_volume = lot * SECOND_ENTRY_VOLUME_MULTIPLIER

                    tick = mt5.symbol_info_tick(symbol)

                    if tick is not None:

                        if second_direction == "BUY":
                            trigger_price = float(tick.ask)
                            second_buy = True
                            second_sell = False

                            # Step 1: price must actually pull back to
                            # or below the second-entry level.
                            if trigger_price <= second_entry:
                                second_pullback_touched = True

                            # Step 2: after the pullback has happened,
                            # open only when price reclaims the level.
                            second_triggered = (
                                second_pullback_touched
                                and
                                trigger_price > second_entry
                            )
                        else:
                            trigger_price = float(tick.bid)
                            second_buy = False
                            second_sell = True

                            # Step 1: price must actually pull back to
                            # or above the second-entry level.
                            if trigger_price >= second_entry:
                                second_pullback_touched = True

                            # Step 2: after the pullback has happened,
                            # open only when price reclaims the level.
                            second_triggered = (
                                second_pullback_touched
                                and
                                trigger_price < second_entry
                            )

                        if second_triggered:

                            console.print(
                                value_panel(
                                    f"[{STYLE_SECOND}]"
                                    f"SECOND ENTRY TRIGGERED"
                                    f"[/{STYLE_SECOND}]",
                                    [
                                        (
                                            "Second entry signal",
                                            round(second_entry, DIGITS),
                                        ),
                                        (
                                            "Trigger Ask/Bid",
                                            round(trigger_price, DIGITS),
                                        ),
                                        (
                                            "Second entry SL",
                                            round(second_sl, DIGITS),
                                        ),
                                        (
                                            "First trade TP",
                                            round(second_tp, DIGITS),
                                        ),
                                        (
                                            "Second entry volume",
                                            second_volume,
                                        ),
                                        ("Magic", SECOND_ENTRY_MAGIC),
                                    ],
                                    style="magenta",
                                )
                            )


                            # The second trade must NOT recalculate TP from
                            # its actual fill. Meta receives the first
                            # trade's absolute TP and keeps it unchanged.
                            Meta.SetExecutionBasedTP(
                                enabled=False
                            )
                            
                            Meta.run(
                                symbol,
                                second_buy,
                                second_sell,
                                second_volume,
                                second_tp,
                                second_sl,
                                SECOND_ENTRY_MAGIC,
                                stopLossPure=True
                            )

                            # --------------------------------
                            # LOG SECOND-ENTRY ORDER
                            # --------------------------------

                            second_order_ticket = (
                                find_open_ticket(
                                    symbol,
                                    SECOND_ENTRY_MAGIC
                                )
                            )

                            if (
                                second_order_ticket
                                is not None
                            ):
                                second_entry_ticket[
                                    "ticket"
                                ] = second_order_ticket

                            log_event(
                                "order_opened",
                                label="second_entry",
                                symbol=symbol,
                                direction=second_direction,
                                magic=SECOND_ENTRY_MAGIC,
                                ticket=second_order_ticket,
                                volume=second_volume,
                                signal_entry=second_entry,
                                sl=second_sl,
                                tp=second_tp,
                                trigger_price=trigger_price,
                                pullback_touched=(
                                    second_pullback_touched
                                ),
                                setup_time=str(
                                    second_setup[
                                        "setup_time"
                                    ]
                                ),
                                entry_time=str(
                                    second_setup[
                                        "entry_time"
                                    ]
                                ),
                            )

                            # Re-check MT5 immediately so the local flag
                            # is synchronized without waiting for another
                            # strategy cycle.
                            second_position_exists_after, _ = get_trade_state(
                                symbol,
                                SECOND_ENTRY_MAGIC
                            )

                            if second_position_exists_after:
                                second_status = True
                                second_order_placed = True
                                second_setup = None
                                second_pullback_touched = False
                                
                            else:
                                console.print(
                                    f"[bold red]"
                                    f"SECOND ENTRY NOT CONFIRMED "
                                    f"(magic:{SECOND_ENTRY_MAGIC})"
                                    f"[/bold red]"
                                )

        # -------------------------------------------------------------
    # 0.5-second polling with compensated sleep.
    # The expensive full processing is still guarded by the
    # candle-change check above, so reducing the polling interval
    # does not cause a full historical rebuild every 0.5 seconds.
    # -------------------------------------------------------------
    elapsed = time_module.perf_counter() - loop_start_time
    remaining = LOOP_SECONDS - elapsed

    if remaining > 0:
        time_module.sleep(remaining)
