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
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timezone
import time
import ta.momentum
from Meta import *
from colorama import init as colorama_init
from colorama import Fore
from colorama import Style
import socket
import sys

colorama_init()
# ساخت کانکشن بین ربات و متاتریدر
if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()

def internet(host="8.8.8.8", port=53, timeout=3):
    """
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        # print(f"Internet Connection Error: {ex}")
        # print("Don't worried, I will try 10 seconds later again :)")
        print("@",end='')
        sys.stdout.flush()
        return False

def HA_RSI_CE_EMA(symbol, preBuy, preSell, status, rsiLength=7, haRsiLength=15, upper=66, lower=28, atrPeriod=4, atrMultiplier=3):
    number_of_data = haRsiLength + 375
    try:
        data = Meta.GetRates(symbol, number_of_data , timeFrame=mt5.TIMEFRAME_M1)
    except BaseException as e:
        print(f"An exception has occurred in TraderBot.HeikinAshi GetRates: {str(e)}")
        return preBuy, preSell, status
    else:
        # محاسبه آر اس آی با طول دیگر به عنوان سیگنال خروج از پوزیشن
        data['rsi'] = ta.momentum.RSIIndicator(data["close"], window=rsiLength).rsi()
        data.dropna(inplace=True)
        #اگر پوزیشن خرید و فروش باز از قبل نداریم
        if status == False:
            # مقادیر را ابتدا به مقیاس آر اس آی می بریم
            # توجه شود که در این استراتژی دو مقدار مختلف برای دو آر اس آی مختلف داریم
            # یکی برای مقادیر هیکن آشی و دیگری برای خود آر اس آی
            data['closeRsi'] = ta.momentum.RSIIndicator(data["close"],window=haRsiLength).rsi()
            data['openRsi'] = ta.momentum.RSIIndicator(data["open"],window=haRsiLength).rsi()
            data['highRsi_Raw'] = ta.momentum.RSIIndicator(data["high"],window=haRsiLength).rsi()
            data['lowRsi_Raw'] = ta.momentum.RSIIndicator(data["low"],window=haRsiLength).rsi()
            data['highRsi'] = data[['highRsi_Raw','lowRsi_Raw']].max(axis=1)
            data['lowRsi'] = data[['highRsi_Raw','lowRsi_Raw']].min(axis=1)

            # محاسبه مقادیر هیکن آشی
            data['hclose'] = (data['closeRsi']+data['openRsi']+data['highRsi']+data['lowRsi'])/4
            data['hopen'] = data['openRsi']
            data.dropna(inplace=True)

            data.reset_index(inplace=True)
            for i in range(1, len(data)):
                data.at[i,'hopen'] = (data.loc[i-1]['hopen']+data.loc[i-1]['hclose'])/2
            data.set_index("time", inplace=True)
            data['hhigh'] = data[['highRsi', 'hopen', 'hclose']].max(axis=1)
            data['hlow'] = data[['lowRsi', 'hopen', 'hclose']].min(axis=1)

            # محاسبه شندلر برای ورود قویتر به پوزیشن
            data['atr'] = pd.Series(np.nan)
            data['atr'] = data['high'] - data['low']
            data['atr'] = data['atr'].rolling(window=atrPeriod).mean()

            data['long'] = data['high'].rolling(window=atrPeriod).max() - (data['atr'] * atrMultiplier)
            data['short'] = data['low'].rolling(window=atrPeriod).min() + (data['atr'] * atrMultiplier)

            #buy
            data['ce'] = np.where((data['close'] > data['short']) & (data['close'].shift(1) <= data['short'].shift(1)), 1, np.nan)
            #sell
            data['ce'] = np.where((data['close'] < data['long']) & (data['close'].shift(1) >= data['long'].shift(1)), -1, data.ce) 
            data['ce'] = data.ce.ffill().fillna(0)

            # محاسبه ای ام ای و ار اس آی برای شاخص ورود قوی تر به پوزیشن
            data['ema'] = data["close"].ewm(min_periods=200,span=200,adjust=False).mean()
            data.dropna(inplace=True)

            buy = (data.hclose.iloc[-3] < lower) and \
                    (data.hclose.iloc[-3] < data.hopen.iloc[-3]) and \
                    (data.hclose.iloc[-2] > data.hopen.iloc[-2]) and \
                    (data.close.iloc[-2] > data.ema.iloc[-2]) and \
                    (data['ce'].iloc[-2] == 1)
            
            sell = (data.hclose.iloc[-3] > upper) and \
                    (data.hclose.iloc[-3] > data.hopen.iloc[-3]) and \
                    (data.hclose.iloc[-2] < data.hopen.iloc[-2]) and \
                    (data.close.iloc[-2] < data.ema.iloc[-2]) and \
                    (data['ce'].iloc[-2] == -1)
            
            if buy == True or sell == True:
                status = True
            return buy,sell,status
            
        else:
            #اگر پوزیشن قبلی خرید بوده
            if preBuy == True:
                #اگر به باند بالایی رسیدی پوزیشن خرید رو ببند یا در حقیقت بفروش چیزهایی که خریدی در باند پایین
                if data.rsi.iloc[-2] > upper :
                    return False,True,False
                # در غیر اینصورت با مقادیر قبلی همچنان نمودار را چک کن
                else:
                    return True,False,True
            elif preSell == True:
                #اگر به باند پایینی رسیدی پوزیشن فروش رو ببند
                if data.rsi.iloc[-2] < lower:
                    return True,False,False
                else:
                    return False,True,True
    

    
######################################################################################
accountInfo = mt5.account_info()
print("-"*75)
print(f"Login: {accountInfo.login} \tserver: {accountInfo.server} \tleverage: {accountInfo.leverage}")
print(f"Balance: {accountInfo.balance} \tEquity: {accountInfo.equity} \tProfit: {accountInfo.profit}")
print(f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
print("-"*75)

symbols_list = {
    "BITCOIN": ["BITCOIN", 0.01],
   }

buyHA = False
sellHA = False
statusHA = False
magic = 3

while True:

    if internet() == True:
        
        Meta.TrailingStopLoss([magic])
        Meta.VerifyTSL([magic])

         
        for asset in symbols_list.keys():
            symbol = symbols_list[asset][0]
            lot = symbols_list[asset][1]

            selected = mt5.symbol_select(symbol)
            if not selected:
                print(f"\nERROR - Failed to select '{symbol}' in MetaTrader 5 with error :",mt5.last_error())                
            else:         
                resume = Meta.resume()
                if resume.shape[0] > 0:
                    row = resume.loc[(resume["symbol"] == symbol) & (resume["magic"] == magic)]
                    # در صورتی که استاپ لاس یک پوزیشن بخوره
                    # باید وضعیت به حالت اولیه برای سفارش گذاری برگرده
                    if row.empty and statusHA == True:
                        statusHA=False
                        print(f"HA {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")
                        # حلقه اصلی هر ۱۰ ثانیه اجرا می شود بنابراین اگر در 
                        # موقعیتی استاپ لاس خورد دوباره در همان موقعیت نباید
                        # پوزیشن قبلی مجدد باز شود
                        time.sleep(50)
                    elif not row.empty and statusHA == False:
                        print("Abnormally position: you have a open position with HA strategy but the statusHA key is False!!")
                elif statusHA == True:
                    statusHA=False
                    print(f"HA {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")
                    time.sleep(50)

                buyHA,sellHA,statusHA=HA_RSI_CE_EMA(symbol, buyHA, sellHA, statusHA)
                Meta.run(symbol, buyHA, sellHA, lot, 0.12, 0.06, 3)  

    # سیگنال زنده بودن ربات                
    # counter += 1          
    # print(f"{':' if counter % 2 == 0 else '.'}",end='')
    # sys.stdout.flush()

    
    time.sleep(10)