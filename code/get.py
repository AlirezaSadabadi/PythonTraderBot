from Meta import *

if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()

df = Meta.GetRates(timeFrame=mt5.TIMEFRAME_H4)
df.to_csv("BitcoinH4.csv")