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

from Helper import *
from tqdm import tqdm
import csv
from Meta import *

if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()

df = Meta.GetRates(timeFrame=mt5.TIMEFRAME_H4)
df = df.loc[:,["open","high","low","close"]]

before = 3
after = 2
support = []
resistance = []

for row in tqdm(range(before,len(df)-after)):
    if Helper.Support(df, row, before, after):
        support.append(round(df.low.iloc[row],-3))
    if Helper.Resistance(df, row, before, after):
        resistance.append(round(df.high.iloc[row],-3))

with open("support.csv", 'w', newline='') as myfile:
     wr = csv.writer(myfile, quoting=csv.QUOTE_NONNUMERIC)
     wr.writerow(support)

with open("resistance.csv", 'w', newline='') as myfile:
     wr = csv.writer(myfile, quoting=csv.QUOTE_NONNUMERIC)
     wr.writerow(resistance)
    
mt5.shutdown()

# with open('support.csv', newline='') as myfile:
#     reader = csv.reader(myfile, quoting=csv.QUOTE_NONNUMERIC)
#     supportList = list(reader)

# print(supportList[0][1])

# if '40000.0' in supportList[0]:
#     print('true')

# print(Counter(supportList[0])) 