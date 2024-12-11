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
            # از هشتاد کمتر باشه میشه گفت که بازار یک بازار رنج هستش
            lags = 2
            for lag in range(1 , lags + 1):
                col = "lag{}".format(lag)
                data[col] = data.Middle.shift(lag)
            data.dropna(inplace = True)

            data["slope1"] = abs(data.Middle-data.lag1)
            data["slope2"] = abs(data.lag1-data.lag2)

            slope = 80

                    # (data.open.iloc[-2] < data.Lower.iloc[-2]) & \
            buy = (data.close.iloc[-3] < data.Lower.iloc[-3]) & \
                    (data.close.iloc[-3] < data.open.iloc[-3]) & \
                    (data.open.iloc[-3] > data.Lower.iloc[-3]) & \
                    (data.close.iloc[-2] > data.open.iloc[-2]) & \
                    (data.slope1.iloc[-2] < slope) & \
                    (data.slope2.iloc[-2] < slope) & \
                    (data.close.iloc[-2] > data.Lower.iloc[-2]) & \
                    (data.close.iloc[-2] < data.Middle.iloc[-2]) # کندل استیک هایی که یکدفعه صعود می کنن از باند پایینی به بالای باند میانی
                        # (data.open.iloc[-2] > data.Upper.iloc[-2]) & \
            sell = (data.close.iloc[-3] > data.Upper.iloc[-3]) & \
                        (data.close.iloc[-3] > data.open.iloc[-3]) & \
                        (data.open.iloc[-3] < data.Upper.iloc[-3]) & \
                        (data.close.iloc[-2] < data.open.iloc[-2]) & \
                        (data.slope1.iloc[-2] < slope) & \
                        (data.slope2.iloc[-2] < slope) & \
                        (data.close.iloc[-2] < data.Upper.iloc[-2]) & \
                        (data.close.iloc[-2] > data.Middle.iloc[-2]) # کندل استیک هایی که یکدفعه نزول می کنن از باند بالایی به زیر باند میانی
            if buy == True or sell == True:
                status = True
            return buy, sell, status
        else:
            # چک کردن اینکه به باند وسط رسیدیم            
            close = data.distance.iloc[-1] * data.distance.iloc[-2] < 0
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

    
######################################################################################
accountInfo = mt5.account_info()
print("-"*30)
print(f"I'm BB_Half trade bot, relax!")
print(f"Login: {accountInfo.login}")
print(f"server: {accountInfo.server}")
print(f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
print("-"*30)

#برای تایم فریم ۴ ساعته
# در متاتریدر ملاک ساعت روسیه است برای همین تمام تایم ها دو ساعت
# جابجا شدند
launching = ["22:00",
             "02:00",
             "06:00",
             "10:00",
             "14:00",
             "18:00"]

symbols_list = {
    "BITCOIN": ["BITCOIN", 0.01],
   }

buy = False
sell = False
status = False

while True:

    if internet() == True:
        
        Meta.TrailingStopLoss()
        Meta.VerifyTSL()

        #برای تایم فریم ۴ ساعته
        current_time = datetime.now(timezone.utc).strftime("%H:%M")
        if current_time in launching:  
            is_time = True
        else:
            is_time = False

        # برای تایم فریم های خاص مثال چهار ساعته برای بولینجرها    
        if is_time:        
            for asset in symbols_list.keys():
                symbol = symbols_list[asset][0]
                lot = symbols_list[asset][1]

                selected = mt5.symbol_select(symbol)
                if not selected:
                    print(f"\nERROR - Failed to select '{symbol}' in MetaTrader 5 with error :",mt5.last_error())                
                else:         
                    resume = Meta.resume()
                    if resume.shape[0] > 0:
                        row = resume.loc[(resume["symbol"] == symbol) & (resume["magic"] == 2)]
                        # در صورتی که استاپ لاس یک پوزیشن بخوره
                        # باید وضعیت به حالت اولیه برای سفارش گذاری برگرده
                        if row.empty and status == True:
                            status=False
                            print(f"BB_Half {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")
                            # حلقه اصلی هر ۱۰ ثانیه اجرا می شود بنابراین اگر در 
                            # موقعیتی استاپ لاس خورد دوباره در همان موقعیت نباید
                            # پوزیشن قبلی مجدد باز شود
                            time.sleep(50)
                        elif not row.empty and status == False:
                            print("Abnormally position: you have a open position with BB_Half strategy but the status key is False!!")
                    elif status == True:
                        status=False
                        print(f"BB_Half {Fore.YELLOW}StopLoss hit!{Style.RESET_ALL}")
                        time.sleep(50)

                    buy,sell,status=BB_Half(symbol, buy, sell, status)
                    Meta.run(symbol, buy, sell, lot, 1.2, 0.6, 2)

    # سیگنال زنده بودن ربات                
    # counter += 1          
    # print(f"{':' if counter % 2 == 0 else '.'}",end='')
    # sys.stdout.flush()

    
    time.sleep(10)