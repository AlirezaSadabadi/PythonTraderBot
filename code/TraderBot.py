#!/usr/bin/env python
# -*- coding: utf-8 -*- 
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
from datetime import datetime, timezone, timedelta
import time
import ta.momentum
from Meta import *
from colorama import init as colorama_init
from colorama import Fore
from colorama import Style
import pandas_ta as pdta
import socket
import sys
import csv

colorama_init()
# ساخت کانکشن بین ربات و متاتریدر
if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()

supportList=[]
resistanceList=[]
# به روزرسانی سطوح حمایتی و مقاومتی
def UpdateSupportResistance():
    global supportList, resistanceList
    # دریافت سطوح حمایتی
    # Get Support levels
    with open('support.csv', newline='') as myfile:
        reader = csv.reader(myfile, quoting=csv.QUOTE_NONNUMERIC)
        supportList = list(reader)
    # سه حمایت آخر
    supportList = supportList[0][-3:]

    # دریافت سطوح مقاومتی
    # Get Resistance levels
    with open('resistance.csv', newline='') as myfile:
        reader = csv.reader(myfile, quoting=csv.QUOTE_NONNUMERIC)
        resistanceList = list(reader)
    # سه مقاومت آخر
    resistanceList = resistanceList[0][-3:]

# بررسی اتصال به اینترنت
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
    
#bitcoin daily time frame: 20 200
#bitcoin 4h    time frame: 159 160
def SMA(symbol, SMA_Fast_Length=20, SMA_Slow_Length=200):  

    df = Meta.GetRates(symbol, 500 , timeFrame=mt5.TIMEFRAME_D1)

    df["SMA fast"] = df["close"].rolling(SMA_Fast_Length).mean()
    df["SMA slow"] = df["close"].rolling(SMA_Slow_Length).mean()

    buy = df["SMA fast"].iloc[-2] > df["SMA slow"].iloc[-2]

    sell = df["SMA fast"].iloc[-2] < df["SMA slow"].iloc[-2]
    
    return buy, sell
    
#bitcoin daily time frame: 20 200
#bitcoin 4h    time frame: 159 160
def SMA_RSI(symbol, SMA_Fast_Length=20, SMA_Slow_Length=200, RSI_Length=14):    
    df = Meta.GetRates(symbol, 500 , timeFrame=mt5.TIMEFRAME_D1)
    df["SMA fast"] = df["close"].rolling(SMA_Fast_Length).mean()
    df["SMA slow"] = df["close"].rolling(SMA_Slow_Length).mean()
    df["RSI"] = ta.momentum.RSIIndicator(df["close"], window=RSI_Length).RSI()

    buySignal1 = df["SMA fast"].iloc[-2] > df["SMA slow"].iloc[-2]
    buySignal2 = df["RSI"].iloc[-2] < df["RSI"].iloc[-3]

    sellSignal1 = df["SMA fast"].iloc[-2] < df["SMA slow"].iloc[-2]
    sellSignal2 = df["RSI"].iloc[-2] > df["RSI"].iloc[-3]
    
    buy = buySignal1 and buySignal2
    sell = sellSignal1 and sellSignal2    

    return buy, sell

#bitcoin daily time frame = 175,201
#bitcoin 4H    time frame = 63,49
def SMA_EMA_Strategy(symbol, movingAverage=[175,201]):
    df = Meta.GetRates(symbol, 500 , timeFrame=mt5.TIMEFRAME_D1)
    df["EMA"] = df["close"].ewm(min_periods=int(movingAverage[0]),span=int(movingAverage[0]),adjust=False).mean()  
    df["SMA"] = df["close"].rolling(int(movingAverage[1])).mean()

    buy = df["EMA"].iloc[-2] > df["SMA"].iloc[-2]
    sell = df["EMA"].iloc[-2] < df["SMA"].iloc[-2]
    return buy, sell

# بهترین مقادیر برای تایم فریم ۴ ساعته از سال ۲۰۲۱ تا ۲۰۲۴ اعداد ۲۱ و ۲ می باشد
def BB_Full(symbol, preBuy, preSell, status, movingAverage=22,coef=2):
    number_of_data = movingAverage + 25
    try:
        data = Meta.GetRates(symbol, number_of_data , timeFrame=mt5.TIMEFRAME_H4)
    except BaseException as e:
        print(f"An exception has occurred in TraderBot.BB_Full GetRates: {str(e)}")
        return preBuy, preSell, status
    else:
        data.dropna(inplace=True)
        data["Middle"] = data["close"].rolling(int(movingAverage)).mean()
        data.dropna(inplace=True)
        data["Lower"] = data["Middle"] - coef * data["close"].rolling(movingAverage).std()
        data["Upper"] = data["Middle"] + coef * data["close"].rolling(movingAverage).std()
        data.dropna(inplace=True)
        
        #اگر پوزیشن خرید و فروش باز از قبل نداریم
        if status == False:
            buy = (data.close.iloc[-3] < data.Lower.iloc[-3]) and \
                        (data.close.iloc[-3] < data.open.iloc[-3]) and \
                        (data.close.iloc[-2] > data.Lower.iloc[-2]) and \
                        (data.close.iloc[-2] > data.open.iloc[-2]) and \
                        (data.open.iloc[-2] < data.Lower.iloc[-2]) and \
                        (data.close.iloc[-2] < data.Middle.iloc[-2]) and \
                        (data.open.iloc[-2] < data.Lower.iloc[-2] - 100) and \
                        (abs(data.close.iloc[-2]-data.open.iloc[-2]) > 600) and \
                        (abs(data.open.iloc[-3]-data.close.iloc[-3]) > 1100) 
            sell = (data.close.iloc[-3] > data.Upper.iloc[-3]) and \
                        (data.close.iloc[-3] > data.open.iloc[-3]) and \
                        (data.close.iloc[-2] < data.Upper.iloc[-2]) and \
                        (data.close.iloc[-2] < data.open.iloc[-2]) and \
                        (data.open.iloc[-2] > data.Upper.iloc[-2]) and \
                        (data.close.iloc[-2] > data.Middle.iloc[-2]) and \
                        (data.open.iloc[-2] > data.Upper.iloc[-2] + 100) and \
                        (abs(data.close.iloc[-2]-data.open.iloc[-2])>600) and \
                        (abs(data.open.iloc[-3]-data.close.iloc[-3])>1100) 
            
            if buy == True or sell == True:
                status = True
            return buy,sell,status
        else:
            #اگر پوزیشن قبلی خرید بوده
            if preBuy == True:
                #اگر به باند بالایی رسیدی پوزیشن خرید رو ببند یا در حقیقت بفروش چیزهایی که خریدی در باند پایین
                if data.close.iloc[-2] > data.Upper.iloc[-2] :
                    return False,True,False
                else:
                    return True,False,True
            elif preSell == True:
                #اگر به باند پایینی رسیدی پوزیشن فروش رو ببند
                if data.close.iloc[-2] < data.Lower.iloc[-2]:
                    return True,False,False
                else:
                    return False,True,True 
    
    
def BB_Half(symbol, preBuy, preSell, status, movingAverage=15, coef=2):
    number_of_data = movingAverage + 25
    try:
        data = Meta.GetRates(symbol, number_of_data , timeFrame=mt5.TIMEFRAME_H4)
    except BaseException as e:
        print(f"An exception has occurred in TraderBot.BB_Half GetRates: {str(e)}")
        return False, False, False
    else:
        data["Middle"] = data["close"].rolling(int(movingAverage)).mean()
        data.dropna(inplace=True)
        data["Lower"] = data["Middle"] - coef * data["close"].rolling(movingAverage).std()
        data["Upper"] = data["Middle"] + coef * data["close"].rolling(movingAverage).std()
        data.dropna(inplace=True)
        data["distance"]=data["close"]-data["Middle"]

        if status == False:
            # به دست آوردن بازار رنج، اگر تفاوت خط میانی از روز قبلش و همچنین تفاوت خط میانی روز قبل از روز قبل ترش
            # از نود کمتر باشه میشه گفت که بازار یک بازار رنج هستش
            lags = 2
            for lag in range(1 , lags + 1):
                col = "lag{}".format(lag)
                data[col] = data.Middle.shift(lag)
            data.dropna(inplace = True)

            data["slope1"] = abs(data.Middle-data.lag1)
            data["slope2"] = abs(data.lag1-data.lag2)

            slope = 80

                    # (data.open.iloc[-2] < data.Lower.iloc[-2]) and \
            buy = (data.close.iloc[-3] < data.Lower.iloc[-3]) and \
                    (data.close.iloc[-3] < data.open.iloc[-3]) and \
                    (data.open.iloc[-3] > data.Lower.iloc[-3]) and \
                    (data.close.iloc[-2] > data.open.iloc[-2]) and \
                    (data.slope1.iloc[-2] < slope) and \
                    (data.slope2.iloc[-2] < slope) and \
                    (data.close.iloc[-2] > data.Lower.iloc[-2]) and \
                    (data.close.iloc[-2] < data.Middle.iloc[-2]) # کندل استیک هایی که یکدفعه صعود می کنن از باند پایینی به بالای باند میانی
                        # (data.open.iloc[-2] > data.Upper.iloc[-2]) and \
            sell = (data.close.iloc[-3] > data.Upper.iloc[-3]) and \
                        (data.close.iloc[-3] > data.open.iloc[-3]) and \
                        (data.open.iloc[-3] < data.Upper.iloc[-3]) and \
                        (data.close.iloc[-2] < data.open.iloc[-2]) and \
                        (data.slope1.iloc[-2] < slope) and \
                        (data.slope2.iloc[-2] < slope) and \
                        (data.close.iloc[-2] < data.Upper.iloc[-2]) and \
                        (data.close.iloc[-2] > data.Middle.iloc[-2]) # کندل استیک هایی که یکدفعه نزول می کنن از باند بالایی به زیر باند میانی
            if buy == True or sell == True:
                status = True
            return buy, sell, status
        else:
            # چک کردن اینکه به باند وسط رسیدیم            
            close = data.distance.iloc[-2] * data.distance.iloc[-3] < 0
            # اگر پوزیشن قبلی خرید بوده
            if preBuy == True:
                #اگر به باند وسط رسیدی پوزیشن خرید رو ببند یا در حقیقت بفروش چیزهایی که خریدی در باند پایین
                if close :
                    return False,True,False
                else:
                    return True,False,True
            elif preSell == True:
                #اگر به باند وسط رسیدی پوزیشن فروش رو ببند
                if close:
                    return True,False,False
                else:
                    return False,True,True 

def HA_RSI_CE_EMA(symbol, preBuy, preSell, status, rsiLength=7, haRsiLength=15, upper=66, lower=28, atrPeriod=4, atrMultiplier=3):
    number_of_data = haRsiLength + 375
    try:
        data = Meta.GetRates(symbol, number_of_data , timeFrame=mt5.TIMEFRAME_M1)
    except BaseException as e:
        print(f"An exception has occurred in TraderBot.HA_RSI_CE_EMA GetRates: {str(e)}")
        return preBuy, preSell, status
    else:    
        # محاسبه آر اس آی با طول دیگر به عنوان شاخص خروج از پوزیشن
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
            # data['rsiy'] = ta.momentum.RSIIndicator(data["close"], window=25).rsi()
            # data['rsiw'] = ta.momentum.RSIIndicator(data["close"], window=100).rsi()
            data.dropna(inplace=True)

                    # (data.hclose.iloc[-3] > lowerExtreme) and \
                    # (data.rsiy.iloc[-2] > data.rsiw.iloc[-2]) and \
                    # data['enter_long'].iloc[-2] == 1
            buy = (data.hclose.iloc[-3] < lower) and \
                    (data.hclose.iloc[-3] < data.hopen.iloc[-3]) and \
                    (data.hclose.iloc[-2] > data.hopen.iloc[-2]) and \
                    (data.close.iloc[-2] > data.ema.iloc[-2]) and \
                    (data['ce'].iloc[-2] == 1)
            
                    #(data.hclose.iloc[-3] < upperExtreme) and \
                    # (data.rsiy.iloc[-2] < data.rsiw.iloc[-2]) and \
                    # data['enter_short'].iloc[-2] == 1
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

def CE_ZLSMA(symbol, preBuy, preSell, status, atrPeriod=3, atrMultiplier=1.95,zlsmaLength=33,risk=1,reward=2):
    global supportList, resistanceList
    number_of_data = zlsmaLength + 40
    vartp=0
    varsl=0
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

            # BollingerBands
            BB = pdta.bbands(data.close, length=15, std=2.0)
            data=data.join(BB)

            data.dropna(inplace=True)

            price = round(data.open.iloc[-1],-3)
            # چک کردن اینکه پوزیشن خرید در سطح مقاومت نباشد
            priceNotInResistance = (price not in (resistanceList))
            
            # چک کردن اینکه پوزیشن فروش در سطح حمایت نباشد
            priceNotInSupport = (price not in (supportList))

            buy = (data['enter_long'].iloc[-2] == 1) and \
                    (data.hclose.iloc[-2] > data.hopen.iloc[-2]) and \
                    (data.hclose.iloc[-2] > data.zlsma.iloc[-2]) and \
                    (data.close.iloc[-2] < data["BBU_15_2.0"].iloc[-2])
                    

            sell = (data['enter_short'].iloc[-2] == 1) and \
                    (data.hclose.iloc[-2] < data.hopen.iloc[-2]) and \
                    (data.hclose.iloc[-2] < data.zlsma.iloc[-2]) and \
                    (data.close.iloc[-2] > data["BBL_15_2.0"].iloc[-2])

            # دادن پیام مناسب بابت اینکه سیگنال خرید صادر شده
            # اما چون قیمت در ناحیه مقاومتی بوده، ربات وارد معامله نشده
            if priceNotInResistance == False and buy == True:
                print(f"CE_ZLSMA: Buy is true, However, The buy price ({price}) for {symbol} is in resistance list.")
                buy = False

            if priceNotInSupport == False and sell == True:
                print(f"CE_ZLSMA: Sell is true, However, The sell price ({price}) for {symbol} is in support list.")
                sell = False
            
            if buy == True or sell == True:
                status=True
                data['atr'] = pdta.atr(data.high, data.low, data.close, length=7)
                varsl = 1 * data.atr.iloc[-1]
                vartp = 2.1 * varsl
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

#####################################################################################################
accountInfo = mt5.account_info()
print("-"*75)
print(f"Login: {accountInfo.login} \tserver: {accountInfo.server} \tleverage: {accountInfo.leverage}")
print(f"Balance: {accountInfo.balance} \tEquity: {accountInfo.equity} \tProfit: {accountInfo.profit}")
print(f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
print("-"*75)

# لیست سطوح مقاومتی و حمایتی برای اولین بار مقداردهی شود
UpdateSupportResistance()

#برای فارکس
# launching = [[0 , "22:58:30"],#0=monday
#              [1 , "00:25:30"]
#             ]

#برای تایم فریم ۴ ساعته
# در متاتریدر ملاک ساعت روسیه است برای همین تمام تایم ها دو ساعت
# جابجا شدند
launching = ["22:10",
             "02:00",
             "06:00",
             "10:00",
             "14:00",
             "18:00"]      

# سه دقیقه اختلاف به این خاطر است که اگر لانچ اول موفق نبود
# در تایم اوت بعدی مقادیر لیست ها به روز شوند
supportResistanceLaunching = ["01:40",
                              "01:43",
                              "13:40",
                              "13:43"]      


symbols_list = {
    "BITCOIN": ["BITCOIN", 0.01],
   }

counter = 0

#برای زمانی که چند تا دارایی رو خواستی اضافه کنی باید این مقادیر پیش فرض
#داخل یک دیکشنری و برای هر دارایی مقدار بگیرند

# برای استراتژی بولینجر فروش در خط بالا و خرید در پایین
buy_full = False
sell_full = False
# برای سیگنال بستن پوزیشن از این متغیر استفاده می شود
statusBB_Full = False

#برای استراتژی بولینجر فروش در خط میانی
buy_half= False
sell_half= False
#برای سیگنال بستن پوزیشن بولینجر
statusBB_Half=False

# سیگنال خرید و فروش هینکن اشی
buyHA = False
sellHA = False
statusHA = False

# سیگنال خرید و فروش شندلر
buyCE =False
sellCE = False
statusCE = False

while True:

    if internet() == True:
        
        Meta.TrailingStopLoss([3])
        Meta.VerifyTSL([3])

        #برای بررسی اینکه وقت این شده که ربات وارد بازار شود        
        # برای فارکس
        # current_time = [datetime.now().weekday(), datetime.now().strftime("%H:%M:%S")]
        #برای تایم فریم ۴ ساعته
        current_time = datetime.now(timezone.utc).strftime("%H:%M")
        if current_time in launching:  
            is_time = True
        else:
            is_time = False
        
        # به روزرسانی حمایت و مقاومت ها در ساعات مشخص شده
        if current_time in supportResistanceLaunching:
            UpdateSupportResistance()

        # برای مواقعی که نیاز به بررسی شرط ساعت و روز ورود لازم نیست
        #is_time=True 

        # برای تایم فریم های خاص مثال چهار ساعته برای بولینجرها    
        if is_time:
            print(f"Watch Dog :) {current_time}")
            Meta.TrailingStopLoss([1,2,4])
            Meta.VerifyTSL([1,2,4])

            # تک تک رمز ارزهای لیست سیمبل ها بررسی می شوند با استراتژی های مدنظر
            for asset in symbols_list.keys():
                symbol = symbols_list[asset][0]
                lot = symbols_list[asset][1]


                # Attempt to enable the symbol in the Meta MarketWatch
                # تلاش برای فعال سازی سیمبل در مارکت واتچ متاتریدر
                selected = mt5.symbol_select(symbol)
                if not selected:
                    print(f"\nERROR - Failed to select '{symbol}' in MetaTrader 5 with error :",mt5.last_error())                
                else:     
                    resume = Meta.resume()
                    # اگر استراتژی بولینجر تا حد باند وسطی فعال نبود
                    if buy_half==False and sell_half==False:
                        if resume.shape[0] > 0:
                            row = resume.loc[(resume["symbol"] == symbol) & (resume["magic"] == 1)]                        
                            # در صورتی که استاپ لاس یک پوزیشن بخوره
                            # باید وضعیت به حالت اولیه برای سفارش گذاری برگرده
                            if row.empty and statusBB_Full==True:
                                statusBB_Full=False
                                print(f"BB_Full {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")
                            elif not row.empty and statusBB_Full==False:
                                print("Abnormally position: you have an open position with Bollinger Full strategy but the statusBB_Full key is False!!")
                        elif statusBB_Full == True:
                            statusBB_Full=False
                            print(f"BB_Full {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")
                        buy_full, sell_full, statusBB_Full = BB_Full(symbol, buy_full, sell_full, statusBB_Full)
                        Meta.run(symbol, buy_full, sell_full, lot, 1.3, 0.65, 1)
                    # اگر استراتژی بولینجر کامل، فعال نبود
                    if buy_full == False and sell_full==False and statusBB_Full == False:
                        if resume.shape[0] > 0:
                            row = resume.loc[(resume["symbol"] == symbol) & (resume["magic"] == 2)]
                            # در صورتی که استاپ لاس یک پوزیشن بخوره
                            # باید وضعیت به حالت اولیه برای سفارش گذاری برگرده
                            if row.empty and statusBB_Half==True:
                                statusBB_Half=False
                                print(f"BB_Half {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")
                            elif not row.empty and statusBB_Half==False:
                                print("Abnormally position: you have an open position with Bollinger Half strategy but the statusBB_Half key is False!!")
                        elif statusBB_Half == True:   
                            statusBB_Half=False                        
                            print(f"BB_Half {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")
                        buy_half, sell_half, statusBB_Half = BB_Half(symbol, buy_half, sell_half, statusBB_Half)
                        Meta.run(symbol, buy_half, sell_half, lot, 1.2, 0.6, 2)

                    #CE_ZLSMA
                    if resume.shape[0] > 0:
                        row = resume.loc[(resume["symbol"] == symbol) & (resume["magic"] == 4)]
                        # در صورتی که استاپ لاس یک پوزیشن بخوره
                        # باید وضعیت به حالت اولیه برای سفارش گذاری برگرده
                        if row.empty and statusCE==True:
                            statusCE=False
                            print(f"CE_ZLSMA {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")
                        elif not row.empty and statusCE==False:
                            print("Abnormally position: you have an open position with CE_ZLSMA strategy but the statusCE key is False!!")
                    elif statusCE == True:   
                        statusCE=False                        
                        print(f"CE_ZLSMA {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")
                    buyCE, sellCE, statusCE, varsl, vartp = CE_ZLSMA(symbol, buyCE, sellCE, statusCE)
                    Meta.run(symbol, buyCE, sellCE, lot, vartp, varsl, 4)
            # حلقه اصلی هر ۱۰ ثانیه برای تریلینگ ران میشه برای اینکه دو سیگنال
            # تکراری برای یک موقعیت در بولینجر و شندلر ثبت نکنیم باید مجموع یک دقیقه
            # صبر شود تا مجدد وارد بولینجر و یا شندلر نشویم                    
            time.sleep(50)    

        # Heikin Ashi
        for asset in symbols_list.keys():
            symbol = symbols_list[asset][0]
            lot = symbols_list[asset][1]

            selected = mt5.symbol_select(symbol)
            if not selected:
                print(f"\nERROR - Failed to select '{symbol}' in MetaTrader 5 with error :",mt5.last_error())                
            else:         
                resume = Meta.resume()
                if resume.shape[0] > 0:
                    row = resume.loc[(resume["symbol"] == symbol) & (resume["magic"] == 3)]
                    # در صورتی که استاپ لاس یک پوزیشن بخوره
                    # باید وضعیت به حالت اولیه برای سفارش گذاری برگرده
                    if row.empty and statusHA == True:
                        statusHA=False
                        print(f"HA_RSI_CE_EMA {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")
                        # حلقه اصلی هر ۱۰ ثانیه اجرا می شود بنابراین اگر در 
                        # موقعیتی استاپ لاس خورد دوباره در همان موقعیت نباید
                        # پوزیشن قبلی مجدد باز شود
                        time.sleep(60)
                    elif not row.empty and statusHA == False:
                        print("Abnormally position: you have a open position with Heikin Ashi strategy but the statusHA key is False!!")
                elif statusHA == True:
                    statusHA=False
                    print(f"HA_RSI_CE_EMA {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")
                    time.sleep(60)

                buyHA,sellHA,statusHA=HA_RSI_CE_EMA(symbol, buyHA, sellHA, statusHA)
                Meta.run(symbol, buyHA, sellHA, lot, 0.12, 0.06, 3)  

    # سیگنال زنده بودن ربات                
    # counter += 1          
    # print(f"{':' if counter % 2 == 0 else '.'}",end='')
    # sys.stdout.flush()

    time.sleep(10)
