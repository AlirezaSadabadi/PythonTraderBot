#!/usr/bin/env python
__author__ = "Alireza Sadabadi"
__copyright__ = "Copyright (c) 2026 Alireza Sadabadi. All rights reserved."
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
from colorama import init as colorama_init
from colorama import Fore
from colorama import Style
import socket
import sys

colorama_init()
# ساخت کانکشن بین ربات و متاتریدر
if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    mt5.shutdown()
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

def Strategy(symbol, preBuy, preSell, status):
    sl = 0
    tp = 0
    number_of_data = 10
    spikeCandleSize = 2 # the spike candle size must be atleast x times bigger than around candles
    pGapSize = 1 # distance from low of candle after spike and high of candle before spike
    try:
        data = Meta.GetRates(symbol, number_of_data , timeFrame=mt5.TIMEFRAME_M1)
        if data.empty:
                    print("No data received")
                    mt5.shutdown()
                    quit()
    except BaseException as e:
        print(f"An exception has occurred in TraderBot.Strategy GetRates: {str(e)}")
        return preBuy, preSell, status, sl, tp
    else:
        
   
        #اگر پوزیشن خرید و فروش باز از قبل نداریم
        if status == False:

            # تشکیل سیگنال خرید و فروش
            buy0 = data['low'].iloc[-1] < data['low'].iloc[-2]

            buy1 = data['close'].iloc[-2] > data['close'].iloc[-3]
            buy2 = data['open'].iloc[-2] > data['open'].iloc[-3]
            buy3 = data['close'].iloc[-2] > data['close'].iloc[-3]
            buy4 = data['open'].iloc[-3] > data['open'].iloc[-4]
            buy5 = data['close'].iloc[-2] > data['open'].iloc[-2]
            buy6 = data['close'].iloc[-3] > data['open'].iloc[-3]
            buy7 = data['close'].iloc[-4] > data['open'].iloc[-4]

            pGapBuy = data['low'].iloc[-2] > data['high'].iloc[-4] + pGapSize
            spikeBuy = (data['close'].iloc[-3] - data['open'].iloc[-3] > spikeCandleSize * (data['close'].iloc[-2]-data['open'].iloc[-2])) & (data['close'].iloc[-3] - data['open'].iloc[-3] > spikeCandleSize * (data['close'].iloc[-4]-data['open'].iloc[-4])) & (data['close'].iloc[-3] - data['open'].iloc[-3] > spikeCandleSize * (data['close'].iloc[-1]-data['open'].iloc[-1]))

            buy = buy0 & buy1 & buy2 & buy3 & buy4 & buy5 & buy6 & buy7 & pGapBuy & spikeBuy

            sell0 = data['high'].iloc[-1] > data['high'].iloc[-2]

            sell1 = data['close'].iloc[-2] < data['close'].iloc[-3]
            sell2 = data['open'].iloc[-2] < data['open'].iloc[-3]
            sell3 = data['close'].iloc[-3] < data['close'].iloc[-4]
            sell4 = data['open'].iloc[-3] < data['open'].iloc[-4]
            sell5 = data['close'].iloc[-2] < data['open'].iloc[-2]
            sell6 = data['close'].iloc[-3] < data['open'].iloc[-3]
            sell7 = data['close'].iloc[-4] < data['open'].iloc[-4]

            pGapSell = data['high'].iloc[-2] < data['low'].iloc[-4] - pGapSize
            spikeSell = (data['open'].iloc[-3] - data['close'].iloc[-3] > spikeCandleSize * (data['open'].iloc[-2]-data['close'].iloc[-2])) & (data['open'].iloc[-3] - data['close'].iloc[-3] > spikeCandleSize * (data['open'].iloc[-4]-data['close'].iloc[-4])) & (data['open'].iloc[-3] - data['close'].iloc[-3] > spikeCandleSize * (data['open'].iloc[-1]-data['close'].iloc[-1]))

            sell = sell0 & sell1 & sell2 & sell3 & sell4 & sell5 & sell6 & sell7 & pGapSell & spikeSell
                
                      
            
            if buy == True or sell == True:
                status = True

            if buy == True:
                price = mt5.symbol_info(symbol).ask
                sl = data['low'].iloc[-4]
                tp = (price - sl) + price
            elif sell == True:
                price = mt5.symbol_info(symbol).bid
                sl = data['high'].iloc[-4]
                tp = price - (sl - price)
            else:
                sl = 0
                tp = 0
        
            return buy,sell,status,sl,tp
        else:
           return preBuy, preSell, status, sl, tp
    

    
######################################################################################
accountInfo = mt5.account_info()
print("-"*75)
print(f"Login: {accountInfo.login} \tserver: {accountInfo.server} \tleverage: {accountInfo.leverage}")
print(f"Balance: {accountInfo.balance} \tEquity: {accountInfo.equity} \tProfit: {accountInfo.profit}")
print(f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
print("-"*75)

symbols_list = {
    "XAUUSD": ["XAUUSD", 0.01],
   }

buy = False
sell = False
status = False
magic = 8

while True:

    if internet() == True:
        
        # Meta.TrailingStopLoss([magic])
        # Meta.VerifyTSL([magic])

         # Strategy
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
                    if row.empty and status == True:
                        status=False
                        print(f"Strategy {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")
                        # حلقه اصلی هر ۱۰ ثانیه اجرا می شود بنابراین اگر در 
                        # موقعیتی استاپ لاس خورد دوباره در همان موقعیت نباید
                        # پوزیشن قبلی مجدد باز شود
                        time.sleep(50)
                    elif not row.empty and status == False:
                        print("Abnormally position: you have a open position with Strategy strategy but the status key is False!!")
                elif status == True:
                    status=False
                    print(f"Strategy {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")
                    time.sleep(50)

                buy,sell,status,sl,tp=Strategy(symbol, buy, sell, status)
                Meta.run(symbol, buy, sell, lot, tp, sl, magic, stopLossPure=True)  

    # سیگنال زنده بودن ربات                
    # counter += 1          
    # print(f"{':' if counter % 2 == 0 else '.'}",end='')
    # sys.stdout.flush()

    
    time.sleep(10)