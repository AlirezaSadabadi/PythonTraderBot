#!/usr/bin/env python
__author__ = "Alireza Sadabadi"
__copyright__ = "Copyright (c) 2026 Alireza Sadabadi. All rights reserved."
__credits__ = ["Alireza Sadabadi"]
__license__ = "Apache"
__version__ = "10.0"
__maintainer__ = "Alireza Sadabadi"
__email__ = "alirezasadabady@gmail.com"
__status__ = "Test - centralized Meta.run state-safe execution, duration management, and invalid-stop protection"
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
from pathlib import Path

colorama_init()

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

# Entry timing relative to the FVG/spike pattern.
# True  -> the first entry must occur on the current candle (-1), using
#          a pullback to the candle immediately after the spike (-2).
# False -> preserve the previous behavior: an immediate pullback is accepted,
#          but if it does not happen, the pending setup may wait for later candles
#          while the other entry conditions remain valid.
ENTRY_IMMEDIATELY_AFTER_FVG = True

# Limit-order execution. When True, Entry 1 is never opened as a market
# order. The pending BUY_LIMIT/SELL_LIMIT is managed by Meta.py.
LIMIT_ORDER = True

# Price source for Entry 1 limit orders:
#   "PULLBACK_LOW" -> BUY: low / SELL: high of the candle after the spike (-2),
#                     then update to each following candle while the setup remains valid.
LIMIT_ORDER_PRICE_SOURCE = "PULLBACK_LOW"

# Require the candle before the spike, the spike, and the candle after it
# to all have the same direction/color. False disables this requirement.
USE_CANDLE_COLOR_FILTER = True

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
# DAILY NO-TRADE TIME FILTER (BROKER/CHART TIME)
# ------------------------------------------------------------
# These times are interpreted directly from the MT5 chart timestamps
# (broker/server/chart time). No timezone conversion is performed.
# Default: block new entries every day from 12:00 through 14:59.
USE_NO_TRADE_TIME_FILTER = False
NO_TRADE_START_TIME = "12:00"
NO_TRADE_END_TIME = "15:00"

# ------------------------------------------------------------
# WEEKDAY FILTER
# ------------------------------------------------------------
# True  = trading is allowed on that weekday.
# False = no new SP2L trades are allowed on that weekday.
USE_WEEKDAY_FILTER = False
TRADING_DAYS = {
    "Monday": True,
    "Tuesday": True,
    "Wednesday": True,
    "Thursday": True,
    "Friday": True,
    "Saturday": True,
    "Sunday": True,
}

# ------------------------------------------------------------
# TRADE DIRECTION FILTER
# ------------------------------------------------------------
# "BOTH" = BUY and SELL are allowed
# "BUY"  = BUY only
# "SELL" = SELL only
TRADE_DIRECTION = "BOTH"

# ------------------------------------------------------------
# TRADE DURATION MANAGEMENT
# ------------------------------------------------------------
# When enabled, an open Entry-1 position is managed by elapsed candle count.
# TP percentages mean the profit DISTANCE REMAINING from the ORIGINAL TP:
#   Stage 1: leave 40% of original TP distance (move TP 60% toward entry).
#   Stage 2: leave 25% of original TP distance (calculated from original TP,
#            not compounded from the Stage-1 TP).
# SL percentages mean how much of the ORIGINAL SL-to-entry distance to cover:
#   Stage 1: move SL 50% of the way toward entry.
#   Stage 2: move SL 100% of the way toward entry by default (break-even).
# Stage 3: after the final threshold, the position is closed.
# Thresholds use complete chart-candle intervals from the first confirmed
# active-position observation. The feature is disabled by default.
# Based on Aref Sayadi Idea
USE_TRADE_DURATION_MANAGEMENT = True
DURATION_STAGE1_CANDLES = 5
DURATION_STAGE1_TP_REMAINING_PCT = 40.0
DURATION_STAGE1_SL_TO_ENTRY_PCT = 50.0
DURATION_STAGE2_CANDLES = 7
DURATION_STAGE2_TP_REMAINING_PCT = 25.0
DURATION_STAGE2_SL_TO_ENTRY_PCT = 100.0
DURATION_STAGE3_CANDLES = 11

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

# ------------------------------------------------------------
# NEWS FILTER
# ------------------------------------------------------------
# The news monitor runs independently and writes a tiny local JSON file.
# SP2L never waits for the internet/API; it only reads this local file.
USE_NEWS_FILTER = True

NEWS_STATUS_FILE = str(
    Path(__file__).with_name("news_status.json")
)

# If True, close positions belonging to both SP2L magics (MAGIC and
# SECOND_ENTRY_MAGIC) when a high-impact news block becomes active.
CLOSE_ON_HIGH_IMPACT_NEWS = True

# False -> close only SP2L positions.
# True  -> close ALL open positions on SYMBOL when news becomes active.
CLOSE_ALL_POSITIONS_ON_NEWS = False

# Always prevent a new SP2L entry while the news block is active.
BLOCK_NEW_ENTRIES_ON_NEWS = True

# The main loop runs every 0.5 second, but the local status file is inspected
# only once per minute. mtime_ns is checked first; JSON is parsed only on change.
# The main trading loop still runs every 0.5 second, but the local news JSON
# is checked only once per minute. The mtime_ns check happens first; JSON is
# parsed only when the file has actually changed.
NEWS_CHECK_EVERY_LOOP = True
NEWS_FILE_CHECK_INTERVAL_SECONDS = 60
NEWS_STATUS_MAX_AGE_SECONDS = 4200
# A refresh normally happens every 60 minutes. Allow a short grace period
# so SP2L does not report a false outage while news_monitor is refreshing.
NEWS_STATUS_REFRESH_GRACE_SECONDS = 5 * 60
NEWS_UNAVAILABLE_LOG_INTERVAL_SECONDS = 30 * 60

# Treat the two SP2L magics as this strategy's own positions.
NEWS_CLOSE_MAGICS = [MAGIC, SECOND_ENTRY_MAGIC]

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


def _parse_hhmm(value):
    """Return (hour, minute) for a HH:MM setting, or raise ValueError."""
    text = str(value).strip()
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time '{value}'. Expected HH:MM.")
    hour = int(parts[0])
    minute = int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid time '{value}'. Expected HH:MM.")
    return hour, minute


# ============================================================
# CONFIGURATION VALIDATION
# ============================================================

# Fail early on invalid user settings instead of silently changing the
# strategy behavior.
_parse_hhmm(NO_TRADE_START_TIME)
_parse_hhmm(NO_TRADE_END_TIME)
if str(TRADE_DIRECTION).upper().strip() not in ("BOTH", "BUY", "SELL"):
    raise ValueError("TRADE_DIRECTION must be 'BOTH', 'BUY', or 'SELL'.")
if DURATION_STAGE1_CANDLES <= 0 or DURATION_STAGE2_CANDLES <= DURATION_STAGE1_CANDLES or DURATION_STAGE3_CANDLES <= DURATION_STAGE2_CANDLES:
    raise ValueError("Duration thresholds must be positive and strictly increasing.")
for _name, _pct in (("DURATION_STAGE1_TP_REMAINING_PCT", DURATION_STAGE1_TP_REMAINING_PCT), ("DURATION_STAGE1_SL_TO_ENTRY_PCT", DURATION_STAGE1_SL_TO_ENTRY_PCT), ("DURATION_STAGE2_TP_REMAINING_PCT", DURATION_STAGE2_TP_REMAINING_PCT), ("DURATION_STAGE2_SL_TO_ENTRY_PCT", DURATION_STAGE2_SL_TO_ENTRY_PCT)):
    if not (0.0 <= float(_pct) <= 100.0):
        raise ValueError(f"{_name} must be between 0 and 100.")
if DURATION_STAGE2_TP_REMAINING_PCT > DURATION_STAGE1_TP_REMAINING_PCT:
    raise ValueError("Stage 2 TP remaining percentage should not exceed Stage 1 TP remaining percentage.")

# ============================================================
# PRINT SETTINGS
# ============================================================

print("-" * 75)
print("OPTIMIZED SP2L TRADER VER10.0-DurationManagement-NoTradeTimeFilter-WeekdayFilter")
print("-" * 75)
print("Symbol              :", SYMBOL)
print("Point               :", BROKER_POINT)
print("Digits              :", DIGITS)
print("Spike multiplier    :", SPIKE_CANDLE_SIZE)
print("Immediate FVG entry  :", ENTRY_IMMEDIATELY_AFTER_FVG)
print("Limit order         :", LIMIT_ORDER)
print("Limit price source  :", LIMIT_ORDER_PRICE_SOURCE)
print("Candle color filter :", USE_CANDLE_COLOR_FILTER)
print("Gap points          :", PGAP_POINTS)
print("Max SL points       :", MAX_SL_DISTANCE_POINTS)
print("LowerLow/HH SL      :", USE_LOWERLOW_HIGHERHIGH_SL)
print("TP                  :", f"{TP_R}R")
print("Second entry        :", USE_SECOND_ENTRY)
print("Second entry volume :", SECOND_ENTRY_VOLUME_MULTIPLIER)
print("EMA filter          :", USE_EMA_FILTER)
print("EMA period          :", EMA_PERIOD)
print("EMA entry rule      :", "BUY pullback/limit > EMA | SELL pullback/limit < EMA")
print("Trend filter        :", USE_TREND_FILTER)
print("Max opposite moves  :", MAX_OPPOSITE_MOVES)
print("Range filter        :", USE_RANGE_FILTER)
print("ADX period          :", ADX_PERIOD)
print("Minimum ADX         :", MIN_ADX)
print("ADX rising filter   :", USE_ADX_RISING_FILTER)
print("Session filter      :", USE_SESSION_FILTER)
print("Session timezone    :", SESSION_TIMEZONE)
print(
    "Session             :",
    f"{SESSION_START_HOUR:02d}:00 - {SESSION_END_HOUR:02d}:00"
)
print("No-trade time filter:", USE_NO_TRADE_TIME_FILTER)
print(
    "No-trade time       :",
    f"{NO_TRADE_START_TIME} - {NO_TRADE_END_TIME} (chart/server time)"
)
print("Weekday filter      :", USE_WEEKDAY_FILTER)
print("Trading days        :", TRADING_DAYS)
print("Trade direction     :", TRADE_DIRECTION)
print("Duration management :", USE_TRADE_DURATION_MANAGEMENT)
print("Duration stage 1    :", DURATION_STAGE1_CANDLES, "candles | TP remaining:", DURATION_STAGE1_TP_REMAINING_PCT, "% of initial target | SL toward entry:", DURATION_STAGE1_SL_TO_ENTRY_PCT, "%")
print("Duration stage 2    :", DURATION_STAGE2_CANDLES, "candles | TP remaining:", DURATION_STAGE2_TP_REMAINING_PCT, "% of initial target | SL toward entry:", DURATION_STAGE2_SL_TO_ENTRY_PCT, "%")
print("Duration stage 3    :", DURATION_STAGE3_CANDLES, "candles | CLOSE POSITION")
print("Magic               :", MAGIC)
print("Second entry magic  :", SECOND_ENTRY_MAGIC)
print("Lot                 :", LOT)
print("News filter         :", USE_NEWS_FILTER)
print("News status file    :", NEWS_STATUS_FILE)
print("Close on news       :", CLOSE_ON_HIGH_IMPACT_NEWS)
print("Close all on news   :", CLOSE_ALL_POSITIONS_ON_NEWS)
print("Block new entries   :", BLOCK_NEW_ENTRIES_ON_NEWS)
print("-" * 75)


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
# TIME / DAY / DIRECTION FILTERS
# ============================================================

def _minutes_of_day(timestamp):
    return int(timestamp.hour) * 60 + int(timestamp.minute)


def is_no_trade_time(timestamp):
    """Check the daily no-trade window using raw MT5 chart/server time."""
    if not USE_NO_TRADE_TIME_FILTER or timestamp is None:
        return False

    start_h, start_m = _parse_hhmm(NO_TRADE_START_TIME)
    end_h, end_m = _parse_hhmm(NO_TRADE_END_TIME)
    start = start_h * 60 + start_m
    end = end_h * 60 + end_m
    now = _minutes_of_day(timestamp)

    if start == end:
        # Explicitly treat equal endpoints as a full-day block. This avoids
        # accidentally disabling the filter when a user enters 00:00/00:00.
        return True

    if start < end:
        return start <= now < end

    # Overnight window, e.g. 22:00 -> 02:00.
    return now >= start or now < end


def is_weekday_blocked(timestamp):
    """Check the weekday allow-list using raw MT5 chart/server time."""
    if not USE_WEEKDAY_FILTER or timestamp is None:
        return False

    day_name = timestamp.strftime("%A")
    return not bool(TRADING_DAYS.get(day_name, True))


def get_entry_block_reason(timestamp):
    """Return a short reason when new entries are blocked, otherwise None."""
    if is_no_trade_time(timestamp):
        return f"NO-TRADE TIME {NO_TRADE_START_TIME}-{NO_TRADE_END_TIME}"

    if is_weekday_blocked(timestamp):
        return f"WEEKDAY BLOCKED ({timestamp.strftime('%A')})"

    return None


def direction_allows(direction):
    """Return True when the configured BUY/SELL direction is allowed."""
    mode = str(TRADE_DIRECTION).upper().strip()
    if mode == "BOTH":
        return True
    if mode == "BUY":
        return direction == "BUY"
    if mode == "SELL":
        return direction == "SELL"
    # Fail closed for an invalid configuration.
    return False


# ============================================================
# ENTRY FILTERS
# ============================================================

def entry_filters_are_valid(
    data,
    entry_pos,
    direction,
    check_ema=True
):

    entry_idx = data.index[entry_pos]

    # --------------------------------------------------------
    # EMA FILTER
    # --------------------------------------------------------

    if USE_EMA_FILTER and check_ema:

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
# The current candle (-1) is NOT part of the FVG pattern itself.
# It is reserved for the entry-timing rule controlled by
# ENTRY_IMMEDIATELY_AFTER_FVG.
# ============================================================

def detect_buy_setup(data):

    if len(data) < 5:
        return False

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

    # Optional candle-color filter. The three candles involved in the
    # pattern are: candle before spike (-4), spike (-3), candle after spike (-2).
    # When disabled, no candle-direction requirement is imposed.
    candle_color_ok = (
        (
            (data["close"].iloc[-4] > data["open"].iloc[-4])
            & (data["close"].iloc[-3] > data["open"].iloc[-3])
            & (data["close"].iloc[-2] > data["open"].iloc[-2])
        )
        if USE_CANDLE_COLOR_FILTER
        else True
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

    )

    # BUY spike structure: the spike candle must form a local LOW.
    # Low(before) < Low(spike) < Low(after)
    spike_low_structure_ok = (
        data["low"].iloc[-3] > data["low"].iloc[-4]
    ) & (
        data["low"].iloc[-2] > data["low"].iloc[-3]
    )

    return (
        buy1
        & buy2
        & buy3
        & buy4
        & candle_color_ok
        & p_gap_buy
        & spike_buy
        & spike_low_structure_ok
    )


def detect_sell_setup(data):

    if len(data) < 5:
        return False

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

    # Optional candle-color filter for SELL: all three pattern candles
    # must be bearish when the option is enabled.
    candle_color_ok = (
        (
            (data["close"].iloc[-4] < data["open"].iloc[-4])
            & (data["close"].iloc[-3] < data["open"].iloc[-3])
            & (data["close"].iloc[-2] < data["open"].iloc[-2])
        )
        if USE_CANDLE_COLOR_FILTER
        else True
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

    )

    # SELL spike structure: the spike candle must form a local HIGH.
    # High(before) > High(spike) > High(after)
    spike_high_structure_ok = (
        data["high"].iloc[-3] < data["high"].iloc[-4]
    ) & (
        data["high"].iloc[-2] < data["high"].iloc[-3]
    )

    return (
        sell1
        & sell2
        & sell3
        & sell4
        & candle_color_ok
        & p_gap_sell
        & spike_sell
        & spike_high_structure_ok
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
        "second_entry_active": False,
        "limit_order_placed": False,
        "limit_order_ticket": None,
        "limit_price": None
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
        "second_entry_active": False,
        "limit_order_placed": False,
        "limit_order_ticket": None,
        "limit_price": None
    }


# ============================================================
# LIMIT ORDER HELPERS
# ============================================================

def _limit_price_for_buy(data):
   
    if LIMIT_ORDER_PRICE_SOURCE == "PULLBACK_LOW":
        return float(data["low"].iloc[-2])
    raise ValueError(
        f"Unsupported LIMIT_ORDER_PRICE_SOURCE: {LIMIT_ORDER_PRICE_SOURCE}"
    )


def _limit_price_for_sell(data):
   
    if LIMIT_ORDER_PRICE_SOURCE == "PULLBACK_LOW":
        return float(data["high"].iloc[-2])
    raise ValueError(
        f"Unsupported LIMIT_ORDER_PRICE_SOURCE: {LIMIT_ORDER_PRICE_SOURCE}"
    )


def _limit_order_price_is_valid(symbol, direction, price):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return False

    if direction == "BUY":
        return float(price) < float(tick.ask)

    return float(price) > float(tick.bid)



def _ema_value_at(data, pos):
    """Return the EMA value belonging to a specific candle."""
    try:
        value = float(data.iloc[pos]["EMA"])
    except (IndexError, KeyError, TypeError, ValueError):
        return None
    return value if np.isfinite(value) else None


def _price_is_on_correct_ema_side(price, ema, direction):
    """BUY must be strictly above EMA; SELL must be strictly below EMA."""
    if ema is None or not np.isfinite(float(ema)):
        return False
    if direction == "BUY":
        return float(price) > float(ema)
    return float(price) < float(ema)


def _limit_reference_ema(data):
    """Use the EMA from the same completed candle that supplies the limit price."""
   
    if LIMIT_ORDER_PRICE_SOURCE == "PULLBACK_LOW":
        return _ema_value_at(data, -2)
    return None


def _limit_order_state_is_valid(data, pending, direction, entry):
    """Validate a live limit setup without requiring a pullback."""
    sl = float(pending["sl"])

    risk = (entry - sl) if direction == "BUY" else (sl - entry)

    if risk <= 0:
        return None

    if risk > MAX_SL_DISTANCE_PRICE:
        return "INVALID"

    # EMA filter for Limit Order: the limit price itself must be on the
    # correct side of EMA60. The EMA comes from the same completed candle
    # that supplied the configured limit price, so it is stable intrabar.
    if USE_EMA_FILTER:
        limit_ema = _limit_reference_ema(data)
        if not _price_is_on_correct_ema_side(entry, limit_ema, direction):
            return "INVALID"

    try:
        start_pos = data.index.get_loc(pending["setup_pos_time"])
    except KeyError:
        return None

    entry_pos = len(data) - 1

    # A limit order may wait without a pullback, but the trend/filter
    # conditions remain live. In particular, the trend filter can invalidate
    # an outstanding order after MAX_OPPOSITE_MOVES is exceeded.
    if direction == "BUY":
        if not buy_trend_is_valid(data, start_pos, entry_pos):
            return "INVALID"
    else:
        if not sell_trend_is_valid(data, start_pos, entry_pos):
            return "INVALID"

    if not entry_filters_are_valid(data, entry_pos, direction, check_ema=False):
        return "INVALID"

    return {
        "direction": direction,
        "entry": float(entry),
        "sl": sl,
        "risk": risk,
        "setup_time": pending["setup_time"],
        "entry_time": data.index[-1],
        "spike_body": pending["spike_body"]
    }


# ============================================================
# FIND FIRST VALID BUY ENTRY
#
# This is the live equivalent of the Optimized backtest's
# find_first_buy_entry(). It does NOT enter immediately when
# a setup is detected.
# ============================================================

def check_pending_buy(
    symbol,
    data,
    pending
):

    if len(data) < 2:
        return None

    sl = pending["sl"]
    current_candle_time = data.index[-1]

    if LIMIT_ORDER:
        # ENTRY_IMMEDIATELY_AFTER_FVG=True means exactly one limit order may
        # be placed on the candle after the spike. If that candle passes,
        # the pattern expires; no later repricing is allowed.
        if (
            ENTRY_IMMEDIATELY_AFTER_FVG
            and current_candle_time != pending["setup_time"]
        ):
            return "EXPIRED"

        if pending.get("limit_order_placed", False):
            state = Meta.run(
                symbol, False, False, lot, magic=MAGIC,
                pending_action="state"
            )
            if state is None or not state.get("query_ok", False):
                # Never invalidate a live setup because MT5 temporarily failed
                # to answer. Reconcile it on the next polling cycle.
                return None

            order = state.get("order")
            position = state.get("position")
            if order is None:
                # The order may have filled and moved from orders_get() to
                # positions_get(). Invalidate only when both are genuinely absent.
                return None if position is not None else "INVALID"

        try:
            entry = _limit_price_for_buy(data)
        except ValueError as exc:
            print(exc)
            return "INVALID"

        result = _limit_order_state_is_valid(
            data, pending, "BUY", entry
        )

        if result in (None, "INVALID"):
            return result

        # A quote-side mismatch is temporary, not a strategy invalidation.
        # Keep the setup alive and retry on the next poll while it is eligible.
        if not pending.get("limit_order_placed", False) and not _limit_order_price_is_valid(symbol, "BUY", entry):
            if not pending.get("limit_price_wait_logged", False):
                print(
                    f"{Fore.YELLOW}LIMIT ORDER WAITING | BUY | price:{round(entry, DIGITS)} "
                    f"is temporarily on the wrong side of market; setup retained for retry."
                    f"{Style.RESET_ALL}"
                )
                pending["limit_price_wait_logged"] = True
            return None
        pending["limit_price_wait_logged"] = False

        result["limit_order"] = True
        result["limit_price"] = entry
        # For PULLBACK_LOW, the reference level is the completed candle
        # immediately before the current candle. Repricing is therefore a
        # once-per-reference-candle operation, not a 0.5-second operation.
        if LIMIT_ORDER_PRICE_SOURCE == "PULLBACK_LOW":
            result["limit_reference_time"] = data.index[-2]
        else:
            result["limit_reference_time"] = pending["setup_time"]
        previous_reference = pending.get("limit_reference_time")
        result["limit_price_changed"] = (
            LIMIT_ORDER_PRICE_SOURCE == "PULLBACK_LOW"
            and previous_reference is not None
            and previous_reference != result["limit_reference_time"]
            and pending.get("limit_price") is not None
            and abs(float(pending["limit_price"]) - entry) > 10 ** (-DIGITS)
        )
        return result

    # Original market-entry logic remains unchanged when LIMIT_ORDER=False.
    if (
        ENTRY_IMMEDIATELY_AFTER_FVG
        and current_candle_time != pending["setup_time"]
    ):
        return "EXPIRED"

    current_low = float(data["low"].iloc[-1])
    current_high = float(data["high"].iloc[-1])
    previous_low = float(data["low"].iloc[-2])

    if ENTRY_IMMEDIATELY_AFTER_FVG:
        reference_level = previous_low
        if not (current_low <= reference_level <= current_high):
            return None
        entry = reference_level
    else:
        if current_low >= previous_low:
            return None
        entry = current_low

    risk = entry - sl
    if risk <= 0:
        return None
    if risk > MAX_SL_DISTANCE_PRICE:
        return "INVALID"

    # EMA filter for Market BUY: the actual pullback/entry price must be
    # strictly above the EMA of the candle used for that pullback.
    if USE_EMA_FILTER:
        ema_pos = -2 if ENTRY_IMMEDIATELY_AFTER_FVG else -1
        pullback_ema = _ema_value_at(data, ema_pos)
        if not _price_is_on_correct_ema_side(entry, pullback_ema, "BUY"):
            return None

    try:
        start_pos = data.index.get_loc(pending["setup_pos_time"])
    except KeyError:
        return None

    entry_pos = len(data) - 1
    if not buy_trend_is_valid(data, start_pos, entry_pos):
        return None
    if not entry_filters_are_valid(data, entry_pos, "BUY"):
        return None

    return {
        "direction": "BUY",
        "entry": entry,
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
    symbol,
    data,
    pending
):

    if len(data) < 2:
        return None

    sl = pending["sl"]
    current_candle_time = data.index[-1]

    if LIMIT_ORDER:
        if (
            ENTRY_IMMEDIATELY_AFTER_FVG
            and current_candle_time != pending["setup_time"]
        ):
            return "EXPIRED"

        if pending.get("limit_order_placed", False):
            state = Meta.run(
                symbol, False, False, lot, magic=MAGIC,
                pending_action="state"
            )
            if state is None or not state.get("query_ok", False):
                # Never invalidate a live setup because MT5 temporarily failed
                # to answer. Reconcile it on the next polling cycle.
                return None

            order = state.get("order")
            position = state.get("position")
            if order is None:
                # The order may have filled and moved from orders_get() to
                # positions_get(). Invalidate only when both are genuinely absent.
                return None if position is not None else "INVALID"

        try:
            entry = _limit_price_for_sell(data)
        except ValueError as exc:
            print(exc)
            return "INVALID"

        result = _limit_order_state_is_valid(
            data, pending, "SELL", entry
        )

        if result in (None, "INVALID"):
            return result

        # A quote-side mismatch is temporary, not a strategy invalidation.
        # Keep the setup alive and retry on the next poll while it is eligible.
        if not pending.get("limit_order_placed", False) and not _limit_order_price_is_valid(symbol, "SELL", entry):
            if not pending.get("limit_price_wait_logged", False):
                print(
                    f"{Fore.YELLOW}LIMIT ORDER WAITING | SELL | price:{round(entry, DIGITS)} "
                    f"is temporarily on the wrong side of market; setup retained for retry."
                    f"{Style.RESET_ALL}"
                )
                pending["limit_price_wait_logged"] = True
            return None
        pending["limit_price_wait_logged"] = False

        result["limit_order"] = True
        result["limit_price"] = entry
        # For PULLBACK_LOW, the reference level is the completed candle
        # immediately before the current candle. Repricing is therefore a
        # once-per-reference-candle operation, not a 0.5-second operation.
        if LIMIT_ORDER_PRICE_SOURCE == "PULLBACK_LOW":
            result["limit_reference_time"] = data.index[-2]
        else:
            result["limit_reference_time"] = pending["setup_time"]
        previous_reference = pending.get("limit_reference_time")
        result["limit_price_changed"] = (
            LIMIT_ORDER_PRICE_SOURCE == "PULLBACK_LOW"
            and previous_reference is not None
            and previous_reference != result["limit_reference_time"]
            and pending.get("limit_price") is not None
            and abs(float(pending["limit_price"]) - entry) > 10 ** (-DIGITS)
        )
        return result

    if (
        ENTRY_IMMEDIATELY_AFTER_FVG
        and current_candle_time != pending["setup_time"]
    ):
        return "EXPIRED"

    current_high = float(data["high"].iloc[-1])
    current_low = float(data["low"].iloc[-1])
    previous_high = float(data["high"].iloc[-2])

    if ENTRY_IMMEDIATELY_AFTER_FVG:
        reference_level = previous_high
        if not (current_low <= reference_level <= current_high):
            return None
        entry = reference_level
    else:
        if current_high <= previous_high:
            return None
        entry = current_high

    risk = sl - entry
    if risk <= 0:
        return None
    if risk > MAX_SL_DISTANCE_PRICE:
        return "INVALID"

    # EMA filter for Market SELL: the actual pullback/entry price must be
    # strictly below the EMA of the candle used for that pullback.
    if USE_EMA_FILTER:
        ema_pos = -2 if ENTRY_IMMEDIATELY_AFTER_FVG else -1
        pullback_ema = _ema_value_at(data, ema_pos)
        if not _price_is_on_correct_ema_side(entry, pullback_ema, "SELL"):
            return None

    try:
        start_pos = data.index.get_loc(pending["setup_pos_time"])
    except KeyError:
        return None

    entry_pos = len(data) - 1
    if not sell_trend_is_valid(data, start_pos, entry_pos):
        return None
    if not entry_filters_are_valid(data, entry_pos, "SELL"):
        return None

    return {
        "direction": "SELL",
        "entry": entry,
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
    """Read live MT5 position state without confusing query failure with no position."""
    try:
        positions = mt5.positions_get(symbol=symbol)
    except BaseException as exc:
        print(
            f"{Fore.YELLOW}TRADE STATE | positions_get exception for {symbol}: "
            f"{exc} -> cycle skipped{Style.RESET_ALL}"
        )
        return None, None

    if positions is None:
        print(
            f"{Fore.YELLOW}TRADE STATE | positions_get failed for {symbol}: "
            f"{mt5.last_error()} -> cycle skipped{Style.RESET_ALL}"
        )
        return None, None

    matching = [
        pos for pos in positions
        if int(getattr(pos, "magic", -1)) == int(magic)
    ]

    if not matching:
        return False, None

    columns = [
        "ticket", "position", "symbol", "volume", "magic",
        "profit", "price", "tp", "sl", "trade_size", "time_open"
    ]
    rows = []
    for pos in matching:
        info = mt5.symbol_info(pos.symbol)
        contract_size = (
            float(info.trade_contract_size)
            if info is not None
            else 0.0
        )
        rows.append([
            pos.ticket, pos.type, pos.symbol, pos.volume, pos.magic,
            pos.profit, pos.price_open, pos.tp, pos.sl, contract_size, int(getattr(pos, "time", 0))
        ])

    row = pd.DataFrame(rows, columns=columns)
    denominator = row["price"] * row["trade_size"] * row["volume"]
    row["profit %"] = np.where(denominator != 0, row["profit"] / denominator, 0.0)
    return True, row.reset_index(drop=True)



def _duration_tp_from_initial(entry, initial_tp, remaining_pct):
    """Return a TP leaving remaining_pct of the ORIGINAL TP-to-entry distance."""
    return entry + ((initial_tp - entry) * (float(remaining_pct) / 100.0))


def _duration_sl_toward_entry(entry, initial_sl, to_entry_pct):
    """Move SL by to_entry_pct of the ORIGINAL SL-to-entry distance."""
    return entry + ((initial_sl - entry) * (1.0 - (float(to_entry_pct) / 100.0)))


def manage_trade_duration(symbol, position_row, lot, magic=MAGIC, current_candle_time=None):
    """
    Manage an already-open Entry-1 position according to elapsed candle count.

    TP stages are always calculated from the initial TP captured for this ticket,
    so Stage 2 leaves 25% of the original target distance instead of compounding
    another reduction from the Stage-1 TP. SL stages are likewise measured from
    the initial SL captured for this ticket.

    Returns:
        "OPEN"   -> position remains open
        "CLOSED" -> stage 3 close was requested/executed
        None     -> management could not safely complete this cycle
    """
    if not USE_TRADE_DURATION_MANAGEMENT or position_row is None or position_row.empty:
        return "OPEN"

    row = position_row.iloc[0]
    ticket = int(row["ticket"])
    direction_buy = int(row["position"]) == int(mt5.POSITION_TYPE_BUY)
    entry = float(row["price"])
    current_tp = float(row["tp"] or 0.0)
    current_sl = float(row["sl"] or 0.0)
    opened_epoch = int(row.get("time_open", 0) or 0)

    if opened_epoch <= 0:
        print(f"{Fore.YELLOW}DURATION MANAGEMENT | ticket {ticket}: open time unavailable; skipping cycle.{Style.RESET_ALL}")
        return None

    _timeframe_seconds = {
        mt5.TIMEFRAME_M1: 60, mt5.TIMEFRAME_M2: 120, mt5.TIMEFRAME_M3: 180,
        mt5.TIMEFRAME_M4: 240, mt5.TIMEFRAME_M5: 300, mt5.TIMEFRAME_M6: 360,
        mt5.TIMEFRAME_M10: 600, mt5.TIMEFRAME_M12: 720, mt5.TIMEFRAME_M15: 900,
        mt5.TIMEFRAME_M20: 1200, mt5.TIMEFRAME_M30: 1800, mt5.TIMEFRAME_H1: 3600,
        mt5.TIMEFRAME_H2: 7200, mt5.TIMEFRAME_H3: 10800, mt5.TIMEFRAME_H4: 14400,
        mt5.TIMEFRAME_H6: 21600, mt5.TIMEFRAME_H8: 28800, mt5.TIMEFRAME_H12: 43200,
        mt5.TIMEFRAME_D1: 86400, mt5.TIMEFRAME_W1: 604800, mt5.TIMEFRAME_MN1: 2592000,
    }
    timeframe_seconds = _timeframe_seconds.get(TIMEFRAME)
    if timeframe_seconds is None:
        print(f"{Fore.YELLOW}DURATION MANAGEMENT | unsupported TIMEFRAME {TIMEFRAME}; skipping cycle.{Style.RESET_ALL}")
        return None

    # IMPORTANT: count chart candles from the first candle observed while this
    # ticket is confirmed as an active position. This deliberately prevents a
    # stale timestamp, timezone mismatch, or delayed fill-state transition from
    # triggering Stage 1 immediately after entry.
    #
    # MT5 rate timestamps are returned as naive UTC timestamps by Meta.GetRates.
    # Convert them consistently to Unix epoch; do not fall back to wall-clock
    # elapsed time when the candle timestamp is unavailable.
    if current_candle_time is None:
        print(
            f"{Fore.YELLOW}DURATION MANAGEMENT | ticket {ticket}: current candle time unavailable; "
            f"skipping safely.{Style.RESET_ALL}"
        )
        return None

    try:
        candle_ts = pd.Timestamp(current_candle_time)
        if candle_ts.tzinfo is None:
            candle_ts = candle_ts.tz_localize("UTC")
        else:
            candle_ts = candle_ts.tz_convert("UTC")
        current_candle_epoch = float(candle_ts.timestamp())
    except (TypeError, ValueError, OverflowError) as exc:
        print(
            f"{Fore.YELLOW}DURATION MANAGEMENT | ticket {ticket}: invalid candle timestamp "
            f"{current_candle_time!r} ({exc}); skipping safely.{Style.RESET_ALL}"
        )
        return None

    # On the first observation, save original TP/SL and establish a candle
    # baseline, then EXIT this cycle without modifying the position. Stage 1
    # can only run after at least DURATION_STAGE1_CANDLES complete candle
    # intervals have elapsed from this baseline.
    if ticket not in duration_tracking_start_candles:
        if current_tp <= 0 or current_sl <= 0:
            print(
                f"{Fore.YELLOW}DURATION MANAGEMENT | cannot capture original TP/SL "
                f"for ticket {ticket}; skipping safely.{Style.RESET_ALL}"
            )
            return None

        duration_tracking_start_candles[ticket] = current_candle_epoch
        duration_initial_prices[ticket] = {"tp": current_tp, "sl": current_sl}
        print(
            f"{Fore.CYAN}DURATION MANAGEMENT | TRACKING STARTED | "
            f"{('BUY' if direction_buy else 'SELL')} ticket:{ticket} | "
            f"baseline candle:{candle_ts.strftime('%Y-%m-%d %H:%M:%S')} UTC | "
            f"Stage 1 earliest after {DURATION_STAGE1_CANDLES} complete candles. "
            f"No SL/TP change on this cycle.{Style.RESET_ALL}"
        )
        return "OPEN"

    baseline_epoch = float(duration_tracking_start_candles[ticket])
    elapsed_candles = max(
        0.0,
        (current_candle_epoch - baseline_epoch) / float(timeframe_seconds)
    )
    completed_candles = int(elapsed_candles)

    # Do not act unless the current candle has advanced by the configured
    # number of full candle intervals from the tracking baseline.
    if completed_candles < int(DURATION_STAGE1_CANDLES):
        return "OPEN"

    # Original levels were captured when the candle baseline was initialized.
    # Subsequent stages always use these stored values, never compounded levels.
    if ticket not in duration_initial_prices:
        print(
            f"{Fore.YELLOW}DURATION MANAGEMENT | ticket {ticket}: original TP/SL state missing; "
            f"skipping safely.{Style.RESET_ALL}"
        )
        return None

    initial_tp = float(duration_initial_prices[ticket]["tp"])
    initial_sl = float(duration_initial_prices[ticket]["sl"])

    # Stage 3 has priority; close through Meta.run and let the usual state
    # reconciliation confirm the position is actually gone.
    if completed_candles >= int(DURATION_STAGE3_CANDLES):
        result = Meta.run(
            symbol, False, False, lot, magic=magic,
            position_action="close", position_ticket=ticket,
        )
        if result is not None and getattr(result, "retcode", None) in (
            mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL, mt5.TRADE_RETCODE_PLACED,
        ):
            print(
                f"{Fore.YELLOW}DURATION MANAGEMENT | STAGE 3 | "
                f"{('BUY' if direction_buy else 'SELL')} ticket:{ticket} | "
                f"completed:{completed_candles} candles | elapsed:{elapsed_candles:.2f} | POSITION CLOSE REQUEST ACCEPTED{Style.RESET_ALL}"
            )
            return "CLOSED"
        print(
            f"{Fore.YELLOW}DURATION MANAGEMENT | STAGE 3 CLOSE FAILED | "
            f"ticket:{ticket} | completed:{completed_candles} | elapsed:{elapsed_candles:.2f} candles | "
            f"result:{getattr(result, 'comment', 'None')}{Style.RESET_ALL}"
        )
        return None

    if current_tp <= 0 or current_sl <= 0:
        print(f"{Fore.YELLOW}DURATION MANAGEMENT | invalid current TP/SL for ticket {ticket}; skipping cycle.{Style.RESET_ALL}")
        return None

    # Stage 2: set target from ORIGINAL TP and SL from ORIGINAL SL. If Stage 1
    # was not observed in this process (e.g. a delayed first poll), apply it first.
    if completed_candles >= int(DURATION_STAGE2_CANDLES) and ticket not in duration_stage2_tickets:
        if ticket not in duration_stage1_tickets:
            stage1_tp = _duration_tp_from_initial(entry, initial_tp, DURATION_STAGE1_TP_REMAINING_PCT)
            stage1_sl = _duration_sl_toward_entry(entry, initial_sl, DURATION_STAGE1_SL_TO_ENTRY_PCT)
            stage1_result = Meta.run(
                symbol, False, False, lot, magic=magic,
                position_action="modify", position_ticket=ticket,
                position_sl=stage1_sl, position_tp=stage1_tp,
            )
            if stage1_result is not None and getattr(stage1_result, "retcode", None) in (
                mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED,
            ):
                duration_stage1_tickets.add(ticket)
                print(
                    f"{Fore.CYAN}DURATION MANAGEMENT | STAGE 1 | "
                    f"{('BUY' if direction_buy else 'SELL')} ticket:{ticket} | "
                    f"completed:{completed_candles} | elapsed:{elapsed_candles:.2f} candles | "
                    f"TP:{round(current_tp, DIGITS)} -> {round(stage1_tp, DIGITS)} "
                    f"(remaining {DURATION_STAGE1_TP_REMAINING_PCT:.1f}% of initial) | "
                    f"SL:{round(current_sl, DIGITS)} -> {round(stage1_sl, DIGITS)}{Style.RESET_ALL}"
                )
            else:
                print(f"{Fore.YELLOW}DURATION MANAGEMENT | STAGE 1 MODIFY FAILED | ticket:{ticket} | result:{getattr(stage1_result, 'comment', 'None')}{Style.RESET_ALL}")
            return "OPEN"

        new_tp = _duration_tp_from_initial(entry, initial_tp, DURATION_STAGE2_TP_REMAINING_PCT)
        new_sl = _duration_sl_toward_entry(entry, initial_sl, DURATION_STAGE2_SL_TO_ENTRY_PCT)
        result = Meta.run(
            symbol, False, False, lot, magic=magic,
            position_action="modify", position_ticket=ticket,
            position_sl=new_sl, position_tp=new_tp,
        )
        if result is not None and getattr(result, "retcode", None) in (
            mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED,
        ):
            duration_stage2_tickets.add(ticket)
            print(
                f"{Fore.CYAN}DURATION MANAGEMENT | STAGE 2 | "
                f"{('BUY' if direction_buy else 'SELL')} ticket:{ticket} | "
                f"elapsed:{elapsed_candles:.2f} candles | "
                f"TP:{round(current_tp, DIGITS)} -> {round(new_tp, DIGITS)} "
                f"(remaining {DURATION_STAGE2_TP_REMAINING_PCT:.1f}% of initial) | "
                f"SL:{round(current_sl, DIGITS)} -> {round(new_sl, DIGITS)}{Style.RESET_ALL}"
            )
            return "OPEN"
        print(f"{Fore.YELLOW}DURATION MANAGEMENT | STAGE 2 MODIFY FAILED | ticket:{ticket} | result:{getattr(result, 'comment', 'None')}{Style.RESET_ALL}")
        return None

    # Stage 1: only once per ticket, even though the main loop polls every 0.5s.
    if completed_candles >= int(DURATION_STAGE1_CANDLES) and ticket not in duration_stage1_tickets:
        new_tp = _duration_tp_from_initial(entry, initial_tp, DURATION_STAGE1_TP_REMAINING_PCT)
        new_sl = _duration_sl_toward_entry(entry, initial_sl, DURATION_STAGE1_SL_TO_ENTRY_PCT)
        result = Meta.run(
            symbol, False, False, lot, magic=magic,
            position_action="modify", position_ticket=ticket,
            position_sl=new_sl, position_tp=new_tp,
        )
        if result is not None and getattr(result, "retcode", None) in (
            mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED,
        ):
            duration_stage1_tickets.add(ticket)
            print(
                f"{Fore.CYAN}DURATION MANAGEMENT | STAGE 1 | "
                f"{('BUY' if direction_buy else 'SELL')} ticket:{ticket} | "
                f"elapsed:{elapsed_candles:.2f} candles | "
                f"TP:{round(current_tp, DIGITS)} -> {round(new_tp, DIGITS)} "
                f"(remaining {DURATION_STAGE1_TP_REMAINING_PCT:.1f}% of initial) | "
                f"SL:{round(current_sl, DIGITS)} -> {round(new_sl, DIGITS)}{Style.RESET_ALL}"
            )
        else:
            print(f"{Fore.YELLOW}DURATION MANAGEMENT | STAGE 1 MODIFY FAILED | ticket:{ticket} | result:{getattr(result, 'comment', 'None')}{Style.RESET_ALL}")

    return "OPEN"


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
    data=None,
    last_setup_time=None,
    last_setup_time_ref=None
):

    # The main loop must receive consumed setup timestamps even when a setup
    # becomes INVALID/EXPIRED inside Strategy. A normal parameter assignment is
    # local to this function and was previously lost between 0.5-second polls.
    if last_setup_time_ref is None:
        last_setup_time_ref = [last_setup_time]

    sl = 0
    tp = 0
    trade_setup = None

    # A setup belongs to the candle on which it is detected. Once that
    # setup has produced a trade, the same candle must never be allowed
    # to create/consume the same pattern again. This is especially
    # important when TP/SL is hit intrabar and the position is already
    # closed before the next 0.5-second polling cycle.
    current_candle_time = data.index[-1] if data is not None and not data.empty else None

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
                symbol,
                data,
                pending_setup
            )

        else:

            result = check_pending_sell(
                symbol,
                data,
                pending_setup
            )

        if result == "INVALID":

            # Consume the setup regardless of whether a pending order was ever placed.
            # last_setup_time is the strategy's single-use/re-entry guard, not merely
            # a log de-duplication flag.
            invalid_setup_time = pending_setup.get("setup_time")
            if invalid_setup_time is not None:
                last_setup_time = invalid_setup_time
                last_setup_time_ref[0] = invalid_setup_time

            if LIMIT_ORDER and pending_setup.get("limit_order_placed", False):
                ticket = pending_setup.get("limit_order_ticket")
                if ticket is not None:
                    Meta.run(symbol, False, False, lot, magic=MAGIC, pending_action="cancel", pending_ticket=ticket)
                print(
                    f"{Fore.YELLOW}LIMIT ORDER CANCELLED -> setup invalidated"
                    f"{Style.RESET_ALL}"
                )

            pending_setup = None

        elif result == "EXPIRED":

            # The setup is single-use even if the order's final broker state
            # takes another poll to settle.
            last_setup_time = pending_setup["setup_time"]
            last_setup_time_ref[0] = last_setup_time

            if LIMIT_ORDER and pending_setup.get("limit_order_placed", False):
                ticket = pending_setup.get("limit_order_ticket")

                # A pending limit can fill while MT5 is processing a cancel
                # request. Never clear the local setup merely because cancel
                # was attempted: first reconcile the authoritative MT5 state.
                if ticket is not None:
                    cancel_result = Meta.run(
                        symbol, False, False, lot, magic=MAGIC,
                        pending_action="cancel", pending_ticket=ticket
                    )

                state = Meta.run(
                    symbol, False, False, lot, magic=MAGIC,
                    pending_action="state"
                )

                if state is None or not state.get("query_ok", False):
                    print(
                        f"{Fore.YELLOW}LIMIT ORDER EXPIRY UNCONFIRMED | "
                        f"ticket:{ticket} | MT5 state unavailable; keeping local "
                        f"setup to avoid losing a possible fill."
                        f"{Style.RESET_ALL}"
                    )
                    # Keep pending_setup. The next polling cycle will reconcile
                    # again; no replacement order can be submitted meanwhile.

                elif state.get("position") is not None:
                    print(
                        f"{Fore.GREEN}LIMIT ORDER FILLED DURING EXPIRY/CANCEL | "
                        f"ticket:{ticket} | preserving setup for position-state "
                        f"reconciliation."
                        f"{Style.RESET_ALL}"
                    )
                    # Keep pending_setup so the main loop's existing
                    # position_exists and not status handler can promote this
                    # fill to an active SP2L position.

                elif state.get("order") is not None:
                    print(
                        f"{Fore.YELLOW}LIMIT ORDER CANCEL NOT CONFIRMED | "
                        f"ticket:{ticket} | order still exists; will retry."
                        f"{Style.RESET_ALL}"
                    )
                    # Cancel may have returned Invalid request because the
                    # order changed state or the request did not settle.
                    # Do not falsely report it as cancelled.

                else:
                    print(
                        f"{Fore.YELLOW}LIMIT ORDER EXPIRED -> MT5 confirms "
                        f"no pending order and no open position."
                        f"{Style.RESET_ALL}"
                    )
                    pending_setup = None

            else:
                pending_setup = None

        elif result is not None:

            entry = result["entry"]
            sl = result["sl"]
            risk = result["risk"]

            if LIMIT_ORDER:
                new_limit_price = float(result["limit_price"])

                if pending_setup.get("limit_order_placed", False):
                    # The order is already sitting in MT5. Do not place it
                    # again. Only update its price when the configured source
                    # is PULLBACK_LOW and the reference candle has advanced.
                    if result.get("limit_price_changed", False):
                        # A BUY_LIMIT must remain below Ask and a SELL_LIMIT
                        # above Bid. If the newly calculated candle level is
                        # already on the market/inside the spread, that is a
                        # broker-price condition, not an SP2L invalidation.
                        # Keep the existing valid pending order alive and wait
                        # for the next reference candle.
                        if not _limit_order_price_is_valid(symbol, direction, new_limit_price):
                            pending_setup["limit_reference_time"] = result.get("limit_reference_time")
                            print(
                                f"{Fore.YELLOW}LIMIT ORDER NOT REPRICED | "
                                f"{direction} | new price:{round(new_limit_price, DIGITS)} "
                                f"is already on the market side; existing order retained."
                                f"{Style.RESET_ALL}"
                            )
                        else:
                            # Replace the pending order once per completed reference candle.
                            # This avoids TRADE_ACTION_MODIFY, which some MT5 servers may
                            # reject for price/freeze/stops-level reasons. We cancel the
                            # exact old ticket, verify the broker state, then place a new
                            # order only if no order/position remains for this magic.
                            old_ticket = pending_setup.get("limit_order_ticket")
                            cancel_result = None
                            if old_ticket is not None:
                                cancel_result = Meta.run(
                                    symbol, False, False, lot, magic=MAGIC,
                                    pending_action="cancel", pending_ticket=old_ticket
                                )

                            cancel_retcode = getattr(cancel_result, "retcode", None) if cancel_result is not None else None
                            cancel_ok = cancel_retcode == mt5.TRADE_RETCODE_DONE

                            # Never place a replacement until MT5 confirms the old order
                            # is gone and no position was opened during the cancel race.
                            state = Meta.run(
                                symbol, False, False, lot, magic=MAGIC,
                                pending_action="state"
                            )

                            if state is None or not state.get("query_ok", False):
                                print(
                                    f"{Fore.YELLOW}LIMIT ORDER REPLACE UNKNOWN -> "
                                    f"state preserved; no duplicate order sent"
                                    f"{Style.RESET_ALL}"
                                )
                            elif state.get("position") is not None:
                                last_setup_time = pending_setup["setup_time"]
                                last_setup_time_ref[0] = last_setup_time
                                pending_setup = None
                                print(
                                    f"{Fore.GREEN}LIMIT ORDER FILLED DURING REPLACE -> "
                                    f"replacement skipped"
                                    f"{Style.RESET_ALL}"
                                )
                            elif state.get("order") is not None:
                                # Cancellation was rejected or has not settled yet.
                                # Keep the existing ticket; retry on a later candle.
                                pending_setup["limit_order_ticket"] = int(state["order"].ticket)
                                pending_setup["limit_order_placed"] = True
                                pending_setup["limit_reference_time"] = result.get("limit_reference_time")
                                print(
                                    f"{Fore.YELLOW}LIMIT ORDER REPLACE DEFERRED | "
                                    f"old order still active; no duplicate sent"
                                    f"{Style.RESET_ALL}"
                                )
                            elif not cancel_ok:
                                # The order is absent now, but cancellation response was
                                # not confirmed. Safe to place only after the state query
                                # has established both order and position are absent.
                                print(
                                    f"{Fore.YELLOW}LIMIT ORDER CANCEL RESPONSE UNCLEAR | "
                                    f"broker state is empty; replacement may proceed"
                                    f"{Style.RESET_ALL}"
                                )
                                pending_setup["limit_order_placed"] = False
                            else:
                                pending_setup["limit_order_placed"] = False

                            if pending_setup is not None and not pending_setup.get("limit_order_placed", False):
                                replacement_tp = (
                                    new_limit_price + TP_R * risk
                                    if direction == "BUY"
                                    else new_limit_price - TP_R * risk
                                )
                                replacement_result = Meta.run(
                                    symbol,
                                    direction == "BUY",
                                    direction == "SELL",
                                    lot,
                                    replacement_tp,
                                    sl,
                                    MAGIC,
                                    stopLossPure=True,
                                    pending_action="place",
                                    pending_price=new_limit_price,
                                    pending_sl=sl,
                                    pending_tp=replacement_tp,
                                    pending_comment="SP2L Limit Entry"
                                )
                                replacement_retcode = getattr(replacement_result, "retcode", None) if replacement_result is not None else None
                                replacement_is_order = (
                                    replacement_result is not None
                                    and hasattr(replacement_result, "ticket")
                                    and int(getattr(replacement_result, "magic", -1)) == int(MAGIC)
                                )
                                if replacement_result is not None and (
                                    replacement_retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED)
                                    or replacement_is_order
                                ):
                                    new_ticket = (
                                        int(replacement_result.order)
                                        if hasattr(replacement_result, "order")
                                        else int(replacement_result.ticket)
                                    )
                                    pending_setup["limit_order_placed"] = True
                                    pending_setup["limit_order_ticket"] = new_ticket
                                    pending_setup["limit_price"] = new_limit_price
                                    pending_setup["limit_reference_time"] = result.get("limit_reference_time")
                                    print(
                                        f"{Fore.CYAN}LIMIT ORDER REPLACED | {direction} | "
                                        f"old ticket:{old_ticket} | new price:{round(new_limit_price, DIGITS)} | "
                                        f"new ticket:{new_ticket} | SL:{round(sl, DIGITS)} | "
                                        f"TP:{round(replacement_tp, DIGITS)}"
                                        f"{Style.RESET_ALL}"
                                    )
                                else:
                                    # No active order exists. Leave the setup eligible
                                    # for a controlled retry through the normal place path.
                                    pending_setup["limit_order_placed"] = False
                                    pending_setup["limit_order_ticket"] = None
                                    pending_setup["limit_price"] = new_limit_price
                                    pending_setup["limit_reference_time"] = result.get("limit_reference_time")
                                    print(
                                        f"{Fore.RED}LIMIT ORDER REPLACEMENT FAILED | "
                                        f"old order is gone; next loop may retry placement"
                                        f"{Style.RESET_ALL}"
                                    )

                    # No market trade is created while a limit order remains pending.
                    return (
                        preBuy,
                        preSell,
                        status,
                        sl,
                        tp,
                        pending_setup,
                        None
                    )

                # First pass: prepare the initial limit order. The main loop
                # submits it through Meta.run, the central Meta execution path.
                pending_setup["limit_price"] = new_limit_price
                limit_tp = (
                    new_limit_price + TP_R * risk
                    if direction == "BUY"
                    else new_limit_price - TP_R * risk
                )
                return (
                    preBuy,
                    preSell,
                    status,
                    sl,
                    limit_tp,
                    pending_setup,
                    {
                        "direction": direction,
                        "entry": new_limit_price,
                        "limit_price": new_limit_price,
                        "sl": sl,
                        "tp": limit_tp,
                        "risk": risk,
                        "setup_time": result["setup_time"],
                        "entry_time": result["entry_time"],
                        "spike_body": result["spike_body"],
                        "limit_order": True,
                        "limit_price_changed": False,
                        "second_entry": get_second_entry(direction, new_limit_price, risk)
                    }
                )

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
    # IMPORTANT: keep an existing pending setup alive.
    #
    # Strategy is called every 0.5 second because the current candle is
    # updated intrabar. Once a setup has been created, however, we must
    # NOT run detect_buy_setup()/detect_sell_setup() again while that
    # same pending setup is still alive. Otherwise the exact same pattern
    # is recreated and "pending setup detected" is printed every loop.
    #
    # If the setup was invalidated/expired above, pending_setup is None
    # and the normal new-setup detection below is allowed to run.
    # ========================================================
    if pending_setup is not None:
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
    #
    # IMPORTANT:
    # Do not reuse a setup that has already generated a trade on
    # this same candle. Without this guard, a trade that opens and
    # closes intrabar (for example by TP) can leave status=False,
    # after which the exact same still-forming pattern is detected
    # again on the next 0.5-second loop.
    # ========================================================

    effective_last_setup_time = last_setup_time_ref[0]
    if (
        effective_last_setup_time is not None
        and current_candle_time is not None
        and current_candle_time == effective_last_setup_time
    ):
        return (
            preBuy,
            preSell,
            status,
            sl,
            tp,
            pending_setup,
            trade_setup
        )

    buy = detect_buy_setup(data)
    sell = detect_sell_setup(data)

    # Direction filter is applied after the existing SP2L setup detectors,
    # so no BUY/SELL detection logic itself is altered.
    if TRADE_DIRECTION == "BUY":
        sell = False
    elif TRADE_DIRECTION == "SELL":
        buy = False

    if buy and not sell:

        pending_setup = create_pending_buy(
            data
        )

        if pending_setup is not None:
            print(
                f"\n{Fore.CYAN}"
                f"BUY pending setup detected"
                f"{Style.RESET_ALL}"
            )

    elif sell and not buy:

        pending_setup = create_pending_sell(
            data
        )

        if pending_setup is not None:
            print(
                f"\n{Fore.CYAN}"
                f"SELL pending setup detected"
                f"{Style.RESET_ALL}"
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
# NEWS FILTER
# ============================================================

def read_news_status(status_file, previous_state=None):
    """Read news_status.json safely and validate freshness."""
    if previous_state is None:
        previous_state = {"high_impact": False, "event_id": None, "event": "", "currency": "", "event_time_broker": "", "block_start": "", "block_end": "", "updated_at": "", "source": "", "error": ""}
    try:
        stat = os.stat(status_file)
        mtime_ns = stat.st_mtime_ns
        age_seconds = max(0.0, time_module.time() - stat.st_mtime)
    except FileNotFoundError:
        state=dict(previous_state); state["error"]="file_not_found"; state["_available"]=False; return state,False,False
    except BaseException as e:
        state=dict(previous_state); state["error"]=f"stat_error:{e}"; state["_available"]=False; return state,False,False
    if previous_state.get("_mtime_ns") == mtime_ns:
        # The monitor normally refreshes on a 60-minute cadence. During the
        # refresh there can be a few seconds where the old JSON is just over
        # the nominal age limit. Keep the feed available during this short
        # hand-off instead of generating a false outage message.
        effective_max_age = (
            NEWS_STATUS_MAX_AGE_SECONDS
            + NEWS_STATUS_REFRESH_GRACE_SECONDS
        )
        if age_seconds <= effective_max_age:
            previous_state["_available"] = True
            previous_state["_age_seconds"] = int(age_seconds)
            previous_state["error"] = ""
            return previous_state, False, True
        state = dict(previous_state)
        state["error"] = f"stale_{int(age_seconds)}s"
        state["_available"] = False
        state["_age_seconds"] = int(age_seconds)
        return state, False, False
    try:
        with open(status_file,"r",encoding="utf-8") as f: state=json.load(f)
        if not isinstance(state,dict): raise ValueError("news status JSON is not an object")
        if "high_impact" not in state: raise ValueError("missing required field: high_impact")
        if not isinstance(state.get("high_impact"),bool): raise ValueError("high_impact must be boolean")
        if "updated_at" not in state or not str(state.get("updated_at") or "").strip(): raise ValueError("updated_at is missing or empty")
        merged=dict(previous_state); merged.update(state); merged["_mtime_ns"]=mtime_ns; merged["_age_seconds"]=int(age_seconds)
        if age_seconds > NEWS_STATUS_MAX_AGE_SECONDS:
            merged["error"]=f"stale_{int(age_seconds)}s"; merged["_available"]=False; return merged,True,False
        merged["error"]=""; merged["_available"]=True; return merged,True,True
    except BaseException as e:
        state=dict(previous_state); state["error"]=f"invalid_status:{e}"; state["_available"]=False; return state,False,False


def _news_close_position(position):
    """Close one MT5 position at the current executable market price."""
    symbol = position.symbol
    tick = mt5.symbol_info_tick(symbol)

    if tick is None:
        print(
            f"NEWS FILTER: no tick available while closing position {position.ticket}."
        )
        return False

    if int(position.type) == int(mt5.POSITION_TYPE_BUY):
        close_type = mt5.ORDER_TYPE_SELL
        close_price = float(tick.bid)
    else:
        close_type = mt5.ORDER_TYPE_BUY
        close_price = float(tick.ask)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(position.volume),
        "type": close_type,
        "position": int(position.ticket),
        "price": close_price,
        "deviation": 20,
        "comment": "SP2L NEWS FILTER CLOSE"
    }

    result = mt5.order_send(request)

    if result is None:
        print(
            f"NEWS FILTER: close failed for position {position.ticket}: "
            f"order_send returned None; error={mt5.last_error()}"
        )
        return False

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(
            f"NEWS FILTER: close failed for position {position.ticket}: "
            f"retcode={result.retcode}, comment={result.comment}"
        )
        return False

    print(
        f"NEWS FILTER: position closed -> ticket={position.ticket}, "
        f"magic={position.magic}, volume={position.volume}, "
        f"price={close_price}"
    )
    return True


def _news_cancel_pending_order(order):
    """Cancel one pending MT5 order when news protection becomes active."""
    try:
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": int(order.ticket),
            "symbol": order.symbol
        }
        result = mt5.order_send(request)

        if result is None:
            print(
                f"NEWS FILTER: pending order cancel failed -> "
                f"ticket={order.ticket}; error={mt5.last_error()}"
            )
            return False

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(
                f"NEWS FILTER: pending order cancel failed -> "
                f"ticket={order.ticket}; retcode={result.retcode}; "
                f"comment={result.comment}"
            )
            return False

        print(
            f"NEWS FILTER: pending order cancelled -> "
            f"ticket={order.ticket}, magic={order.magic}"
        )
        return True

    except BaseException as e:
        print(
            f"NEWS FILTER: exception cancelling pending order "
            f"{getattr(order, 'ticket', '?')}: {str(e)}"
        )
        return False


def _news_log_time():
    """Return local SP2L log time with second precision."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def handle_news_activation(symbol, news_state):
    """Close/cancel SP2L exposure when a new high-impact block activates."""
    if not USE_NEWS_FILTER:
        return

    event = news_state.get("event") or "High-impact news"
    currency = news_state.get("currency") or ""
    event_time = news_state.get("event_time_broker") or ""
    block_start = news_state.get("block_start") or ""
    block_end = news_state.get("block_end") or ""

    now_text = _news_log_time()

    print()
    print(
        f"{Fore.RED}NEWS FILTER | {now_text} | HIGH IMPACT DETECTED"
        f"{Style.RESET_ALL}"
    )
    # The local news JSON may contain only high_impact=True (for example
    # during a manual test) without an active event payload. Do not print
    # empty/missing event fields as if they were available.
    if event:
        print("Event       :", event)
    if currency:
        print("Currency    :", currency)
    if event_time:
        print("News time   :", event_time)
    if block_start or block_end:
        print("Block       :", f"{block_start} -> {block_end}")
    print("Symbol      :", symbol)

    if BLOCK_NEW_ENTRIES_ON_NEWS:
        print(
            f"{Fore.RED}NEWS FILTER | {now_text} | "
            f"NEW ENTRIES BLOCKED{Style.RESET_ALL}"
        )

    if CLOSE_ON_HIGH_IMPACT_NEWS:
        try:
            positions = mt5.positions_get(symbol=symbol)
        except BaseException as e:
            positions = None
            print(
                f"{Fore.RED}NEWS FILTER | {_news_log_time()} | "
                f"positions_get failed: {str(e)}{Style.RESET_ALL}"
            )

        if positions:
            matching_count = 0
            closed_count = 0
            for position in positions:
                own_position = (
                    int(position.magic) in
                    [int(x) for x in NEWS_CLOSE_MAGICS]
                )
                if CLOSE_ALL_POSITIONS_ON_NEWS or own_position:
                    matching_count += 1
                    if _news_close_position(position):
                        closed_count += 1

            print(
                f"{Fore.RED}NEWS FILTER | {_news_log_time()} | "
                f"positions close result: {closed_count}/{matching_count}"
                f"{Style.RESET_ALL}"
            )
        else:
            print(
                f"{Fore.RED}NEWS FILTER | {_news_log_time()} | "
                f"no matching open positions to close.{Style.RESET_ALL}"
            )
    else:
        print(
            f"{Fore.YELLOW}NEWS FILTER | {_news_log_time()} | "
            f"position closing disabled by setting.{Style.RESET_ALL}"
        )

    # Also remove pending orders belonging to SP2L. This prevents a pending
    # second-entry order from becoming a position during the news window.
    try:
        orders = mt5.orders_get(symbol=symbol)
    except BaseException as e:
        orders = None
        print(
            f"{Fore.RED}NEWS FILTER | {_news_log_time()} | "
            f"orders_get failed: {str(e)}{Style.RESET_ALL}"
        )

    if orders:
        matching_orders = 0
        cancelled_orders = 0
        for order in orders:
            own_order = (
                int(order.magic) in
                [int(x) for x in NEWS_CLOSE_MAGICS]
            )
            if CLOSE_ALL_POSITIONS_ON_NEWS or own_order:
                matching_orders += 1
                if _news_cancel_pending_order(order):
                    cancelled_orders += 1

        if matching_orders:
            print(
                f"{Fore.RED}NEWS FILTER | {_news_log_time()} | "
                f"pending orders cancelled: {cancelled_orders}/{matching_orders}"
                f"{Style.RESET_ALL}"
            )

def log_spike_blocked_by_news(data, news_state, last_logged_key):
    """Log a detected spike without creating a trade while news is active."""
    if data is None or len(data) < 5:
        return last_logged_key

    buy = bool(detect_buy_setup(data))
    sell = bool(detect_sell_setup(data))
    candle_key = str(data.index[-1])

    if buy and not sell:
        key = (candle_key, "BUY", news_state.get("event_id"))
        if key != last_logged_key:
            print()
            print(
                f"{Fore.YELLOW}NEWS FILTER | {_news_log_time()} | "
                f"BUY SPIKE DETECTED -> ENTRY BLOCKED BY HIGH-IMPACT NEWS"
                f"{Style.RESET_ALL}"
            )
            event_text = news_state.get("event") or "High-impact news"
            currency_text = news_state.get("currency") or ""
            event_time_text = news_state.get("event_time_broker") or ""
            print("News event :", event_text)
            if currency_text:
                print("Currency   :", currency_text)
            if event_time_text:
                print("News time  :", event_time_text)
            print("Candle     :", candle_key)
            last_logged_key = key

    elif sell and not buy:
        key = (candle_key, "SELL", news_state.get("event_id"))
        if key != last_logged_key:
            print()
            print(
                f"{Fore.YELLOW}NEWS FILTER | {_news_log_time()} | "
                f"SELL SPIKE DETECTED -> ENTRY BLOCKED BY HIGH-IMPACT NEWS"
                f"{Style.RESET_ALL}"
            )
            print("News event :", news_state.get("event", "High-impact news"))
            print("Currency   :", news_state.get("currency", ""))
            print("News time  :", news_state.get("event_time_broker", ""))
            print("Candle     :", candle_key)
            last_logged_key = key

    return last_logged_key


# ============================================================
# ACCOUNT INFORMATION
# ============================================================

accountInfo = mt5.account_info()

print("-" * 75)

if accountInfo is not None:

    print(
        f"Login: {accountInfo.login}"
        f"\tserver: {accountInfo.server}"
        f"\tleverage: {accountInfo.leverage}"
    )

    print(
        f"Balance: {accountInfo.balance}"
        f"\tEquity: {accountInfo.equity}"
        f"\tProfit: {accountInfo.profit}"
    )

print(
    "Run time:",
    datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)

print("-" * 75)


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

# Candle timestamp of the last setup that actually produced Entry 1.
# A setup is single-use: it cannot be reused while that candle is still forming,
# even if the resulting position is opened and closed intrabar by TP/SL.
last_setup_time = None

# Tickets that have successfully received each duration-management stage.
# Explicit ticket sets prevent repeated modifications during 0.5-second polling.
duration_stage1_tickets = set()
duration_stage2_tickets = set()
# Original TP/SL levels captured once per open position, used as the reference
# for non-compounding duration-management adjustments.
duration_initial_prices = {}
# First candle observed while this position is active. Duration stages cannot run before this baseline.
duration_tracking_start_candles = {}

# Used to prevent processing the same live candle repeatedly.
last_processed_candle = None

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

# News state is intentionally local and cheap to read. The monitor performs
# all network activity; SP2L only consumes its atomic JSON result.
news_state = {
    "high_impact": False,
    "event_id": None,
    "event": "",
    "currency": "",
    "event_time_broker": "",
    "block_start": "",
    "block_end": "",
    "updated_at": "",
    "source": "",
    "error": ""
}
last_news_event_id = None
last_news_active = False
last_news_spike_log_key = None
last_news_status_available = None
last_news_unavailable_log_time = None
# Local news JSON is inspected at most once per minute.
last_news_file_check_time = 0.0

# Entry-filter logging is de-duplicated so the 0.5-second loop does not
# print the same block message continuously.
last_entry_filter_log_reason = None
last_entry_filter_log_candle = None

while True:

    loop_start_time = time_module.perf_counter()

    if internet() is True:

        for asset in symbols_list.keys():

            symbol = symbols_list[asset][0]
            lot = symbols_list[asset][1]

            # =================================================
            # NEWS STATUS
            # =================================================
            news_changed = False
            now_wall_time = time_module.time()
            if (
                USE_NEWS_FILTER
                and NEWS_CHECK_EVERY_LOOP
                and (
                    last_news_file_check_time == 0.0
                    or now_wall_time - last_news_file_check_time >= NEWS_FILE_CHECK_INTERVAL_SECONDS
                )
            ):
                news_state, news_changed, _news_available = read_news_status(
                    NEWS_STATUS_FILE,
                    news_state
                )
                last_news_file_check_time = now_wall_time

            news_available = (
                USE_NEWS_FILTER
                and bool(news_state.get("_available", False))
            )

            if USE_NEWS_FILTER:
                now_log = time_module.time()
                if not news_available:
                    reason = str(news_state.get("error", "unavailable"))
                    should_log = (
                        last_news_status_available is not False
                        or last_news_unavailable_log_time is None
                        or now_log - last_news_unavailable_log_time >= NEWS_UNAVAILABLE_LOG_INTERVAL_SECONDS
                    )
                    if should_log:
                        print(
                            f"{Fore.RED}NEWS FILTER | "
                            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                            f"status unavailable ({reason}) -> trading continues."
                            f"{Style.RESET_ALL}"
                        )
                        last_news_unavailable_log_time = now_log
                elif last_news_status_available is not True:
                    print(
                        f"{Fore.GREEN}NEWS FILTER | "
                        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"news feed connected; receiving news status."
                        f"{Style.RESET_ALL}"
                    )
                last_news_status_available = news_available

            news_high_impact = (
                news_available
                and bool(news_state.get("high_impact", False))
            )

            news_active = (
                news_high_impact
                and BLOCK_NEW_ENTRIES_ON_NEWS
            )

            if news_high_impact and (not last_news_active or news_changed):
                # Some news feeds omit event_id. Use a stable fallback key so
                # the activation handler still runs once for that event.
                current_event_id = news_state.get("event_id")
                if current_event_id in (None, ""):
                    current_event_id = (
                        news_state.get("event"),
                        news_state.get("currency"),
                        news_state.get("event_time_broker"),
                        news_state.get("block_start"),
                        news_state.get("block_end"),
                    )

                if current_event_id != last_news_event_id:
                    handle_news_activation(symbol, news_state)
                    last_news_event_id = current_event_id

                # A setup that existed before the news must not survive the
                # news window. It will have to be detected again afterwards.
                # IMPORTANT: do not reset `status` here. It represents the
                # live position state; resetting it before MT5 confirms the
                # position is closed suppresses close detection and can leave
                # an open position looking "abnormal" to the strategy.
                pending_setup = None
                second_setup = None
                second_pullback_touched = False
                second_order_placed = False
                buy = False
                sell = False

            if (
                news_available
                and not news_active
                and last_news_active
            ):
                print()
                print(
                    f"{Fore.GREEN}NEWS FILTER | {_news_log_time()} | "
                    f"HIGH-IMPACT WINDOW ENDED -> NEW ENTRIES ENABLED"
                    f"{Style.RESET_ALL}"
                )
                print("Event :", news_state.get("event", ""))
                print("Until :", news_state.get("block_end", ""))

            last_news_active = news_active

            selected = mt5.symbol_select(
                symbol
            )

            if not selected:

                print(
                    f"\nERROR - Failed to select "
                    f"'{symbol}' in MetaTrader 5 "
                    f"with error :",
                    mt5.last_error()
                )

                continue

            # =================================================
            # CHECK EXISTING POSITION
            # =================================================

            position_exists, row = get_trade_state(
                symbol
            )

            # A failed MT5 position query is UNKNOWN, not a closed position.
            # Skip this cycle so no close message, duplicate entry, or abnormal
            # position handling can be triggered by a transient API failure.
            if position_exists is None:
                elapsed = time_module.perf_counter() - loop_start_time
                remaining = LOOP_SECONDS - elapsed
                if remaining > 0:
                    time_module.sleep(remaining)
                continue

            # -------------------------------------------------
            # Trade duration management
            # -------------------------------------------------
            # This runs on the live Entry-1 position before the normal close/fill
            # state handling. It never opens a trade and never changes setup
            # lifecycle state. The actual SL/TP/close requests are routed through
            # Meta.run so the central execution path remains the single order gateway.
            if position_exists and status and USE_TRADE_DURATION_MANAGEMENT:
                duration_result = manage_trade_duration(
                    symbol, row, lot, magic=MAGIC,
                    current_candle_time=current_candle_time
                )
                if duration_result == "CLOSED":
                    # Do not immediately manufacture a closed state. The next
                    # poll will confirm MT5 no longer has the position and the
                    # existing Strategy Position closed handler will run normally.
                    pass
                elif duration_result is None:
                    # A failed management request is retried on the next poll.
                    pass

            # -------------------------------------------------
            # Stop loss / position closed
            # -------------------------------------------------

            if not position_exists and status:

                # Clear per-ticket duration state only after MT5 confirms the
                # position is gone, so a later trade starts with a fresh baseline.
                duration_stage1_tickets.clear()
                duration_stage2_tickets.clear()
                duration_initial_prices.clear()
                duration_tracking_start_candles.clear()

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

                print(
                    f"Strategy "
                    f"{Fore.YELLOW}"
                    f"Position closed / SL or TP hit!"
                    f"{Style.RESET_ALL}"
                )

            # -------------------------------------------------
            # Abnormal open position
            # -------------------------------------------------

            elif position_exists and not status:

                # A limit order is allowed to remain pending. Once MT5 fills
                # it, the pending order disappears and a real position exists.
                # Promote that fill to the normal SP2L position state instead
                # of treating it as an abnormal/manual position.
                if (
                    LIMIT_ORDER
                    and pending_setup is not None
                    and pending_setup.get("limit_order_placed", False)
                ):
                    # The pending order has filled. Reconcile its TP using the
                    # actual MT5 fill price before constructing second-entry data.
                    Meta.run(
                        symbol, False, False, lot, magic=MAGIC,
                        pending_action="get"
                    )
                    # Refresh the row because UpdateTPAfterFill may have changed TP.
                    _filled_exists, _filled_row = get_trade_state(symbol)
                    if _filled_exists is None:
                        # Do not guess while MT5 is temporarily unable to
                        # provide the newly-filled position snapshot.
                        elapsed = time_module.perf_counter() - loop_start_time
                        remaining = LOOP_SECONDS - elapsed
                        if remaining > 0:
                            time_module.sleep(remaining)
                        continue

                    if not _filled_exists or _filled_row is None:
                        # The pending order may have filled and closed extremely
                        # quickly. Do not manufacture an active position.
                        pending_setup = None
                        continue

                    row = _filled_row

                    status = True
                    buy = int(row.iloc[0]["position"]) == 0
                    sell = int(row.iloc[0]["position"]) == 1
                    pending_setup = None

                    if USE_SECOND_ENTRY:
                        filled_price = float(row.iloc[0]["price"])
                        filled_sl = float(row.iloc[0]["sl"])
                        filled_tp = float(row.iloc[0]["tp"])
                        filled_risk = (
                            filled_price - filled_sl
                            if buy
                            else filled_sl - filled_price
                        )

                        if filled_risk > 0:
                            second_setup = {
                                "direction": "BUY" if buy else "SELL",
                                "entry": get_second_entry(
                                    "BUY" if buy else "SELL",
                                    filled_price,
                                    filled_risk
                                ),
                                "sl": filled_sl,
                                "tp": filled_tp,
                                "setup_time": last_setup_time,
                                "entry_time": data.index[-1]
                            }
                            second_pullback_touched = False
                            second_order_placed = False

                    print(
                        f"{Fore.GREEN if buy else Fore.RED}"
                        f"LIMIT ORDER FILLED -> {"BUY" if buy else "SELL"} POSITION ACTIVE"
                        f"{Style.RESET_ALL}"
                    )
                else:
                    print(
                        "Abnormally position: "
                        "you have an open position "
                        "with OPTIMIZED SP2L TRADER VER10.0 "
                        "but the status key is False!!"
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
            # TIME / DAY ENTRY BLOCK
            # =================================================
            # Use the raw candle timestamp from MT5. The user explicitly
            # wants broker/chart time, so no timezone conversion is applied.
            entry_block_reason = get_entry_block_reason(current_candle_time)

            # =================================================
            # NEWS BLOCK
            # =================================================
            # Keep spike detection visible in the log, but do not allow the
            # strategy state machine to create/execute an entry while a
            # high-impact news block is active.
            if news_active:
                last_news_spike_log_key = log_spike_blocked_by_news(
                    data,
                    news_state,
                    last_news_spike_log_key
                )

                # No stale setup may survive the news window. Preserve
                # `status` until get_trade_state() confirms that MT5 no longer
                # has the position. This allows the normal SL/TP close handler
                # to run even if the position closes during the news window.
                pending_setup = None
                trade_setup = None
                second_setup = None
                second_pullback_touched = False
                second_order_placed = False
                buy = False
                sell = False

                elapsed = time_module.perf_counter() - loop_start_time
                remaining = LOOP_SECONDS - elapsed
                if remaining > 0:
                    time_module.sleep(remaining)
                continue

            # A cancelled/expired Entry-1 limit order must also remove any
            # local second-entry state that may have been created for it.
            if LIMIT_ORDER and pending_setup is None and not status:
                second_setup = None
                second_pullback_touched = False
                second_order_placed = False

            # =================================================
            # TIME / DAY BLOCK -> NO NEW ENTRIES
            # =================================================
            # Existing positions are never force-closed by this filter.
            # An Entry-1 LIMIT order, however, is a live future entry, so it
            # must be cancelled when the no-trade window/day becomes active.
            # The originating setup is consumed via last_setup_time so it
            # cannot reappear repeatedly during the blocked period.
            if entry_block_reason is not None:
                if pending_setup is not None:
                    if (
                        LIMIT_ORDER
                        and pending_setup.get("limit_order_placed", False)
                    ):
                        ticket = pending_setup.get("limit_order_ticket")
                        if ticket is not None:
                            Meta.run(
                                symbol, False, False, lot, magic=MAGIC,
                                pending_action="cancel", pending_ticket=ticket
                            )
                            print(
                                f"{Fore.YELLOW}LIMIT ORDER CANCELLED -> "
                                f"entry filter active ({entry_block_reason})"
                                f"{Style.RESET_ALL}"
                            )

                    setup_time = pending_setup.get("setup_time")
                    if setup_time is not None:
                        last_setup_time = setup_time
                    pending_setup = None

                # A setup that would otherwise be detected on this candle
                # is consumed for this candle only. When the next candle
                # arrives, normal detection resumes if the filter allows it.
                if current_candle_time is not None and not status:
                    last_setup_time = current_candle_time

                # The second entry is a new trade, so it is also blocked.
                # Do not alter an already-open second position.
                second_setup = None
                second_pullback_touched = False

                if (
                    last_entry_filter_log_reason != entry_block_reason
                    or last_entry_filter_log_candle != current_candle_time
                ):
                    print(
                        f"{Fore.YELLOW}ENTRY FILTER ACTIVE | "
                        f"{entry_block_reason} -> new entries blocked"
                        f"{Style.RESET_ALL}"
                    )
                    last_entry_filter_log_reason = entry_block_reason
                    last_entry_filter_log_candle = current_candle_time

                elapsed = time_module.perf_counter() - loop_start_time
                remaining = LOOP_SECONDS - elapsed
                if remaining > 0:
                    time_module.sleep(remaining)
                continue

            # =================================================
            # STRATEGY
            #
            # Strategy receives cached data. Therefore it no longer
            # downloads/rebuilds NUMBER_OF_DATA every 0.5 second.
            # Pending entry and current-candle setup detection remain
            # active every 0.5 second.
            # =================================================

            last_setup_time_ref = [last_setup_time]
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
                data=data,
                last_setup_time=last_setup_time,
                last_setup_time_ref=last_setup_time_ref
            )
            last_setup_time = last_setup_time_ref[0]

            # =================================================
            # EXECUTE ENTRY 1
            # =================================================

            if trade_setup is not None:

                direction = trade_setup["direction"]

                entry = trade_setup["entry"]
                sl = trade_setup["sl"]
                tp = trade_setup["tp"]

                print()
                print("-" * 75)
                print(
                    f"{Fore.GREEN if direction == 'BUY' else Fore.RED}"
                    f"VALID {direction} ENTRY"
                    f"{Style.RESET_ALL}"
                )

                print(
                    "Setup time :",
                    trade_setup["setup_time"]
                )

                print(
                    "Entry time :",
                    trade_setup["entry_time"]
                )

                print(
                    "Entry      :",
                    round(entry, DIGITS)
                )

                print(
                    "SL         :",
                    round(sl, DIGITS)
                )

                print(
                    "TP         :",
                    round(tp, DIGITS)
                )

                print(
                    "Risk       :",
                    round(
                        trade_setup["risk"],
                        DIGITS
                    )
                )

                print(
                    "Second     :",
                    round(
                        trade_setup["second_entry"],
                        DIGITS
                    )
                )

                print("-" * 75)

                if trade_setup.get("limit_order_update", False):
                    # The pending order already exists. Strategy has modified
                    # its price; keep the local second-entry calculations in
                    # sync with the new risk/TP, but do not place another order.
                    if USE_SECOND_ENTRY:
                        second_setup = None
                    trade_setup = None

                elif trade_setup.get("limit_order", False):
                    # Pending orders use the exact requested limit price. TP
                    # is derived from that price and the fixed SL, so it does
                    # not depend on a later market quote.
                    limit_price = float(trade_setup["limit_price"])
                    # Pending orders carry a safe initial TP; when filled, Meta.run
                    # reconciles TP against the actual MT5 position fill price.
                    Meta.SetExecutionBasedTP(
                        enabled=True, tp_r=TP_R, signal_entry=limit_price
                    )

                    if not _limit_order_price_is_valid(symbol, direction, limit_price):
                        if pending_setup is None or not pending_setup.get("limit_price_wait_logged", False):
                            print(
                                f"{Fore.YELLOW}LIMIT ORDER WAITING | {direction} | "
                                f"price:{round(limit_price, DIGITS)} moved to the wrong side of market; "
                                f"setup retained for retry.{Style.RESET_ALL}"
                            )
                        # The quote may have crossed between Strategy's pre-check
                        # and this final execution check. Keep the setup alive so
                        # the next poll can retry; do not consume the setup here.
                        if pending_setup is not None:
                            pending_setup["limit_price_wait_logged"] = True
                        trade_setup = None
                        # Skip this submission only; pending_setup remains active.
                        # The loop's normal cadence performs the next retry.
                        continue

                    result = Meta.run(
                        symbol,
                        direction == "BUY",
                        direction == "SELL",
                        lot,
                        tp,
                        sl,
                        MAGIC,
                        stopLossPure=True,
                        pending_action="place",
                        pending_price=limit_price,
                        pending_sl=sl,
                        pending_tp=tp,
                        pending_comment="SP2L Limit Entry"
                    )

                    result_retcode = getattr(result, "retcode", None) if result is not None else None
                    result_is_existing_order = (
                        result is not None
                        and hasattr(result, "ticket")
                        and int(getattr(result, "magic", -1)) == int(MAGIC)
                    )
                    if result is not None and (
                        result_retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED)
                        or result_is_existing_order
                    ):
                        pending_setup["limit_order_placed"] = True
                        pending_setup["limit_order_ticket"] = int(result.order) if hasattr(result, "order") else (int(result.ticket) if hasattr(result, "ticket") else None)
                        pending_setup["limit_price"] = limit_price
                        if LIMIT_ORDER_PRICE_SOURCE == "PULLBACK_LOW":
                            pending_setup["limit_reference_time"] = data.index[-2]
                        else:
                            pending_setup["limit_reference_time"] = pending_setup["setup_time"]
                        print(
                            f"{Fore.CYAN}LIMIT ORDER PLACED | "
                            f"{direction} | price:{round(limit_price, DIGITS)} | "
                            f"SL:{round(sl, DIGITS)} | TP:{round(tp, DIGITS)} | "
                            f"ticket:{pending_setup["limit_order_ticket"]}"
                            f"{Style.RESET_ALL}"
                        )
                    else:
                        print(
                            f"{Fore.RED}LIMIT ORDER FAILED -> setup invalidated"
                            f"{Style.RESET_ALL}"
                        )
                        pending_setup = None

                    # The pattern is consumed when the first limit order is
                    # placed, even though no position exists yet.
                    last_setup_time = trade_setup["setup_time"]

                else:
                    # TP is calculated by Meta at the actual executable
                    # Ask/Bid using the fixed SL and TP_R.
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

                    # Mark the originating setup candle as consumed immediately.
                    last_setup_time = trade_setup["setup_time"]

                # =================================================
                # SECOND ENTRY SETUP
                # =================================================

                if USE_SECOND_ENTRY and not trade_setup.get("limit_order", False):

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

                    print(
                        f"{Fore.MAGENTA}"
                        f"Second entry is ENABLED."
                        f"{Style.RESET_ALL}"
                    )

                    print(
                        "Second entry price:",
                        round(
                            second_setup["entry"],
                            DIGITS
                        )
                    )

                    print(
                        "Second entry volume:",
                        lot
                        *
                        SECOND_ENTRY_VOLUME_MULTIPLIER
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

                    print(
                        f"{Fore.MAGENTA}"
                        f"Second entry position is ACTIVE "
                        f"(magic:{SECOND_ENTRY_MAGIC})"
                        f"{Style.RESET_ALL}"
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

                    print(
                        f"Second entry "
                        f"{Fore.YELLOW}"
                        f"position closed / "
                        f"SL or TP hit "
                        f"(magic:{SECOND_ENTRY_MAGIC})"
                        f"{Style.RESET_ALL}"
                    )

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

                            print()
                            print("-" * 75)
                            print(
                                f"{Fore.MAGENTA}"
                                f"SECOND ENTRY TRIGGERED"
                                f"{Style.RESET_ALL}"
                            )
                            print(
                                "Second entry signal :",
                                round(second_entry, DIGITS)
                            )
                            print(
                                "Trigger Ask/Bid     :",
                                round(trigger_price, DIGITS)
                            )
                            print(
                                "Second entry SL     :",
                                round(second_sl, DIGITS)
                            )
                            print(
                                "First trade TP      :",
                                round(second_tp, DIGITS)
                            )
                            print(
                                "Second entry volume :",
                                second_volume
                            )
                            print(
                                "Magic               :",
                                SECOND_ENTRY_MAGIC
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
                                print(
                                    f"{Fore.RED}"
                                    f"SECOND ENTRY NOT CONFIRMED "
                                    f"(magic:{SECOND_ENTRY_MAGIC})"
                                    f"{Style.RESET_ALL}"
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
