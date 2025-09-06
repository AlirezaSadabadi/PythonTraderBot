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


import hashlib
import json
import time
import hmac
from urllib.parse import urlparse, urlencode
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
from colorama import init as colorama_init
from colorama import Fore
from colorama import Style
import time
import csv
import requests

accessId_secertKey = dict()
with open('access_id_secret_key.csv') as f:
    reader = csv.reader(f)
    for row in reader:
        accessId_secertKey[row[0]]=row[1]

access_id = accessId_secertKey['access_id']
secret_key = accessId_secertKey['secret_key']


class RequestsClient(object):
    HEADERS = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
        "X-COINEX-KEY": "",
        "X-COINEX-SIGN": "",
        "X-COINEX-TIMESTAMP": "",
    }

    def __init__(self):
        self.access_id = access_id
        self.secret_key = secret_key
        self.url = "https://api.coinex.com/v2"
        self.headers = self.HEADERS.copy()

    # Generate your signature string
    def gen_sign(self, method, request_path, body, timestamp):
        prepared_str = f"{method}{request_path}{body}{timestamp}"
        signature = hmac.new(
            bytes(self.secret_key, 'latin-1'), 
            msg=bytes(prepared_str, 'latin-1'), 
            digestmod=hashlib.sha256
        ).hexdigest().lower()
        return signature

    def get_common_headers(self, signed_str, timestamp):
        headers = self.HEADERS.copy()
        headers["X-COINEX-KEY"] = self.access_id
        headers["X-COINEX-SIGN"] = signed_str
        headers["X-COINEX-TIMESTAMP"] = timestamp
        headers["Content-Type"] = "application/json; charset=utf-8"
        return headers

    def request(self, method, url, params={}, data=""):
        req = urlparse(url)
        request_path = req.path

        timestamp = str(int(time.time() * 1000))
        if method.upper() == "GET":
            # If params exist, query string needs to be added to the request path
            if params:
                for item in params:
                    if params[item] is None:
                        del params[item]
                        continue
                request_path = request_path + "?" + urlencode(params)

            signed_str = self.gen_sign(
                method, request_path, body="", timestamp=timestamp
            )
            response = requests.get(
                url,
                params=params,
                headers=self.get_common_headers(signed_str, timestamp)
                #proxies={'https':'http://127.0.0.1:1090'}
            )

        else:
            signed_str = self.gen_sign(
                method, request_path, body=data, timestamp=timestamp
            )
            response = requests.post(
                url, data, headers=self.get_common_headers(signed_str, timestamp)
                #proxies={'https':'http://127.0.0.1:1090'}
            )

        if response.status_code != 200:
            raise ValueError(response.text)
        return response


request_client = RequestsClient()

class Coinex():

    summary=None
    minPrice={}
    maxPrice={}

    def GetRates(symbol="BTCUSDT", number_of_data = 1000, timeFrame='1min'):
        request_path = "/futures/kline"
        params = {"market": symbol,
                  "limit": number_of_data,
                  "period": timeFrame}
        response = request_client.request(
            "GET",
            "{url}{request_path}".format(url=request_client.url, request_path=request_path),
            params=params,
        )

        resJson = response.json()
        df = pd.DataFrame()
        if resJson['code'] == 0:
            df = pd.DataFrame(resJson['data'])
            df["time"] = pd.to_datetime(df["created_at"], unit="ms")    
            df = df.set_index("time")  
            df["close"] = pd.to_numeric(df["close"], downcast="float")
            df["open"] = pd.to_numeric(df["open"], downcast="float")
            df["high"] = pd.to_numeric(df["high"], downcast="float")
            df["low"] = pd.to_numeric(df["low"], downcast="float")
        else:
            print(f"The response has an error in GetRates {resJson}")  
        return df
    
    def AccountInfo():
        request_path = "/account/info"
        response = request_client.request(
            "GET",
            "{url}{request_path}".format(url=request_client.url, request_path=request_path),            
        )

        resJson = response.json()
        if resJson['code'] == 0:
            return resJson['data']['user_id']    
        else:
            print(f"The response has an error in AccountInfo {resJson}") 

    def BalanceInfo():
        request_path = "/assets/futures/balance"
        response = request_client.request(
            "GET",
            "{url}{request_path}".format(url=request_client.url, request_path=request_path),            
        )

        resJson = response.json()
        if resJson['code'] == 0:
            return resJson['data']    
        else:
            print(f"The response has an error in BalanceInfo {resJson}") 

    def GetCurrentPrice(symbol='BTCUSDT'):
        request_path = "/futures/ticker"
        params = {"market": symbol}
        response = request_client.request(
            "GET",
            "{url}{request_path}".format(url=request_client.url, request_path=request_path),
            params=params,
        )

        resJson = response.json()
        if resJson['code'] == 0:
            return float(resJson['data'][0]['last'])
        else:
            print(f"The response has an error in GetCurrentPrice {resJson}")  

    def resume(market_type='FUTURES', page=1, limit=100):
        request_path = "/futures/pending-position"
        summary = pd.DataFrame()
        params = {"market_type": market_type,
                  "page": page,
                  "limit": limit}
        try:
            response = request_client.request(
                "GET",
                "{url}{request_path}".format(url=request_client.url, request_path=request_path),
                params=params,
            )
            resJson = response.json()
            if resJson['code'] == 0: 
                # اگر داده ای برگشت آنگاه فرآیند را ادامه بده
                if resJson['data']:
                    """ پوزیشن های جاری را بر می گرداند. پوزیشن صفر پوزیشن خرید می باشد """            
                    positionsList = pd.DataFrame(resJson['data'])
                    summary = positionsList.loc[:,['position_id','market','take_profit_price','stop_loss_price','side','avg_entry_price']]
                    summary['position'] = np.where(summary['side'] == 'short', 1 , np.nan)
                    summary['position'] = np.where(summary['side'] == 'long' , 0 , summary['position'])
                    summary['position'].fillna(2)
                    summary.rename(columns={'position_id':'ticket','market':'symbol', 'take_profit_price':'tp', 'stop_loss_price':'sl', 'avg_entry_price':'price'},inplace=True)
            else:
                print(f"The response has an error in resume {resJson}")  
        except BaseException as e:
            print(f"Error in Coinex.resume: {str(e)}") 
        return summary
            
    def TrailingStopLoss():
        Coinex.summary = Coinex.resume()
        if Coinex.summary.shape[0] >0:
            for i in range(Coinex.summary.shape[0]):
                difference = 0
                row = Coinex.summary.iloc[i]
                symbol = row["symbol"]               
                """ تغییر پویای استاپ لاس برای سفارش های خرید """
                if row["position"] == 0:
                    try:
                        if (symbol not in Coinex.maxPrice.keys()):
                            Coinex.maxPrice[symbol]=float(row["price"])
                        current_price = Coinex.GetCurrentPrice(symbol)
                        from_sl_to_curent_price = current_price - float(row["sl"])
                        from_sl_to_max_price = Coinex.maxPrice[symbol] - float(row["sl"])
                        if current_price > Coinex.maxPrice[symbol]:
                            Coinex.maxPrice[symbol] = current_price
                        if from_sl_to_curent_price > from_sl_to_max_price:
                            difference = from_sl_to_curent_price - from_sl_to_max_price
                            
                            # point = mt5.symbol_info(symbol).point
                            information = Coinex.SetStopLoss(symbol, (float(row['sl']) + difference))
                            if information is not None:
                                information = information['data']
                                if information:
                                    print(f"Buy StopLoss Trailing\t symbol:{symbol}\t order:{information['position_id']}\t avg_entry_price:{information['avg_entry_price']}\t SL:{information['stop_loss_price']}")
                    except BaseException as e:
                        print(f"An exception has occurred in Coinex.Trailing_stop_loss buy order :{str(e)}")

                """ تغییر پویای استاپ لاس برای سفارش های فروش """
                if row["position"] == 1:
                    try:
                        if symbol not in Coinex.minPrice.keys():
                            Coinex.minPrice[symbol]=float(row["price"])
                        current_price = Coinex.GetCurrentPrice(symbol)
                        from_sl_to_curent_price = float(row["sl"]) - current_price
                        from_sl_to_min_price = float(row["sl"]) - Coinex.minPrice[symbol]
                        if current_price < Coinex.minPrice[symbol]:
                            Coinex.minPrice[symbol] = current_price
                        if from_sl_to_curent_price > from_sl_to_min_price:
                            difference = from_sl_to_curent_price - from_sl_to_min_price 
                            # point = mt5.symbol_info(symbol).point                                                        
                            information = Coinex.SetStopLoss(symbol, (float(row['sl']) - difference))
                            if information is not None:
                                information = information['data']
                                if information:
                                    print(f"Sell StopLoss Trailing\t symbol:{symbol}\t order:{information['position_id']}\t avg_entry_price:{information['avg_entry_price']}\t SL:{information['stop_loss_price']}")
                    except BaseException as e:
                        print(f"An exception has occurred in Coinex.Trailing_stop_loss sell order :{str(e)}")
                        
    def VerifyTSL():
        #print("MAX", Coinex.maxPrice)
        #print("MIN", Coinex.minPrice)
        if len(Coinex.summary)>0:
            buy_open_positions_symbols = Coinex.summary.loc[(Coinex.summary["position"]==0)]["symbol"]
            sell_open_positions_symbols = Coinex.summary.loc[(Coinex.summary["position"]==1)]["symbol"]
        else:
            buy_open_positions_symbols = []
            sell_open_positions_symbols = []
        
        # اگر یک پوزیشن خرید به صورت دستی بسته شود یا استاپ لاس آن بخورد
        # بایستی مقادیر ماکزیمم آن در دیکشنری نیز حذف گردد
        if len(Coinex.maxPrice) != len(buy_open_positions_symbols) and len(buy_open_positions_symbols) >0:
            symbol_to_delete = []

            for symbol in Coinex.maxPrice.keys():
                if symbol not in list(buy_open_positions_symbols):
                    symbol_to_delete.append(symbol)

            for symbol in symbol_to_delete:
                del Coinex.maxPrice[symbol]

                        
        if len(Coinex.minPrice) != len(sell_open_positions_symbols) and len(sell_open_positions_symbols) >0:
            symbol_to_delete = []

            for symbol in Coinex.minPrice.keys():
                if symbol not in list(sell_open_positions_symbols):
                    symbol_to_delete.append(symbol)

            for symbol in symbol_to_delete:
                del Coinex.minPrice[symbol]

        # در صورتی که لیست خرید ها خالی باشد دیکشنری ماکزیمم پاک می شود
        if len(buy_open_positions_symbols) == 0:
            Coinex.maxPrice={}

        if len(sell_open_positions_symbols) == 0:
            Coinex.minPrice={}

    def WaitUntilMarketOpen(symbol, buy, sell, amount, pct_tp=0.02, pct_sl=0.01, ticket=None, result=None, leverage = 1, timeFrame='1min'):
        sleepDic = {
                    "1min":60,
                    "3min":180,
                    "5min":300,
                    "15min":900,
                    "30min":1800,
                    "1hour":3600,
                    "2hour":7200,
                    "4hour":14400,
                    "6hour":21600,
                    "12hour":43200,
                    "1day":86400,
                    "3day":250200,
                    "1week":604800
                }
        passBecauseStopLossHit = False
        while (Coinex.MarketStatus == False and passBecauseStopLossHit == False):
            time.sleep(sleepDic[timeFrame])
            # اگر در حین صبر کردن، استاپ لاس سفارش بخوره دیگر نیاز نیست سفارش را ببندیم    
            resume = Coinex.resume()
            if resume.shape[0] > 0:
                try:
                    row = resume.loc[(resume["symbol"] == symbol)]
                    if not row.empty:
                        result = Coinex.SendOrder(symbol, amount, buy, sell, ticket=ticket,pct_tp=pct_tp, pct_sl=pct_sl, leverage=leverage)
                    else:
                        passBecauseStopLossHit = True
                except BaseException as e:
                    print(f"An exception has occurred in Coinex.run close buy position: {str(e)}")
            else:
                passBecauseStopLossHit = True

        return result, passBecauseStopLossHit
        
    def RiskReward(symbol='BITCOIN', buy=True, risk=0.01, reward=0.02, leverage=1):    
        try:    
            price = Coinex.GetCurrentPrice(symbol)
            decimalCount = str(price)[::-1].find(".")
            varDown = risk/leverage
            varUp = reward/leverage
            if buy:
                price = Coinex.GetCurrentPrice(symbol)
                price_varDown = varDown * price
                price_varUp = varUp * price                    
                tp = np.round(price + price_varUp, decimalCount)
                sl = np.round(price - price_varDown, decimalCount)            
            else:                
                price = Coinex.GetCurrentPrice(symbol)
                price_varDown = varDown * price
                price_varUp = varUp * price                    
                tp = np.round(price - price_varUp, decimalCount)
                sl = np.round(price + price_varDown, decimalCount)
        except BaseException as e:
            print(f"An exception has occurred in Coinex.RiskReward: {str(e)}")
            return 0, 0
        else:
            return tp, sl
    
    def PlaceOrder(data):
        request_path = '/futures/order'
        data = json.dumps(data)
        response = request_client.request(
            "POST",
            "{url}{request_path}".format(url=request_client.url, request_path=request_path),
            data=data,
        )    
        
        return response.json()
    
    def ClosePosition(data):
        request_path = '/futures/close-position'
        data = json.dumps(data)
        response = request_client.request(
            "POST",
            "{url}{request_path}".format(url=request_client.url, request_path=request_path),
            data=data,
        )    
        
        return response.json()
    
    def SetStopLoss(symbol, sl_price):
        request_path = '/futures/set-position-stop-loss'
        data={
            "market": symbol,
            "market_type": "FUTURES",
            "stop_loss_type": "latest_price",
            "stop_loss_price": str(sl_price)
        }
        data = json.dumps(data)
        response = request_client.request(
            "POST",
            "{url}{request_path}".format(url=request_client.url, request_path=request_path),
            data=data,
        )
        resJson = response.json()
        if resJson['code'] != 0:
            print(f'Set stop loss has an error {resJson}!')
        return resJson
    
    def SetTakeProfit(symbol, tp_price):
        request_path = '/futures/set-position-take-profit'
        data={
            "market": symbol,
            "market_type": "FUTURES",
            "take_profit_type": "latest_price",
            "take_profit_price": str(tp_price)
        }
        data = json.dumps(data)
        response = request_client.request(
            "POST",
            "{url}{request_path}".format(url=request_client.url, request_path=request_path),
            data=data,
        )
        resJson = response.json()
        if resJson['code'] != 0:
            print(f'Set take profit has an error {resJson}!')
        return resJson

    def SendOrder(symbol, amount, buy, sell, ticket=None, pct_tp=0.02, pct_sl=0.01, leverage=1):    

        #OPEN A buy TRADE
        if buy and ticket==None:
            try:
                request = {
                "market": symbol,
                "market_type": 'FUTURES',
                "side": 'buy',
                "type": 'market',               
                "amount": amount,
                "is_hide": True
                }

                result = Coinex.PlaceOrder(request)

                if result['code'] == 0 and result['message'] == 'OK':
                    tp, sl = Coinex.RiskReward(symbol, buy=True, risk=pct_sl, reward=pct_tp,leverage=leverage)            
                    info_sl = Coinex.SetStopLoss(symbol, sl)
                    info_tp = Coinex.SetTakeProfit(symbol, tp)
                    if (info_sl is not None and info_tp is not None):
                        if info_sl['data'] and info_tp['data']:
                            print('-'*75)
                            print(f"SL: {info_sl['data']['stop_loss_price']}\t TP: {info_tp['data']['take_profit_price']}")

            except BaseException as e:
                print(f"An exception has occurred in Coinex.SendOrder open a buy trade: {str(e)}")
                result = None

            return result

        #OPEN A sell TRADE        
        if sell and ticket==None:
            try:
                request = {
                "market": symbol,
                "market_type": 'FUTURES',
                "side": 'sell',
                "type": 'market',               
                "amount": amount,
                "is_hide": True
                }

                result = Coinex.PlaceOrder(request)

                if result['code'] == 0 and result['message'] == 'OK':
                    tp, sl = Coinex.RiskReward(symbol, buy=False, risk=pct_sl, reward=pct_tp)
                    info_sl = Coinex.SetStopLoss(symbol, sl)
                    info_tp = Coinex.SetTakeProfit(symbol, tp)
                    if (info_sl is not None and info_tp is not None):
                        if info_sl['data'] and info_tp['data']:
                            print("-"*75)
                            print(f"SL: {info_sl['data']['stop_loss_price']}\t TP: {info_tp['data']['take_profit_price']}")

            except BaseException as e:
                print(f"An exception has occurred in Coinex.SendOrder open a sell trade: {str(e)}")
                result = None
            return result
        
        
        #CLOSE A buy TRADE
        if buy and ticket!=None:
            try:
                request = {
                    "market": symbol,
                    "market_type": "FUTURES",
                    "type": "market"
                }
            
                result = Coinex.ClosePosition(request)
            except BaseException as e:
                print(f"An exception has occurred in Coinex.SendOrder close a buy trade: {str(e)}")
                result = None

            return result

        #CLOSE A sell TRADE    
        if sell and ticket!=None:
            try:
                request = {
                    "market": symbol,
                    "market_type": "FUTURES",
                    "type": "market"
                }
            
                result = Coinex.ClosePosition(request)
            except BaseException as e:
                print(f"An exception has occurred in Coinex.SendOrder close a sell trade: {str(e)}")
                result = None

            return result
        
    def MarketStatus(symbol='BTCUSDT'):
        request_path = "/futures/market"
        params = {"market":symbol}

        response = request_client.request(
            "GET",
            "{url}{request_path}".format(url=request_client.url, request_path=request_path),
            params=params,
        )
        resJson = response.json()
        if resJson['code'] == 0:
            return resJson['data'][0]['is_market_available']    
        else:
            print(f"The response has an error in MarketStatus {resJson}") 
        
    def run(symbol, buy, sell, amount, pct_tp=0.02, pct_sl=0.01, leverage = 1, timeFrame='1min'):

        if buy == True or sell ==True:
            resume = Coinex.resume()
            if resume.shape[0] > 0:
                    try:
                        row = resume.loc[(resume["symbol"] == symbol)]
                        if row.empty:
                            position = None
                            ticket = None
                        else:
                            position = row.values[0][6]
                            ticket = row.values[0][0]
                    except BaseException as e:
                        print(f"An exception has occurred in Coinex.run: {str(e)}")
            else:
                position = None
                ticket = None
            
            # برای بررسی بسته بودن بازار و چاپ پیام مناسب
            marketClosed = False
            # اگر قبل از بستن پوزیشن، استاپ لاس بخوره باید از حلقه صبر برای باز شدن بازار خارج شد
            passBecauseStopLossHit = False

            # سفارش تکراری خرید در یک استراتژی انجام نده
            if buy == True and position == 0:
                buy = False
                
            # اگر سفارش خرید داشتی و الان باید ببندیش                
            elif buy == False and position == 0:
                result = Coinex.SendOrder(symbol, amount, True, False, ticket=ticket,pct_tp=pct_tp, pct_sl=pct_sl, leverage=leverage)
                
                # درصورتی که بازار بسته بشه بایستی صبر کرد تا زمانی که بازار باز شود و سفارش را ببندیم
                if Coinex.MarketStatus(symbol)==False and result['message'] != "OK":
                    print("Market closed!")
                    marketClosed = True
                    result, passBecauseStopLossHit = Coinex.WaitUntilMarketOpen(symbol, True, False, amount, pct_tp, pct_sl, ticket, result, leverage, timeFrame)                
                if (marketClosed and passBecauseStopLossHit == False):
                    print("Market open!")
                    marketClosed = False
                if passBecauseStopLossHit:
                    print(f"I try to close a buy trade but stoploss hit! market maybe close or open!")
                    passBecauseStopLossHit = False

                if result is not None:
                    if result['code'] == 0:
                        print("-"*75)
                        print("Date: ", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "\tSYMBOL:", symbol)
                        print(f"{Fore.LIGHTCYAN_EX}CLOSE {Style.RESET_ALL}BUY POSITION: {result['message']}")
                        if result['message'] != "OK":
                            print("WARNINGS", result['message'])
                        print("-"*75)   
                    else:
                        print(f"{Fore.YELLOW}Warning: {Style.RESET_ALL}The close buy SendOrder result for has an error: {result}!")
                
            elif sell == True and position == 1:
                sell = False
                
            elif sell == False and position == 1:
                result = Coinex.SendOrder(symbol, amount, False, True, ticket=ticket,pct_tp=pct_tp, pct_sl=pct_sl, leverage=leverage)

                # درصورتی که بازار بسته بشه بایستی صبر کرد تا زمانی که بازار باز شود و سفارش را ببندیم
                if Coinex.MarketStatus(symbol) == False:
                    print("Market closed!")
                    marketClosed = True
                    result, passBecauseStopLossHit = Coinex.WaitUntilMarketOpen(symbol, False, True, amount, pct_tp, pct_sl, ticket, result, leverage, timeFrame)                
                if (marketClosed and passBecauseStopLossHit == False):
                    print("Market open!")
                    marketClosed = False
                if passBecauseStopLossHit:
                    print(f"I try to close a buy trade but stoploss hit! market maybe close or open!")
                    passBecauseStopLossHit = False
                if result is not None:
                    if result['code'] == 0:
                        print("-"*75)
                        print("Date: ", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "\tSYMBOL:", symbol)
                        print(f"{Fore.LIGHTCYAN_EX}CLOSE {Style.RESET_ALL}SELL POSITION: {result['message']}")
                        
                        if result['message'] != "OK":
                            print("WARNINGS", result['message'])                   
                        print("-"*75)
                    else:
                        print(f"{Fore.YELLOW}Warning: {Style.RESET_ALL}The close sell SendOrder result for has an error {result}!")

            elif buy == True:
                result =  Coinex.SendOrder(symbol, amount, True, False, ticket=None,pct_tp=pct_tp, pct_sl=pct_sl, leverage=leverage)
                if result is not None:
                    if result['code'] == 0:
                        print("-"*75)
                        print("Date: ", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "\tSYMBOL:", symbol)
                        print(f"{Fore.GREEN if buy == True else Fore.WHITE}BUY: {buy} \t  {Fore.RED if sell == True else Fore.WHITE}SELL: {sell} {Style.RESET_ALL}")
                        print(f"OPEN BUY POSITION: {result['message']}")
                        print(f"price: {result['data']['last_filled_price']}")
                        if result['message'] != "OK":
                            print("WARNINGS", result['message'])
                        print("-"*75)
                    else:
                        print(f"{Fore.YELLOW}Warning: {Style.RESET_ALL}The open buy SendOrder result has an error {result}!")

            elif sell == True:
                result = Coinex.SendOrder(symbol, amount, False, True, ticket=None,pct_tp=pct_tp, pct_sl=pct_sl, leverage=leverage)
                if result is not None:
                    if result['code'] == 0:
                        print("-"*75)
                        print("Date: ", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "\tSYMBOL:", symbol)
                        print(f"{Fore.GREEN if buy == True else Fore.WHITE}BUY: {buy} \t  {Fore.RED if sell == True else Fore.WHITE}SELL: {sell} {Style.RESET_ALL}")
                        print(f"OPEN SELL POSITION: {result['message']}")
                        print(f"price: {result['data']['last_filled_price']}")
                        if result['message'] != "OK":
                            print("WARNINGS",  result['message'])
                        print("-"*75)
                    else:
                        print(f"{Fore.YELLOW}Warning: {Style.RESET_ALL}The open sell SendOrder result has an error {result}!")

    
    def SetLeverage(symbol='BTCUSDT', market_type='FUTURES', margin_mode='cross', leverage=10):
        request_path = "/futures/adjust-position-leverage"
        data = {"market": symbol,
                  "market_type": market_type,
                  "margin_mode": margin_mode,
                  "leverage": leverage}
        data = json.dumps(data)
        response = request_client.request(
            "POST",
            "{url}{request_path}".format(url=request_client.url, request_path=request_path),
            data=data,
        )

        resJson = response.json()
        if resJson['code'] == 0:
            print(f"The {symbol} leverage changed to {resJson['data']['leverage']} successfully")
        else:
            print(f"The response has an error in SetLeverage {resJson}")
