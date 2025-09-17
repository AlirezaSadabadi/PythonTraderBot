#!/usr/bin/env python
__author__ = "Alireza Sadabadi"
__copyright__ = "Copyright (c) 2025 Alireza Sadabadi. All rights reserved."
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
from datetime import datetime, timezone, timedelta
import time
from Meta import *
from colorama import init as colorama_init
from colorama import Fore
from colorama import Style
import pandas_ta as ta
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

def VWAP_BB(symbol, preBuy, preSell, status):
    number_of_data = 50
    varsl = 0
    vartp = 0
    try:
        data = Meta.GetRates(symbol, number_of_data , timeFrame=mt5.TIMEFRAME_M5)
    except BaseException as e:
        print(f"An exception has occurred in TraderBot.VWAP_BB GetRates: {str(e)}")
        return preBuy, preSell, status, 0, 0
    else:
        
        data['rsi']=ta.rsi(data.close, length=16)        
        
        #اگر پوزیشن خرید و فروش باز از قبل نداریم
        if status == False:

            # فرمول استراتژی برای سیگنال و تولید ستون های لازم
            data["vwap"]=ta.vwap(data.high, data.low, data.close, data.tick_volume)
            BB = ta.bbands(data.close, length=15, std=2.0)
            data=data.join(BB)

            backCandles = 26
            data['uptrend'] = 1
            data['downtrend'] = 1
            data['max_open_close'] = np.maximum(data['open'], data['close'])
            data['min_open_close'] = np.minimum(data['open'], data['close'])
            data.loc[(data['max_open_close'] >= data['vwap']), 'downtrend'] = 0
            data.loc[(data['min_open_close'] <= data['vwap']), 'uptrend'] = 0
            data['signal_uptrend'] = data['uptrend'].rolling(backCandles + 1, min_periods=1).min()
            data['signal_downtrend'] = data['downtrend'].rolling(backCandles + 1, min_periods=1).min()
            data['vwapsignal'] = 0
            data.loc[(data['signal_uptrend'] == 1) & (data['signal_downtrend'] == 1), 'vwapsignal'] = 3
            data.loc[(data['signal_uptrend'] == 1) & (data['signal_downtrend'] == 0), 'vwapsignal'] = -1
            data.loc[(data['signal_uptrend'] == 0) & (data['signal_downtrend'] == 1), 'vwapsignal'] = 1

            # if((data.vwapsignal.iloc[-2] == 1) or (data.vwapsignal.iloc[-2] == -1)):
            #     print(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
            #     print(f"Buy {symbol} {Fore.GREEN if (data.vwapsignal.iloc[-2] == 1) else Fore.RED}VWAP {Fore.GREEN if (data.close.iloc[-2] <= data["BBL_15_2.0"].iloc[-2]) else Fore.RED}BB {Fore.GREEN if (data.rsi.iloc[-2] < 46) else Fore.RED}RSI {Style.RESET_ALL}")
            #     print(f"Sel {symbol} {Fore.GREEN if (data.vwapsignal.iloc[-2] == -1) else Fore.RED}VWAP {Fore.GREEN if (data.close.iloc[-2] >= data["BBU_15_2.0"].iloc[-2]) else Fore.RED}BB {Fore.GREEN if (data.rsi.iloc[-2] > 59) else Fore.RED}RSI {Style.RESET_ALL}")

            # تشکیل سیگنال خرید و فروش
            buy = (data.vwapsignal.iloc[-2] == 1) and \
                        (data.close.iloc[-2] <= data["BBL_15_2.0"].iloc[-2]) and \
                        (data.rsi.iloc[-2] < 46)

            sell = (data.vwapsignal.iloc[-2] == -1) and \
                        (data.close.iloc[-2] >= data["BBU_15_2.0"].iloc[-2]) and \
                        (data.rsi.iloc[-2] > 59)
            
            if buy == True or sell == True:
                status = True
                data['atr'] = ta.atr(data.high, data.low, data.close, length=7)
                varsl = 1.2 * data.atr.iloc[-1]
                vartp = 1.89 * varsl
            return buy,sell,status,varsl,vartp
        else:
            #اگر پوزیشن قبلی خرید بوده
            if preBuy == True:
                #اگر به شرط زیر رسیدی پوزیشن خرید رو ببند 
                if data.rsi.iloc[-2] >= 90 :
                    return False,True,False,0,0
                # در غیر اینصورت با مقادیر قبلی همچنان نمودار را چک کن
                else:
                    return True,False,True,0,0
            elif preSell == True:
                #اگر به شرط زیر رسیدی پوزیشن فروش رو ببند
                if data.rsi.iloc[-2] <= 10:
                    return True,False,False,0,0
                # در غیر اینصورت با مقادیر قبلی همچنان نمودار را چک کن
                else:
                    return False,True,True,0,0
    

    
######################################################################################
accountInfo = mt5.account_info()
print("-"*75)
print(f"Login: {accountInfo.login} \tserver: {accountInfo.server} \tleverage: {accountInfo.leverage}")
print(f"Balance: {accountInfo.balance} \tEquity: {accountInfo.equity} \tProfit: {accountInfo.profit}")
print(f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
print("-"*75)

# symbols_list = {
#     "BITCOIN" : ["BITCOIN", 0.01],
#     "RIPPLE" : ["RIPPLE", 0.01],
#     "BNB" : ["BNB", 0.01],
#     "CARDANO" : ["CARDANO", 0.01],
#     "CHAINLINK" : ["CHAINLINK", 0.01],
#     "LITECOIN" : ["LITECOIN", 0.01],
#     "POLYGON" : ["POLYGON", 0.01],
#     "SOLANA" : ["SOLANA", 0.01],
#     "UNISWAP" : ["UNISWAP", 0.01],
#     "AXS" : ["AXS", 0.01],
#     "SNEK" : ["SNEK", 0.01],
#     "COSMOS" : ["COSMOS", 0.01],
#     "PYTH" : ["PYTH", 0.01],
#     "COTI" : ["COTI", 0.01],
#     "FETCH.AI" : ["FETCH.AI", 0.01],
#     "ILLUVIUM" : ["ILLUVIUM", 0.01],
#     "IMGNAI" : ["IMGNAI", 0.01],
#     "INJ" : ["INJ", 0.01],
#     "NAKA" : ["NAKA", 0.01],
#     "RENDER" : ["RENDER", 0.01]
#    }

symbols_list = {
    "RIPPLE" : ["RIPPLE", 0.01],
    "BNB" : ["BNB", 0.01],
    "CARDANO" : ["CARDANO", 0.01],
    "CHAINLINK" : ["CHAINLINK", 0.01]
   }

buyVWAP = {}
sellVWAP = {}
statusVWAP = {}
magic = 5

for asset in symbols_list.keys():
    symbol = symbols_list[asset][0]
    buyVWAP[symbol] = False
    sellVWAP[symbol] = False
    statusVWAP[symbol] = False

while True:

    if internet() == True:
        
        currentTimeMinute = datetime.now(timezone.utc).minute
        # تایم فریم ۵ دقیقه
        if currentTimeMinute % 5 == 0:
            Meta.TrailingStopLoss([magic])
            Meta.VerifyTSL([magic])
            
            # VWAP_BB
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
                        if row.empty and statusVWAP[symbol] == True:
                            statusVWAP[symbol]=False
                            print(f"VWAP_BB {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")
                            # حلقه اصلی هر ۱۰ ثانیه اجرا می شود بنابراین اگر در 
                            # موقعیتی استاپ لاس خورد دوباره در همان موقعیت نباید
                            # پوزیشن قبلی مجدد باز شود
                            # چون ۶۰ ثانیه هم در همین شرط اسلیپ می کنیم بنابراین حاصل ۲۳۰ میشود
                            time.sleep(230)
                        elif not row.empty and statusVWAP[symbol] == False:
                            print("Abnormally position: you have a open position with VWAP_BB strategy but the statusVWAP key is False!!")
                    elif statusVWAP[symbol] == True:
                        statusVWAP[symbol]=False
                        print(f"VWAP_BB {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")
                        time.sleep(230)

                    buyVWAP[symbol],sellVWAP[symbol],statusVWAP[symbol],varsl,vartp=VWAP_BB(symbol, buyVWAP[symbol], sellVWAP[symbol], statusVWAP[symbol])
                    Meta.run(symbol, buyVWAP[symbol], sellVWAP[symbol], lot, vartp, varsl, magic, stopLossWithAtr=True)  
            # جلوگیری از چندبار وارد شدن در دقیقه ضریب ۵
            time.sleep(60)

    # سیگنال زنده بودن ربات                
    # counter += 1          
    # print(f"{':' if counter % 2 == 0 else '.'}",end='')
    # sys.stdout.flush()

    
    time.sleep(10)