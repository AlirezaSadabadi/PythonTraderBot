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

from datetime import datetime, timezone, timedelta
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

class Helper:
    def __init__(self) -> None:
        try:                
            # establish connection to MetaTrader 5 terminal
            if not mt5.initialize():
                print("MetaTrader initialize() failed, error code =",mt5.last_error())
        except BaseException as e:
            print(f"An exception has occurred in Meta.__init__: {str(e)}")

    # می توان قیمت مدنظر استاپ لاس را به دلار داد و ریسک را به درصد به دست آورد
    def RiskCalculation(symbol, sl):
        leverage = mt5.account_info().leverage
        price = mt5.symbol_info(symbol).ask 
        risk =np.round(((abs(price - sl) / price) * leverage) , 2)
        return risk

    '''
    Find the volume depending of your capital and MinMaxLot
    '''
    def GetLotSize(symbol, capital):
        leverage = mt5.account_info().leverage
        investedCapital = capital * leverage
        tradeSize = mt5.symbol_info(symbol).trade_contract_size
        price = (mt5.symbol_info(symbol).ask + mt5.symbol_info(symbol).bid)/2
        lotSize=investedCapital/tradeSize/price
        minLot=mt5.symbol_info(symbol).volume_min
        maxLot=mt5.symbol_info(symbol).volume_max
        if minLot<lotSize:
            number_decimal = str(minLot)[::-1].find(".")
            if number_decimal>0:
                lot_size_rounded = np.round(lotSize, number_decimal)
                if lotSize < lot_size_rounded:
                    lot_size_rounded = np.round(lot_size_rounded - minLot, number_decimal)
            else:
                number_size_lot =  len(str(minLot))
                lot_size_rounded = int(np.round(lotSize, -number_size_lot))
                if lotSize < lot_size_rounded:
                    lot_size_rounded = int(np.round(lot_size_rounded - number_size_lot, - number_size_lot))                    
            if lot_size_rounded>maxLot:
                lot_size_rounded = maxLot            
            goodLot = lot_size_rounded            
        else: 
            goodLot="Invested capital is too small to be able to place an order"
        return lotSize,minLot,maxLot,goodLot
    
    # سی سی کندل جاری است و افتر و بیفور هم تعداد کندل بعد و قبل از سی سی می باشند
    # cc is current candle, after is number of candles after the c, before is number of candle before the c
    def Support(data, cc, before, after): 
        for i in range(cc-before+1, cc+1):
            if(data.low.iloc[i]>data.low.iloc[i-1]):
                return 0
        for i in range(cc+1,cc+after+1):
            if(data.low.iloc[i]<data.low.iloc[i-1]):
                return 0
        return 1
    # سی سی کندل جاری است و افتر و بیفور هم تعداد کندل بعد و قبل از سی سی می باشند
    # cc is current candle, after is number of candles after the c, before is number of candle before the c
    def Resistance(data, cc, before, after):
        for i in range(cc-before+1, cc+1):
            if(data.high.iloc[i]<data.high.iloc[i-1]):
                return 0
        for i in range(cc+1,cc+after+1):
            if(data.high.iloc[i]>data.high.iloc[i-1]):
                return 0
        return 1
