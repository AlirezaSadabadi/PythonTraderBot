#!/usr/bin/env python
__author__ = "Alireza Sadabadi"
__copyright__ = "Copyright (c) 2026 Alireza Sadabadi. All rights reserved."
__credits__ = ["Alireza Sadabadi"]
__license__ = "Apache"
__version__ = "7.1"
__maintainer__ = "Alireza Sadabadi"
__email__ = "alirezasadabady@gmail.com"
__status__ = "Test"
__doc__ = "you can see the tutorials in https://youtube.com/@alirezasadabadi?si=d8o7LK_Ai1Hf68is"

import MetaTrader5 as mt5
from datetime import datetime, timezone, time
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

PGAP_POINTS = 100
MAX_SL_DISTANCE_POINTS = 1000

# Use market-structure pivots for Stop Loss:
# BUY -> search backward for the first LowerLow before the spike.
# SELL -> search backward for the first HigherHigh before the spike.
# If False, use the original candle immediately before the spike.
USE_LOWERLOW_HIGHERHIGH_SL = False

TP_R = 0.9

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

print("-" * 75)
print("OPTIMIZED SP2L TRADER VER7.0")
print("-" * 75)
print("Symbol              :", SYMBOL)
print("Point               :", BROKER_POINT)
print("Digits              :", DIGITS)
print("Spike multiplier    :", SPIKE_CANDLE_SIZE)
print("Gap points          :", PGAP_POINTS)
print("Max SL points       :", MAX_SL_DISTANCE_POINTS)
print("LowerLow/HH SL      :", USE_LOWERLOW_HIGHERHIGH_SL)
print("TP                  :", f"{TP_R}R")
print("Second entry        :", USE_SECOND_ENTRY)
print("Second entry volume :", SECOND_ENTRY_VOLUME_MULTIPLIER)
print("EMA filter          :", USE_EMA_FILTER)
print("EMA period          :", EMA_PERIOD)
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
print("Magic               :", MAGIC)
print("Second entry magic  :", SECOND_ENTRY_MAGIC)
print("Lot                 :", LOT)
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

# Used to prevent detecting the same live setup repeatedly.
last_setup_time = None

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

            # -------------------------------------------------
            # Stop loss / position closed
            # -------------------------------------------------

            if not position_exists and status:

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

                print(
                    "Abnormally position: "
                    "you have an open position "
                    "with OPTIMIZED SP2L TRADER VER7.0 "
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

                print()
                print("-" * 75)
                print(
                    f"{Fore.GREEN if buy == True else Fore.RED}"
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
