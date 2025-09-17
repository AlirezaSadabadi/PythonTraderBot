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
from datetime import datetime, timezone
import time
from Meta import *
from colorama import init as colorama_init
from colorama import Fore
from colorama import Style
import pandas_ta as pdta
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

def CE_ZLSMA_HA(symbol, preBuy, preSell, status, atrPeriod=3, atrMultiplier=1.95,zlsmaLength=33,risk=1,reward=2):
    number_of_data = zlsmaLength + 40
    varsl = 0
    vartp = 0
    try:
        data = Meta.GetRates(symbol, number_of_data , timeFrame=mt5.TIMEFRAME_H4)
    except BaseException as e:
        print(f"An exception has occurred in TraderBot.CE_ZLSMA GetRates: {str(e)}")
        return False, False, False, 0, 0
    else:
        # Heikin Ashi
        # محاسبه مقادیر هیکن آشی
        data['hclose'] = (data['close']+data['open']+data['high']+data['low'])/4
        data['hopen'] = data['open']
        data.reset_index(inplace=True)
        for i in range(1, len(data)):
            data.at[i,'hopen'] = (data.loc[i-1]['hopen']+data.loc[i-1]['hclose'])/2
        data.set_index("time", inplace=True)

        # calculate zlsma
        data['zlsma'] = pdta.zlma(close=data['hclose'], length=zlsmaLength, mamode='simple')

        data.dropna(inplace=True)

        if status == False:
            #Chandelier Exit
            data['atr'] = pd.Series(np.nan)
            data['atr'] = data['high'] - data['low']
            data['atr'] = data['atr'].rolling(window=atrPeriod).mean()

            data['long'] = data['high'].rolling(window=atrPeriod).max() - (data['atr'] * atrMultiplier)
            data['short'] = data['low'].rolling(window=atrPeriod).min() + (data['atr'] * atrMultiplier)

            #  Long position
            data['enter_long'] = np.where(((data['close'] > data['short']) & (data['close'].shift(1) <= data['short'].shift(1))), 1, 0)
            #  Short position
            data['enter_short'] = np.where(((data['close'] < data['long']) & (data['close'].shift(1) >= data['long'].shift(1))), 1, 0)
            data.dropna(inplace=True)

            data.dropna(inplace=True)

            buy = (data['enter_long'].iloc[-2] == 1) and \
                    (data.hclose.iloc[-2] > data.hopen.iloc[-2]) and \
                    (data.hclose.iloc[-2] > data.zlsma.iloc[-2]) 
                    

            sell = (data['enter_short'].iloc[-2] == 1) and \
                    (data.hclose.iloc[-2] < data.hopen.iloc[-2]) and \
                    (data.hclose.iloc[-2] < data.zlsma.iloc[-2])

            if buy == True or sell == True:
                status=True
                data['atr'] = pdta.atr(data.high, data.low, data.close, length=7)
                varsl = 1 * data.atr.iloc[-1]
                vartp = 2.16 * varsl
            return buy,sell,status,varsl,vartp
        else:
            #اگر پوزیشن قبلی خرید بوده
            if preBuy == True:        
                #اگر به شرط زیر رسیدی پوزیشن خرید رو ببند        
                if (data.hclose.iloc[-2] < data.hopen.iloc[-2]) and (data.hclose.iloc[-2] < data.zlsma.iloc[-2]):
                    return False,True,False,0,0
                # در غیر اینصورت با مقادیر قبلی همچنان نمودار را چک کن
                else:
                    return True,False,True,0,0
            elif preSell == True:
                #اگر به شرط زیر رسیدی پوزیشن فروش رو ببند
                if (data.hclose.iloc[-2] > data.hopen.iloc[-2]) and (data.hclose.iloc[-2] > data.zlsma.iloc[-2]):
                    return True,False,False,0,0
                else:
                    return False,True,True,0,0
    
######################################################################################
accountInfo = mt5.account_info()
print("-"*75)
print(f"Login: {accountInfo.login} \tserver: {accountInfo.server} \tleverage: {accountInfo.leverage}")
print(f"Balance: {accountInfo.balance} \tEquity: {accountInfo.equity} \tProfit: {accountInfo.profit}")
print(f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
print("-"*75)

# در متاتریدر ملاک ساعت روسیه است برای همین تمام تایم ها دو ساعت
# جابجا شدند
launching = ["22:06",
             "02:00",
             "06:00",
             "10:00",
             "14:00",
             "18:00"]      


symbols_list = {
    "BITCOIN" : ["BITCOIN", 0.01],
    "RIPPLE" : ["RIPPLE", 0.01],
    "BNB" : ["BNB", 0.01],
    "CARDANO" : ["CARDANO", 0.01],
    "CHAINLINK" : ["CHAINLINK", 0.01],
    "LITECOIN" : ["LITECOIN", 0.01],
    "POLYGON" : ["POLYGON", 0.01],
    "SOLANA" : ["SOLANA", 0.01],
    "UNISWAP" : ["UNISWAP", 0.01],
    "AXS" : ["AXS", 0.01],
    "COSMOS" : ["COSMOS", 0.01],
    "PYTH" : ["PYTH", 0.01],
    "ILLUVIUM" : ["ILLUVIUM", 0.01],
    "INJ" : ["INJ", 0.01],
    "RENDER" : ["RENDER", 0.01],
    "DOGECOIN" : ["DOGECOIN", 0.01],
    "ETHEREUM" : ["ETHEREUM", 0.01],
    "POLKADOT" : ["POLKADOT", 0.01]
   }

buy = {}
sell = {}
status = {}
magic = 4

for asset in symbols_list.keys():
    symbol = symbols_list[asset][0]
    buy[symbol] = False
    sell[symbol] = False
    status[symbol] = False

while True:

    if internet() == True:

        #برای تایم فریم ۴ ساعته
        current_time = datetime.now(timezone.utc).strftime("%H:%M")

        if current_time in launching:  
            is_time = True
        else:
            is_time = False

        if is_time:
        
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
                        if row.empty and status[symbol] == True:
                            status[symbol]=False
                            print(f"CE_ZLSMA_HA {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}") 
                        elif not row.empty and status[symbol] == False:
                            print("Abnormally position: you have a open position with CE_ZLSMA_HA strategy but the status key is False!!")
                    elif status[symbol] == True:
                        status[symbol]=False
                        print(f"CE_ZLSMA_HA {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")

                    buy[symbol],sell[symbol],status[symbol],varsl,vartp=CE_ZLSMA_HA(symbol, buy[symbol], sell[symbol], status[symbol])
                    Meta.run(symbol, buy[symbol], sell[symbol], lot, vartp, varsl, magic) 
            time.sleep(40) 

    
    time.sleep(20)