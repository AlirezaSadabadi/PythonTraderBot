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

import json
from urllib.parse import quote
import requests

token = ''
chatId = ''
ip = '127.0.0.1'
port = '1090'
useProxy = True

class TeleBot():
    

    def __init__(self):        
        self.url = f'https://api.telegram.org/bot{token}/'
        self.proxies = {'https':f'http://{ip}:{port}'}
        self.chatId = chatId
    
    def DecodeMsg(resp):
        decoded=''
        for line in resp:
            decoded+=line.decode('utf-8')
        return decoded

    def SendMessage(self, message='empty'):
        message  = quote(str(message).encode('utf-8'))
        cmd  = 'sendMessage'    
        try:
            if useProxy:
                resp = requests.get(self.url + cmd + f'?chat_id={self.chatId}&text={message}',
                        proxies=self.proxies)
            else:
                resp = requests.get(self.url + cmd + f'?chat_id={self.chatId}&text={message}')
            # converting to utf-8
            line = TeleBot.DecodeMsg(resp)
            # converting to JSON
            check = json.loads(line)
            if check['ok']:
                print('Message Send Successfully')
            else:
                print(check['description'])
        except BaseException as e:
            print(f"An exception has occurred in TelegramBot SendMessage: {str(e)}")
