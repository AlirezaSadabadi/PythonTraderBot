#!/usr/bin/env python
__author__ = "Alireza Sadabadi"
__copyright__ = "Copyright (c) 2026 Alireza Sadabadi. All rights reserved."
__credits__ = ["Alireza Sadabadi"]
__license__ = "Apache"
__version__ = "4.0"
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
# راه اندازی متاتریدر 5
# ============================================================

if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    mt5.shutdown()
    quit()


# ============================================================
# بررسی اتصال اینترنت
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
# تنظیمات
# ============================================================

SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M1
NUMBER_OF_DATA = 500

SPIKE_CANDLE_SIZE = 1.5

PGAP_POINTS = 100
MAX_SL_DISTANCE_POINTS = 1000

TP_R = 1.0

# ------------------------------------------------------------
# ورود دوم
# ------------------------------------------------------------

USE_SECOND_ENTRY = False

SECOND_ENTRY_VOLUME_MULTIPLIER = 2.0

# ------------------------------------------------------------
# فیلتر EMA
# ------------------------------------------------------------

USE_EMA_FILTER = True

EMA_PERIOD = 60

# ------------------------------------------------------------
# فیلتر ساختار روند
# ------------------------------------------------------------

USE_TREND_FILTER = True

MAX_OPPOSITE_MOVES = 1

# ------------------------------------------------------------
# فیلتر رنج / ADX
# ------------------------------------------------------------

USE_RANGE_FILTER = False

ADX_PERIOD = 14
MIN_ADX = 20.0

# ------------------------------------------------------------
# فیلتر سشن نیویورک
# ------------------------------------------------------------

USE_SESSION_FILTER = False

SESSION_START_HOUR = 1
SESSION_END_HOUR = 5

SESSION_TIMEZONE = "America/New_York"

# ------------------------------------------------------------
# مدیریت حجم معاملات
#
# LOT_MODE:
#   "FIXED"   = حجم ثابت (همیشه با مقدار LOT_FIXED معامله میشود)
#   "PERCENT" = حجم درصدی (بر اساس درصد ریسک از موجودی و فاصله SL)
# ------------------------------------------------------------

LOT_MODE = "FIXED"

# حجم ثابت (فقط وقتی LOT_MODE = "FIXED")
LOT_FIXED = 0.01

# درصد ریسک از موجودی (فقط وقتی LOT_MODE = "PERCENT")
LOT_RISK_PERCENT = 1.0

# ------------------------------------------------------------
# معامله
# ------------------------------------------------------------

MAGIC = 8

LOOP_SECONDS = 2

# ------------------------------------------------------------
# >>> تنظیمات ضربان قلب (Heartbeat)
# نمایش وضعیت ربات هر چند ثانیه
# ------------------------------------------------------------

SHOW_HEARTBEAT = True
HEARTBEAT_SECONDS = 600       # >>> هر ۱۰ دقیقه یک‌بار ALIVE چاپ می‌شود

# ============================================================
# اطلاعات نماد
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
# چاپ تنظیمات
# ============================================================

print("-" * 75)
print("ADVANCED TRADER")
print("-" * 75)
print("Symbol              :", SYMBOL)
print("Point               :", BROKER_POINT)
print("Digits              :", DIGITS)
print("Spike multiplier    :", SPIKE_CANDLE_SIZE)
print("Gap points          :", PGAP_POINTS)
print("Max SL points       :", MAX_SL_DISTANCE_POINTS)
print("TP                  :", f"{TP_R}R")

# >>> حالت حجم
if LOT_MODE == "FIXED":
    print("Lot mode            : FIXED")
    print("Lot (fixed)         :", LOT_FIXED)
elif LOT_MODE == "PERCENT":
    print("Lot mode            : PERCENT")
    print("Lot risk percent    :", f"{LOT_RISK_PERCENT}%")
else:
    print("Lot mode            : UNKNOWN ->", LOT_MODE)

print("Second entry        :", USE_SECOND_ENTRY)
print("Second entry volume :", SECOND_ENTRY_VOLUME_MULTIPLIER)
print("EMA filter          :", USE_EMA_FILTER)
print("EMA period          :", EMA_PERIOD)
print("Trend filter        :", USE_TREND_FILTER)
print("Max opposite moves  :", MAX_OPPOSITE_MOVES)
print("Range filter        :", USE_RANGE_FILTER)
print("ADX period          :", ADX_PERIOD)
print("Minimum ADX         :", MIN_ADX)
print("Session filter      :", USE_SESSION_FILTER)
print("Session timezone    :", SESSION_TIMEZONE)
print(
    "Session             :",
    f"{SESSION_START_HOUR:02d}:00 - {SESSION_END_HOUR:02d}:00"
)
print("Magic               :", MAGIC)
print("Heartbeat           :", SHOW_HEARTBEAT)
print("Heartbeat seconds   :", HEARTBEAT_SECONDS, f"({HEARTBEAT_SECONDS//60} min)")
print("-" * 75)


# ============================================================
# محاسبه EMA
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
# محاسبه ADX
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
# سشن نیویورک
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
# محاسبه حجم معامله
# ============================================================

def calculate_lot(sl_distance_price):

    # --------------------------------------------------------
    # حالت حجم ثابت
    # --------------------------------------------------------

    if LOT_MODE == "FIXED":
        return LOT_FIXED

    # --------------------------------------------------------
    # حالت حجم درصدی
    # --------------------------------------------------------

    try:

        account = mt5.account_info()

        if account is None:
            return LOT_FIXED

        balance = float(account.balance)
        risk_amount = balance * (LOT_RISK_PERCENT / 100.0)

        tick_value = float(symbol_info.trade_tick_value)
        tick_size = float(symbol_info.trade_tick_size)
        point = float(symbol_info.point)

        if tick_size <= 0 or tick_value <= 0 or point <= 0:
            print("Invalid tick info -> fallback to LOT_FIXED")
            return LOT_FIXED

        # ارزش هر 1 point برای 1 لات
        value_per_point_per_lot = tick_value * (point / tick_size)

        if value_per_point_per_lot <= 0:
            return LOT_FIXED

        sl_points = sl_distance_price / point

        if sl_points <= 0:
            return float(symbol_info.volume_min)

        # مقدار ضرر برای 1 لات در این SL
        loss_per_lot = sl_points * value_per_point_per_lot

        if loss_per_lot <= 0:
            return LOT_FIXED

        raw_lot = risk_amount / loss_per_lot

        # گرد کردن به گام حجم
        step = float(symbol_info.volume_step) if symbol_info.volume_step > 0 else 0.01

        lot = round(raw_lot / step) * step

        # محدود کردن به بازه مجاز بروکر
        lot = max(
            float(symbol_info.volume_min),
            min(float(symbol_info.volume_max), lot)
        )

        # گرد کردن نهایی
        lot = round(lot, 2)

        return lot

    except BaseException as e:

        print(f"calculate_lot error: {e} -> fallback to LOT_FIXED")
        return LOT_FIXED


# ============================================================
# دریافت داده بازار
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

        if USE_RANGE_FILTER:

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
            f"AdvancedTrader.GetRates: {str(e)}"
        )

        return None


# ============================================================
# فیلترهای ورود
# ============================================================

def entry_filters_are_valid(
    data,
    entry_pos,
    direction
):

    entry_idx = data.index[entry_pos]

    # --------------------------------------------------------
    # فیلتر EMA
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
    # فیلتر رنج / ADX
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
    # فیلتر سشن نیویورک
    # --------------------------------------------------------

    if USE_SESSION_FILTER:

        if not is_in_new_york_session(
            entry_idx
        ):
            return False

    return True


# ============================================================
# فیلتر روند
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
# تشخیص ستاپ
#
# ایندکس گذاری مطابق سبک لایو تریدر:
#   -1 = کندل آخر
#   -2 = کندل بعد از اسپایک
#   -3 = کندل اسپایک
#   -4 = کندل قبل از اسپایک
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
# ستاپ در انتظار
# ============================================================

def create_pending_buy(data):

    setup_time = data.index[-1]

    sl = float(
        data["low"].iloc[-4]
    )

    spike_body = abs(
        float(data["close"].iloc[-3])
        -
        float(data["open"].iloc[-3])
    )

    return {
        "direction": "BUY",
        "setup_time": setup_time,
        "setup_pos_time": setup_time,
        "sl": sl,
        "spike_body": spike_body,
        "second_entry_active": False
    }


def create_pending_sell(data):

    setup_time = data.index[-1]

    sl = float(
        data["high"].iloc[-4]
    )

    spike_body = abs(
        float(data["open"].iloc[-3])
        -
        float(data["close"].iloc[-3])
    )

    return {
        "direction": "SELL",
        "setup_time": setup_time,
        "setup_pos_time": setup_time,
        "sl": sl,
        "spike_body": spike_body,
        "second_entry_active": False
    }


# ============================================================
# یافتن اولین ورود خرید معتبر
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
# یافتن اولین ورود فروش معتبر
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
# ورود دوم
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
# وضعیت معامله
# ============================================================

def get_trade_state(symbol):

    resume = Meta.resume()

    if resume is None:
        return False, None

    if resume.shape[0] == 0:
        return False, None

    row = resume.loc[
        (resume["symbol"] == symbol)
        &
        (resume["magic"] == MAGIC)
    ]

    if row.empty:
        return False, None

    return True, row


# ============================================================
# >>> تابع ضربان قلب (Heartbeat)
# نمایش وضعیت ربات هر ۱۰ دقیقه
# ============================================================

def print_heartbeat(symbol, status, pending_setup):

    try:

        tick = mt5.symbol_info_tick(symbol)

        if tick is not None:
            bid = round(tick.bid, DIGITS)
            ask = round(tick.ask, DIGITS)
            spread = round(tick.ask - tick.bid, DIGITS)
        else:
            bid = ask = spread = "N/A"

        now_str = datetime.now(timezone.utc).strftime("%H:%M:%S")

        pos_state = (
            f"{Fore.GREEN}OPEN{Style.RESET_ALL}"
            if status
            else "NONE"
        )

        pending_state = (
            f"{Fore.CYAN}YES ({pending_setup['direction']}){Style.RESET_ALL}"
            if pending_setup is not None
            else "NO"
        )

        profit_info = ""

        if status:

            positions = mt5.positions_get(symbol=symbol)

            if positions:

                total_profit = sum(
                    p.profit for p in positions
                    if p.magic == MAGIC
                )

                profit_info = f" | P/L: {round(total_profit, 2)}"

        print(
            f"[{now_str}] "
            f"{Fore.CYAN}ALIVE{Style.RESET_ALL} | "
            f"{symbol} | "
            f"Bid: {bid} | "
            f"Ask: {ask} | "
            f"Spread: {spread} | "
            f"Position: {pos_state} | "
            f"Pending: {pending_state}"
            f"{profit_info}"
        )

        sys.stdout.flush()

    except BaseException as e:
        print(f"Heartbeat error: {str(e)}")


# ============================================================
# استراتژی پیشرفته
# ============================================================

def Strategy(
    symbol,
    preBuy,
    preSell,
    status,
    pending_setup
):

    sl = 0
    tp = 0
    trade_setup = None

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

    buy = detect_buy_setup(data)
    sell = detect_sell_setup(data)

    if buy and not sell:

        pending_setup = create_pending_buy(
            data
        )

        print(
            f"\n{Fore.CYAN}"
            f"BUY pending setup detected"
            f"{Style.RESET_ALL}"
        )

    elif sell and not buy:

        pending_setup = create_pending_sell(
            data
        )

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
# اطلاعات حساب
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
# نمادها
# ============================================================

symbols_list = {
    SYMBOL: [SYMBOL],
}


# ============================================================
# وضعیت اولیه
# ============================================================

buy = False
sell = False
status = False

pending_setup = None

last_setup_time = None

last_processed_candle = None

# >>> HEARTBEAT: زمان آخرین نمایش وضعیت
last_heartbeat_time = datetime.now(timezone.utc)

# ============================================================
# حلقه اصلی
# ============================================================

while True:

    if internet() is True:

        for asset in symbols_list.keys():

            symbol = symbols_list[asset][0]

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
            # بررسی پوزیشن موجود
            # =================================================

            position_exists, row = get_trade_state(
                symbol
            )

            if not position_exists and status:

                status = False
                buy = False
                sell = False
                pending_setup = None

                print(
                    f"Strategy "
                    f"{Fore.YELLOW}"
                    f"Position closed / SL or TP hit!"
                    f"{Style.RESET_ALL}"
                )

                time_module.sleep(60-LOOP_SECONDS)

            elif position_exists and not status:

                print(
                    "Abnormally position: "
                    "you have an open position "
                    "with Advanced Trader "
                    "but the status key is False!!"
                )

                status = True

            # =================================================
            # استراتژی
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
                pending_setup
            )

            # =================================================
            # اجرای ورود اول
            # =================================================

            if trade_setup is not None:

                direction = trade_setup["direction"]

                entry = trade_setup["entry"]
                sl = trade_setup["sl"]
                tp = trade_setup["tp"]
                risk = trade_setup["risk"]

                # ---------------------------------------------
                # محاسبه حجم بر اساس حالت انتخاب شده
                # ---------------------------------------------
                lot = calculate_lot(risk)

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
                    "Lot mode   :",
                    LOT_MODE
                )

                print(
                    "Lot        :",
                    lot
                )

                print(
                    "Second     :",
                    round(
                        trade_setup["second_entry"],
                        DIGITS
                    )
                )

                print("-" * 75)

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

                if USE_SECOND_ENTRY:

                    print(
                        f"{Fore.MAGENTA}"
                        f"Second entry is ENABLED."
                        f"{Style.RESET_ALL}"
                    )

                    print(
                        "Second entry price:",
                        round(
                            trade_setup["second_entry"],
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

        # ============================================================
        # >>> ضربان قلب (هر ۱۰ دقیقه)
        # ============================================================

        if SHOW_HEARTBEAT:

            now = datetime.now(timezone.utc)

            if (now - last_heartbeat_time).total_seconds() >= HEARTBEAT_SECONDS:

                last_heartbeat_time = now

                for asset in symbols_list.keys():

                    symbol = symbols_list[asset][0]

                    print_heartbeat(
                        symbol,
                        status,
                        pending_setup
                    )

    time_module.sleep(
        LOOP_SECONDS
    )
