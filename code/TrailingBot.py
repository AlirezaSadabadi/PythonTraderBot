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
import socket
import sys
from colorama import init as colorama_init

colorama_init()
# ساخت کانکشن بین ربات و متاتریدر
if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    quit()

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

#####################################################################################################
accountInfo = mt5.account_info()
print("-"*30)
print(f"I'm Trailing Bot, Relax!")
print(f"Login: {accountInfo.login}")
print(f"server: {accountInfo.server}")
print(f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
print("-"*30)

counter = 0

while True:

    # internet connection
    # بررسی اتصال اینترنت
    if internet() == True:
        
        Meta.TrailingStopLoss()
        Meta.VerifyTSL()

    # WatchDog
    # سیگنال زنده بودن ربات                
    # counter += 1          
    # print(f"{':' if counter % 2 == 0 else '.'}",end='')
    # sys.stdout.flush()

    # هر چند ثانیه تریلینگ انجام شود
    time.sleep(10)
