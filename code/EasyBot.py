#!/usr/bin/env python
__author__ = "Alireza Sadabadi"
__copyright__ = "Copyright (c) 2024 Alireza Sadabadi. All rights reserved."
__credits__ = ["Alireza Sadabadi"]
__license__ = "Apache"
__version__ = "2.0"
__maintainer__ = "Alireza Sadabadi"
__email__ = "alirezasadabady@gmail.com"
__status__ = "Test"
__doc__ = "you can see the tutorials in https://youtube.com/@alirezasadabadi?si=d8o7LK_Ai1Hf68is"

import MetaTrader5 as mt5
from datetime import datetime, timezone
import time
from Meta import *

# ساخت کانکشن بین ربات و متاتریدر
# Establish connection between bot and metatrader
if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()

# یک استراتژی ساده میانگین متحرک با دو نمودار کند و تند
# an strategy that two simple moving average with different length (fast and slow)
def SMA(symbol, SMA_Fast_Length=20, SMA_Slow_Length=200):  

    df = Meta.GetRates(symbol, 205 , timeFrame=mt5.TIMEFRAME_M1)

    df["SMA fast"] = df["close"].rolling(SMA_Fast_Length).mean()
    df["SMA slow"] = df["close"].rolling(SMA_Slow_Length).mean()

    buySignal1 = df["SMA fast"].iloc[-2] > df["SMA slow"].iloc[-2]
    buySignal2 = df["SMA fast"].iloc[-3] < df["SMA slow"].iloc[-3]

    sellSignal1 = df["SMA fast"].iloc[-2] < df["SMA slow"].iloc[-2]
    sellSignal2 = df["SMA fast"].iloc[-3] > df["SMA slow"].iloc[-3]

    # پیدا کردن نقطه تقاطع دو میانگین تند و کند
    # find the MA fast and slow cross
    buy = buySignal1 and buySignal2
    sell = sellSignal1 and sellSignal2
    
    return buy, sell

#####################################################################################################
# چاپ بنر ربات
# print bot banner
accountInfo = mt5.account_info()
print("-"*75)
print(f"Login: {accountInfo.login} \tserver: {accountInfo.server} \tleverage: {accountInfo.leverage}")
print(f"Balance: {accountInfo.balance} \tEquity: {accountInfo.equity} \tProfit: {accountInfo.profit}")
print(f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
print("-"*75)

symbol = 'BITCOIN'
lot = 0.01

# تلاش برای فعال سازی سیمبل در مارکت واتچ متاتریدر
# try to enable symbol in market watch
selected = mt5.symbol_select(symbol)
if not selected:
    print(f"\nERROR - Failed to select '{symbol}' in MetaTrader 5 with error :",mt5.last_error())                
else: 
    while True:
        # اجرای استراتژی و گرفتن سیگنال
        # run the strategy and get the signal
        buy, sell = SMA(symbol)
        # صدور دستور پوزیشن گیری و ثبت سفارش
        # send order and get the position
        Meta.run(symbol, buy, sell, lot, pct_tp=0.12, pct_sl=0.06, magic=0)
        # در اجرای هر گام حلقه یک دقیقه صبر کن
        # run the loop every 1 minute
        time.sleep(60)