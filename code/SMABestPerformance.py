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

from Meta import *
import pandas as pd
import numpy as np
from itertools import product
from tqdm import tqdm

df = pd.read_csv("BitcoinH4.csv", index_col='time')
df = df.loc[:,["close"]]

def SMA(fastLength, slowLength):
    data = df.copy()
    data["return"]=np.log(data.close.div(data.close.shift(1)))

    data["SMA fast"] = data["close"].rolling(fastLength).mean()
    data["SMA slow"] = data["close"].rolling(slowLength).mean()
    data.dropna(inplace=True)
    
    data["position"]=np.where(data["SMA fast"]>data["SMA slow"],1,-1)
    data["strategy"]=data["position"].shift(1) * data["return"]
    data.dropna(inplace=True)

    return np.exp(data["strategy"].sum())

####################################################
input = "sma"
print("Test start time")
current_dateTime = datetime.now()
print(current_dateTime)
print(75*"-")

combinations=list(product(range(1,301),range(1,301)))
results=[]

for combination in tqdm(combinations):
    results.append(SMA(combination[0],combination[1]))

bestCombination=combinations[np.argmax(results)]
print(75*"-")
print(f"the best combination for {input.upper()} is {bestCombination}")
columns=["SMA_FAST","SMA_SLOW"]
completeResults = pd.DataFrame(data=combinations,columns=columns)
completeResults["performance"]= results
print(75*"-")
print("top Perf results:")
print(completeResults.nlargest(10,"performance"))
print(75*"-")
print("five smallest perf results:")
print(completeResults.nsmallest(5,"performance"))

completeResults.to_csv("test.csv")

print(75*"-")
print("Test end time")
current_dateTime = datetime.now()
print(current_dateTime)