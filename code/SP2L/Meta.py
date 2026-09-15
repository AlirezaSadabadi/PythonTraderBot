from datetime import datetime, timezone, timedelta
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from colorama import init as colorama_init
from colorama import Fore
from colorama import Style
import time
from TelegramBot import TeleBot

class Meta:
    
    # برای دسترسی داشتن به پوزیشن های جاری در عملیات تریلینگ
    # Easy access to current position in trailing stop and verify TSL
    summary=None
    minPrice={}
    maxPrice={}
    # ارسال اعلان ها با تلگرام
    # Send Messages to Telegram
    teleBotMessage = False

    # Optional execution-based TP configuration. Existing method signatures
    # and the default Meta behavior remain unchanged.
    executionBasedTP = False
    executionTP_R = 1.0
    executionSignalEntry = None

    def SetExecutionBasedTP(enabled=False, tp_r=1.0, signal_entry=None):
        Meta.executionBasedTP = enabled
        Meta.executionTP_R = tp_r
        Meta.executionSignalEntry = signal_entry

    def UpdateTPAfterFill(symbol, magic, buy, sl, fallback_tp=None, max_attempts=10, delay=0.05):
        """
        Method B: keep the original TP as an immediate fallback, then
        recalculate TP from the actual filled position price and update it.

        If the position is no longer visible before the update (for example
        the original TP/SL was hit immediately), no modification is made and
        the original order TP remains in effect.
        """
        if Meta.executionBasedTP != True:
            return None

        try:
            position = None

            for _ in range(max_attempts):
                positions = mt5.positions_get(symbol=symbol)

                if positions is not None:
                    matching = [
                        pos for pos in positions
                        if int(pos.magic) == int(magic)
                    ]

                    if len(matching) > 0:
                        # The latest matching position is the one just opened.
                        position = matching[-1]
                        break

                time.sleep(delay)

            if position is None:
                print("Execution TP update skipped: position not found after fill. Original TP remains active.")
                return None

            fill_price = float(position.price_open)
            current_sl = float(position.sl) if float(position.sl) > 0 else float(sl)

            # Slippage relative to the strategy signal entry.
            # Positive value = adverse movement against the trade.
            signal_entry = Meta.executionSignalEntry
            if signal_entry is None:
                slippage = None
            else:
                signal_entry = float(signal_entry)
                if buy:
                    slippage = fill_price - signal_entry
                else:
                    slippage = signal_entry - fill_price

            if buy:
                risk_distance = fill_price - current_sl
                if risk_distance <= 0:
                    print("Execution TP update skipped: invalid BUY fill/SL distance.")
                    return None
                new_tp = fill_price + (risk_distance * Meta.executionTP_R)
            else:
                risk_distance = current_sl - fill_price
                if risk_distance <= 0:
                    print("Execution TP update skipped: invalid SELL fill/SL distance.")
                    return None
                new_tp = fill_price - (risk_distance * Meta.executionTP_R)

            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is not None:
                new_tp = round(new_tp, int(symbol_info.digits))

            filling_type = symbol_info.filling_mode if symbol_info is not None else mt5.ORDER_FILLING_RETURN

            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": symbol,
                "position": int(position.ticket),
                "sl": current_sl,
                "tp": new_tp,
                "type_filling": filling_type,
                "type_time": mt5.ORDER_TIME_GTC
            }

            result = mt5.order_send(request)

            print("========== REAL FILL TP UPDATE =========")
            print("Symbol          :", symbol)
            print("Direction       :", "BUY" if buy else "SELL")
            print("Position Ticket :", position.ticket)
            print("Signal Entry    :", "N/A" if signal_entry is None else signal_entry)
            print("Actual Fill     :", fill_price)
            print("Slippage        :", "N/A" if slippage is None else slippage)
            print("SL              :", current_sl)
            print("Old TP          :", fallback_tp)
            print("TP_R            :", Meta.executionTP_R)
            print("New TP          :", new_tp)
            print("Real Risk       :", risk_distance)
            print("Real Reward     :", abs(new_tp - fill_price))
            print("Real RR         :", abs(new_tp - fill_price) / abs(fill_price - current_sl))
            print("Update Result   :", "None" if result is None else result.comment)
            print("==========================================")

            return result

        except BaseException as e:
            exceptMessage = f"An exception has occurred in Meta.UpdateTPAfterFill: {str(e)}"
            print(exceptMessage)
            if Meta.teleBotMessage:
                TeleBot().SendMessage(exceptMessage)
            return None

    def __init__(self) -> None:
        try:                
            colorama_init()
            # establish connection to MetaTrader 5 terminal
            if not mt5.initialize():
                print("MetaTrader initialize() failed, error code =",mt5.last_error())
        except BaseException as e:
            exceptMessage = f"An exception has occurred in Meta.__init__: {str(e)}"
            print(exceptMessage)
            if Meta.teleBotMessage:
                TeleBot().SendMessage(exceptMessage)
    
    def ConvertStringToDatetime(strDate):
        year,month,day=strDate.split("/")
        isValidDate=True
        try:
            convertedStrDate = datetime(int(year),int(month),int(day))
        except:
            isValidDate=False
        if isValidDate:
            return convertedStrDate       
        else:
            print("Your fromDate is not a correct format")

    def GetRates(symbol="BITCOIN", number_of_data = 10000, timeFrame=mt5.TIMEFRAME_D1, fromDate = None):
        if fromDate is None:
            #متاتریدر در تایم روسیه است و بنابراین پارامتر فرام دیت باید دو یا سه ساعت جلوتر از
            # ساعت جهانی تنظیم شود
            # فعلا ۲ ساعت است اما قبلا ۳ ساعت اختلاف هم دیده بودم برای همین ۳ میذارم
            # که در حقیقت ۲ ساعت هم پوشش میده
            fromDate=datetime.now(timezone.utc)+timedelta(hours=3)
        if type(fromDate).__name__=='str':
            fromDate= Meta.ConvertStringToDatetime(fromDate)
        df = pd.DataFrame()
        try:
            rates = mt5.copy_rates_from(symbol, timeFrame, fromDate, number_of_data)
        except BaseException as e:
                exceptMessage = f"An exception has occurred in Meta.GetRates: {str(e)}"
                print(exceptMessage)
                if Meta.teleBotMessage:
                    TeleBot().SendMessage(exceptMessage)
        else:
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")    
            df = df.set_index("time")    
        return df
    
    def GetTicks(symbol="BITCOIN", number_of_data = 10000, fromDate=None):
        if fromDate is None:
            fromDate = datetime.now(timezone.utc)+timedelta(hours=2)
        if type(fromDate)=='str':
            fromDate= Meta.ConvertStringToDatetime(fromDate)
        df = pd.DataFrame()
        try:
            ticks = mt5.copy_ticks_from(symbol, fromDate, number_of_data,  mt5.COPY_TICKS_ALL)
        except BaseException as e:
                exceptMessage = f"An exception has occurred in Meta.GetTicks: {str(e)}"
                print(exceptMessage)
                if Meta.teleBotMessage:
                    TeleBot().SendMessage(exceptMessage)
        else:
            df = pd.DataFrame(ticks)
            df["time"] = pd.to_datetime(df["time"], unit="s")    
            df = df.set_index("time")    
        return df
    
    def FindFillingMode(symbol):
        for i in range(2):
            request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": mt5.symbol_info(symbol).volume_min,
            "type": mt5.ORDER_TYPE_BUY,
            "price": mt5.symbol_info_tick(symbol).ask,
            "type_filling": i,
            "type_time": mt5.ORDER_TIME_GTC
            }
            try:
                result = mt5.order_check(request)            
                if result.comment == "Done":
                    break
            except BaseException as e:
                exceptMessage = f"An Exception has occurred in Meta.FindFillingMode: {str(e)}"
                print(exceptMessage)
                if Meta.teleBotMessage:
                    TeleBot().SendMessage(exceptMessage)
                break

        return i
    
    def RiskReward(symbol='BITCOIN', buy=True, risk=0.01, reward=0.02):    
            try:    
                leverage = mt5.account_info().leverage
                price = mt5.symbol_info(symbol).ask            
                decimalCount = str(price)[::-1].find(".") + 2
                varDown = risk/leverage
                varUp = reward/leverage
                if buy:
                    price = mt5.symbol_info(symbol).ask              
                    price_varDown = varDown * price
                    price_varUp = varUp * price                    
                    tp = np.round(price + price_varUp, decimalCount)
                    sl = np.round(price - price_varDown, decimalCount)
                else:                
                    price = mt5.symbol_info(symbol).bid
                    price_varDown = varDown * price
                    price_varUp = varUp * price                    
                    tp = np.round(price - price_varUp, decimalCount)
                    sl = np.round(price + price_varDown, decimalCount)
                print(f"price: {price} sl:{sl} tp:{tp}")
            except BaseException as e:
                exceptMessage = f"An exception has occurred in Meta.RiskReward: {str(e)}"
                print(exceptMessage)
                if Meta.teleBotMessage:
                    TeleBot().SendMessage(exceptMessage)
                return 0, 0
            else:
                return tp, sl
    '''
    مواردی که استاپ لاس توسط مکانیزم هایی نظیر
    atr
    محاسبه می شود و فقط تفاوت حد ضرر و سود از قیمت اصلی
    ارسال می شود توسط این تابع مقدار اصلی حد ضرر محاسبه می گردد
    '''
    def StopLossTakeProfitFromVar(symbol='BITCOIN', buy=True, vartp=0, varsl=0):
        if buy:
            price = mt5.symbol_info(symbol).ask 
            tp = price + vartp
            sl = price - varsl
        else:                
            price = mt5.symbol_info(symbol).bid
            tp = price - vartp
            sl = price + varsl
        return tp, sl
               
    def PlacePendingOrder(symbol, lot, buy, sell, price, sl, tp, magic=0, comment="No specific comment"):
        try:
            filling_type = mt5.ORDER_FILLING_RETURN

            if buy:
                order_type = mt5.ORDER_TYPE_BUY_LIMIT
            elif sell:
                order_type = mt5.ORDER_TYPE_SELL_LIMIT
            else:
                print("ERROR: PlacePendingOrder requires buy=True or sell=True.")
                return None

            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": lot,
                "type": order_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 10,
                "magic": magic,
                "comment": comment,
                "type_filling": filling_type,
                "type_time": mt5.ORDER_TIME_GTC
            }

            result = mt5.order_send(request)

            if result is not None:
                print("Pending order: ", result.comment)
                if hasattr(result, "request"):
                    print(
                        "price:", result.request.price,
                        "SL:", result.request.sl,
                        "TP:", result.request.tp,
                        "magic:", magic
                    )

            return result

        except BaseException as e:
            exceptMessage = f"An exception has occurred in Meta.PlacePendingOrder: {str(e)}"
            print(exceptMessage)
            if Meta.teleBotMessage:
                TeleBot().SendMessage(exceptMessage)
            return None

    def SendOrder(symbol, lot, buy, sell, ticket=None,pct_tp=0.02, pct_sl=0.01, comment="No specific comment", magic=0, stopLossWithAtr=False, stopLossPure=False):    

        filling_type=Meta.FindFillingMode(symbol)
        #این سیاست اجرا به این معنی است که یک سفارش فقط در حجم مشخص شده قابل اجرا است.
        #در صورتی که مقدار لازم در حال حاضر در بازار موجود نباشد، دستور اجرا نخواهد شد
        #حجم مورد نظر را می توان از چندین پیشنهاد موجود تشکیل داد
        #FOK = Fill or Kill
        #filling_type = mt5.ORDER_FILLING_FOK

        #توافقی برای اجرای معامله با حداکثر حجم موجود در بازار در حجم مشخص شده در سفارش
        #در صورتی که درخواست به طور کامل پر نشود، سفارشی با حجم موجود اجرا می شود
        #و حجم باقیمانده لغو می شود
        #IOC = Immediate or Cancel
        #filling_type = mt5.ORDER_FILLING_IOC
        
        #خط مشی BOC نشان می دهد که سفارش را فقط می توان در Depth of Market (دفتر سفارش) قرار داد.
        #اگر سفارش بلافاصله پس از ثبت تکمیل شود، این سفارش لغو می شود.
        #این سیاست تضمین می کند که قیمت سفارش داده شده بدتر از بازار فعلی خواهد بود
        #BOC برای اجرای معاملات غیرفعال استفاده می‌شود: تضمین می‌شود که سفارش نمی‌تواند بلافاصله پس از ثبت اجرا شود و بنابراین بر نقدینگی جاری تأثیر نمی‌گذارد
        #این خط‌مشی پر کردن فقط برای سفارش‌های محدود و توقف پشتیبانی می‌شود
        #filling_type = mt5.ORDER_FILLING_BOC     

        #filling_type=mt5.ORDER_FILLING_RETURN

        #OPEN A buy TRADE
        if buy and ticket==None:
            # استراتژی هایی که استاپ لاس آن ها با مکانیزم نظیر
            # atr
            # محاسبه می شود به تابع دیگری ارجاع می شود
            # if magic == 5 or magic == 4 or magic == 7:
            if stopLossWithAtr == True:
                tp, sl = Meta.StopLossTakeProfitFromVar(symbol, True, pct_tp, pct_sl)
            else:
                if stopLossPure == False:
                    tp, sl = Meta.RiskReward(symbol, buy=True, risk=pct_sl, reward=pct_tp)
                else:
                    tp, sl = pct_tp, pct_sl
            
            try:
                askPrice = mt5.symbol_info_tick(symbol).ask
                print(f"askPrice:{askPrice}")

                # Method B: calculate an immediate fallback TP from the
                # pre-order quote, then recalculate TP from the actual fill
                # immediately after order_send().
                # RiskReward() is intentionally not used in this path.
                if Meta.executionBasedTP == True and stopLossPure == True:
                    risk_distance = askPrice - sl
                    if risk_distance <= 0:
                        print("ERROR: execution price is not above BUY SL; order not sent.")
                        return None
                    tp = askPrice + (risk_distance * Meta.executionTP_R)

                    signal_text = "N/A" if Meta.executionSignalEntry is None else str(Meta.executionSignalEntry)
                    slippage = None if Meta.executionSignalEntry is None else askPrice - Meta.executionSignalEntry
                    real_rr = abs(tp - askPrice) / abs(askPrice - sl)
                    print("========== EXECUTION DEBUG ==========")
                    print("Symbol          :", symbol)
                    print("Direction       : BUY")
                    print("Signal Entry    :", signal_text)
                    print("Execution Entry :", askPrice)
                    print("Slippage        :", "N/A" if slippage is None else slippage)
                    print("SL              :", sl)
                    print("Risk Distance   :", risk_distance)
                    print("TP_R            :", Meta.executionTP_R)
                    print("TP        :", tp)
                    print("Quote RR         :", real_rr)
                    print("=====================================")
                request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": mt5.ORDER_TYPE_BUY,
                "price": askPrice,
                "deviation": 10,               
                "sl": sl, 
                "magic": magic,
                "comment": comment,
                "type_filling": filling_type,
                "type_time": mt5.ORDER_TIME_GTC}

                #برای بعضی از استراتژی ها تیک پروفیت می گذارم
                if magic == 5 or magic == 1000 or magic==4 or magic==6 or magic == 7 or magic == 8:
                    request['tp']=tp
            
                result = mt5.order_send(request)

                # Method B: the original TP is already on the order as a fallback.
                # Immediately after fill, recalculate TP from the real position price.
                if (
                    result is not None
                    and Meta.executionBasedTP == True
                    and stopLossPure == True
                    and hasattr(result, "retcode")
                    and result.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED)
                ):
                    Meta.UpdateTPAfterFill(
                        symbol,
                        magic,
                        True,
                        sl,
                        fallback_tp=tp
                    )
            except BaseException as e:
                exceptMessage = f"An exception has occurred in Meta.SendOrder open a buy trade: {str(e)}"
                print(exceptMessage)
                result = None
                if Meta.teleBotMessage:
                    TeleBot().SendMessage(exceptMessage)

            return result

        #OPEN A sell TRADE        
        if sell and ticket==None:
            # if magic == 5 or magic == 4 or magic == 7:
            if stopLossWithAtr == True:
                tp, sl = Meta.StopLossTakeProfitFromVar(symbol, False, pct_tp, pct_sl)
            else:
                if stopLossPure == False:
                    tp, sl = Meta.RiskReward(symbol, buy=False, risk=pct_sl, reward=pct_tp)
                else:
                    tp, sl = pct_tp, pct_sl
            try:
                bidPrice = mt5.symbol_info_tick(symbol).bid
                print(f"bidPrice:{bidPrice}")

                # Method B: calculate an immediate fallback TP from the
                # pre-order quote, then recalculate TP from the actual fill
                # immediately after order_send().
                # RiskReward() is intentionally not used in this path.
                if Meta.executionBasedTP == True and stopLossPure == True:
                    risk_distance = sl - bidPrice
                    if risk_distance <= 0:
                        print("ERROR: execution price is not below SELL SL; order not sent.")
                        return None
                    tp = bidPrice - (risk_distance * Meta.executionTP_R)

                    signal_text = "N/A" if Meta.executionSignalEntry is None else str(Meta.executionSignalEntry)
                    slippage = None if Meta.executionSignalEntry is None else Meta.executionSignalEntry - bidPrice
                    real_rr = abs(tp - bidPrice) / abs(bidPrice - sl)
                    print("========== EXECUTION DEBUG ==========")
                    print("Symbol          :", symbol)
                    print("Direction       : SELL")
                    print("Signal Entry    :", signal_text)
                    print("Execution Entry :", bidPrice)
                    print("Slippage        :", "N/A" if slippage is None else slippage)
                    print("SL              :", sl)
                    print("Risk Distance   :", risk_distance)
                    print("TP_R            :", Meta.executionTP_R)
                    print("Final TP        :", tp)
                    print("Real RR         :", real_rr)
                    print("=====================================")
                request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": mt5.ORDER_TYPE_SELL,
                "price": bidPrice,
                "deviation": 10,                
                "sl": sl, 
                "magic": magic,
                "comment": comment,
                "type_filling": filling_type,
                "type_time": mt5.ORDER_TIME_GTC}

                if magic == 5 or magic == 1000 or magic==4 or magic==6 or magic == 7 or magic == 8:
                    request['tp']=tp
            
                result = mt5.order_send(request)

                # Method B: the original TP is already on the order as a fallback.
                # Immediately after fill, recalculate TP from the real position price.
                if (
                    result is not None
                    and Meta.executionBasedTP == True
                    and stopLossPure == True
                    and hasattr(result, "retcode")
                    and result.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED)
                ):
                    Meta.UpdateTPAfterFill(
                        symbol,
                        magic,
                        False,
                        sl,
                        fallback_tp=tp
                    )
            except BaseException as e:
                exceptMessage = f"An exception has occurred in Meta.SendOrder open a sell trade: {str(e)}"
                print(exceptMessage)
                result = None
                if Meta.teleBotMessage:
                    TeleBot().SendMessage(exceptMessage)
            return result
        
        
        #CLOSE A buy TRADE
        if buy and ticket!=None:
            try:
                request = {
                "position": ticket,
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": mt5.ORDER_TYPE_SELL,
                "price": mt5.symbol_info_tick(symbol).bid,
                "deviation": 10,
                "magic": magic,
                "comment": comment,
                "type_filling": filling_type,
                "type_time": mt5.ORDER_TIME_GTC}
            
                result = mt5.order_send(request)
            except BaseException as e:
                exceptMessage = f"An exception has occurred in Meta.SendOrder close a buy trade: {str(e)}"
                print(exceptMessage)
                result = None
                if Meta.teleBotMessage:
                    TeleBot().SendMessage(exceptMessage)

            return result

        #CLOSE A sell TRADE    
        if sell and ticket!=None:
            try:
                request = {
                "position": ticket,
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": mt5.ORDER_TYPE_BUY,
                "price": mt5.symbol_info_tick(symbol).ask,
                "deviation": 10,
                "magic": magic,
                "comment": comment,
                "type_filling": filling_type,
                "type_time": mt5.ORDER_TIME_GTC}
            
                result = mt5.order_send(request)
            except BaseException as e:
                exceptMessage = f"An exception has occurred in Meta.SendOrder close a sell trade: {str(e)}"
                print(exceptMessage)
                result = None
                if Meta.teleBotMessage:
                    TeleBot().SendMessage(exceptMessage)

            return result
        
    def resume():
        """ پوزیشن های جاری را بر می گرداند. پوزیشن صفر پوزیشن خرید می باشد """            
        columns = ["ticket", "position", "symbol", "volume", "magic", "profit", "price", "tp", "sl","trade_size"]
        summary = pd.DataFrame()
        
        try:
            positionsList = mt5.positions_get()
            if len(positionsList) != 0:
                for element in positionsList:
                    element_pandas = pd.DataFrame([element.ticket, element.type, element.symbol, element.volume, element.magic,
                                                element.profit, element.price_open, element.tp,
                                                element.sl, mt5.symbol_info(element.symbol).trade_contract_size],
                                                index=columns).transpose()
                    summary = pd.concat((summary, element_pandas), axis=0)

                summary["profit %"] = summary.profit / (summary.price * summary.trade_size * summary.volume)
                summary = summary.reset_index(drop=True)
        except BaseException as e:
            exceptMessage = f"Error in Meta.resume: {str(e)}"
            print(exceptMessage)
            if Meta.teleBotMessage:
                TeleBot.SendMessage(exceptMessage)
        
        return summary    
    
    def TrailingStopLoss(magicList):
        Meta.summary = Meta.resume()
        if Meta.summary.shape[0] >0:
            for i in range(Meta.summary.shape[0]):
                difference = 0
                row = Meta.summary.iloc[i]
                symbol = row["symbol"]
                # اگر اینکار رو نکنیم تی پی
                # توسط تغییر استاپ لاس سفارش پاک می شود
                tp = row["tp"]
                magic = row['magic'] 
                # گرانول ریز کردن تریلینگ
                # اینگونه تریلینگ فقط برای استراتژی خاصی که آنرا صدا زده اجرا می شود 
                if magic in magicList:
                    """ تغییر پویای استاپ لاس برای سفارش های خرید """
                    if row["position"] == 0:
                        try:
                            if (symbol not in Meta.maxPrice.keys()):
                                Meta.maxPrice[symbol]={}
                            if (magic not in Meta.maxPrice[symbol].keys()):
                                Meta.maxPrice[symbol][magic]=row["price"]                        
                            current_price = (mt5.symbol_info(symbol).ask + mt5.symbol_info(symbol).bid ) / 2
                            from_sl_to_curent_price = current_price - row["sl"]
                            from_sl_to_max_price = Meta.maxPrice[symbol][magic] - row["sl"]
                            if current_price > Meta.maxPrice[symbol][magic]:
                                Meta.maxPrice[symbol][magic] = current_price
                            if from_sl_to_curent_price > from_sl_to_max_price:
                                difference = from_sl_to_curent_price - from_sl_to_max_price
                                filling_type=Meta.FindFillingMode(symbol)
                                # point = mt5.symbol_info(symbol).point
                                request = {
                                "action": mt5.TRADE_ACTION_SLTP,
                                "symbol": symbol,
                                "position": row["ticket"],
                                "volume": row["volume"],
                                "type": mt5.ORDER_TYPE_BUY,
                                "price": row["price"],
                                "tp": tp,
                                "sl": row["sl"] + difference,
                                "type_filling": filling_type,
                                "type_time": mt5.ORDER_TIME_GTC,
                                }
                                information = mt5.order_send(request)
                                print(f"Buy StopLoss Trailing\tsymbol:{symbol}\tmagic:{magic}\torder:{row['ticket']}\tprice:{information.request.price}\tSL:{information.request.sl}")
                        except BaseException as e:
                            exceptMessage = f"An exception has occurred in Meta.Trailing_stop_loss buy order :{str(e)}"
                            print(exceptMessage)
                            if Meta.teleBotMessage:
                                TeleBot().SendMessage(exceptMessage)

                    """ تغییر پویای استاپ لاس برای سفارش های فروش """
                    if row["position"] == 1:
                        try:
                            if symbol not in Meta.minPrice.keys():
                                Meta.minPrice[symbol]={}
                            if (magic not in Meta.minPrice[symbol].keys()):
                                Meta.minPrice[symbol][magic]=row["price"]
                            current_price = (mt5.symbol_info(symbol).ask + mt5.symbol_info(symbol).bid ) / 2
                            from_sl_to_curent_price = row["sl"] - current_price
                            from_sl_to_min_price = row["sl"] - Meta.minPrice[symbol][magic]
                            if current_price < Meta.minPrice[symbol][magic]:
                                Meta.minPrice[symbol][magic] = current_price
                            if from_sl_to_curent_price > from_sl_to_min_price:
                                difference = from_sl_to_curent_price - from_sl_to_min_price 
                                filling_type = mt5.symbol_info(symbol).filling_mode
                                # point = mt5.symbol_info(symbol).point
                                request = {
                                "action": mt5.TRADE_ACTION_SLTP,
                                "symbol": symbol,
                                "position": row["ticket"],
                                "volume": row["volume"],
                                "type": mt5.ORDER_TYPE_SELL,
                                "price": row["price"],
                                "tp":tp,
                                "sl": row["sl"] - difference,
                                "type_filling": filling_type,
                                "type_time": mt5.ORDER_TIME_GTC,
                                }                                
                                information = mt5.order_send(request)
                                print(f"Sell StopLoss Trailing\t{symbol}\tmagic:{magic}\torder:{row['ticket']}\tprice:{information.request.price}\tSL:{information.request.sl}")
                        except BaseException as e:
                            exceptMessage = f"An exception has occurred in Meta.Trailing_stop_loss sell order :{str(e)}"
                            print(exceptMessage)
                            if Meta.teleBotMessage:
                                TeleBot.SendMessage(exceptMessage)
                        
    def VerifyTSL(magicList):
        #print("MAX", Meta.maxPrice)
        #print("MIN", Meta.minPrice)
        if len(Meta.summary)>0:
            buy_open_positions_symbols = Meta.summary.loc[(Meta.summary["position"]==0) & (Meta.summary["magic"].isin(magicList))]["symbol"]
            sell_open_positions_symbols = Meta.summary.loc[(Meta.summary["position"]==1) & (Meta.summary["magic"].isin(magicList))]["symbol"]
            # distinct (unique) the list's items
            buy_open_positions_symbols = list(set(buy_open_positions_symbols))
            sell_open_positions_symbols = list(set(sell_open_positions_symbols))
        else:
            buy_open_positions_symbols = []
            sell_open_positions_symbols = []
        
        if len(buy_open_positions_symbols)>0:
            for symbol in buy_open_positions_symbols:
                magicBuySymbol = Meta.summary.loc[(Meta.summary["position"]==0) & (Meta.summary["symbol"]==symbol) & (Meta.summary["magic"].isin(magicList))]["magic"]

                # اگر یک پوزیشن خرید به صورت دستی بسته شود یا استاپ لاس آن بخورد
                # بایستی مقادیر ماکزیمم آن در دیکشنری نیز حذف گردد
                # در این قسمت در صورتی که چند سفارش مختلف با استراتژی مختلف
                # برای یک رمزارز وجود داشته باشد مدیریت می شود
                # اما آخرین سفارش یک رمزارز در لیست خرید با شرط چند خط پایین تر حذف می شود
                if len(Meta.maxPrice[symbol]) != len(magicBuySymbol) and len(magicBuySymbol) >0:
                    magic_to_delete = []

                    for magic in Meta.maxPrice[symbol].keys():
                        if magic not in list(magicBuySymbol):
                            magic_to_delete.append(magic)

                    for magic in magic_to_delete:
                        del Meta.maxPrice[symbol][magic]
        # آخرین سفارش خرید یک رمزارز در لیست به شکل زیر از دیکشنری ماکزیمم پاک می شود
        if len(Meta.maxPrice) > len(buy_open_positions_symbols) and len(Meta.maxPrice) >0:
            symbol_to_delete = []

            for symbol in Meta.maxPrice.keys():
                if symbol not in list(buy_open_positions_symbols):
                    symbol_to_delete.append(symbol)

            for symbol in symbol_to_delete:
                del Meta.maxPrice[symbol]

        if len(sell_open_positions_symbols)>0:
            for symbol in sell_open_positions_symbols:
                magicSellSymbol = Meta.summary.loc[(Meta.summary["position"]==1) & (Meta.summary["symbol"]==symbol) & (Meta.summary["magic"].isin(magicList))]["magic"]

                if len(Meta.minPrice[symbol]) != len(magicSellSymbol) and len(magicSellSymbol) >0:
                    magic_to_delete = []

                    for magic in Meta.minPrice[symbol].keys():
                        if magic not in list(magicSellSymbol):
                            magic_to_delete.append(magic)

                    for magic in magic_to_delete:
                        del Meta.minPrice[symbol][magic]
                        
        if len(Meta.minPrice) > len(sell_open_positions_symbols) and len(Meta.minPrice) >0:
            symbol_to_delete = []

            for symbol in Meta.minPrice.keys():
                if symbol not in list(sell_open_positions_symbols):
                    symbol_to_delete.append(symbol)

            for symbol in symbol_to_delete:
                del Meta.minPrice[symbol]

        # در صورتی که لیست خرید ها خالی باشد دیکشنری ماکزیمم پاک می شود
        if len(buy_open_positions_symbols) == 0:
            Meta.maxPrice={}

        if len(sell_open_positions_symbols) == 0:
            Meta.minPrice={}
                            
    def WaitUntilMarketOpen(symbol, lot, buy, sell, ticket=None, pct_tp=0.02, pct_sl=0.01, magic=0, result=None, stopLossWithAtr=False, stopLossPure=False):

        passBecauseStopLossHit = False
        while (result.comment == "Market closed" and passBecauseStopLossHit == False):
            # برای استراتژی یک دقیقه باید هر ۵ ثانیه بازار را چک کنیم و مابقی هر یک دقیقه
            if magic !=3:
                time.sleep(60)
            else:
                time.sleep(5)
            # برای بستن پوزیشن های فعال
            if ticket != None:
                # اگر در حین صبر کردن، استاپ لاس سفارش بخوره دیگر نیاز نیست سفارش را ببندیم    
                resume = Meta.resume()
                if resume.shape[0] > 0:
                    try:
                        row = resume.loc[(resume["symbol"] == symbol) & (resume["magic"] == magic)]
                        if not row.empty:
                            before = mt5.account_info().balance
                            result = Meta.SendOrder(symbol, lot, buy, sell, ticket=ticket,pct_tp=pct_tp, pct_sl=pct_sl, comment=" No specific comment", magic=magic, stopLossWithAtr=stopLossWithAtr, stopLossPure=stopLossPure)
                        else:
                            passBecauseStopLossHit = True
                    except BaseException as e:
                        exceptMessage = f"An exception has occurred in Coinex.WaitUntilMarketOpen: {str(e)}"
                        print(exceptMessage)
                        if Meta.teleBotMessage:
                            TeleBot().SendMessage(exceptMessage)
                else:
                    passBecauseStopLossHit = True
            # برای باز کردن پوزیشن جدید در شرایط بسته بودن بازار
            else:
                result = Meta.SendOrder(symbol, lot, buy, sell, ticket=ticket,pct_tp=pct_tp, pct_sl=pct_sl, comment=" No specific comment", magic=magic, stopLossWithAtr=stopLossWithAtr, stopLossPure=stopLossPure)
                # فقط برای اینکه خالی نباشد
                # مقدار این متغیر برای بستن پوزیشن کاربرد دارد
                before = 1

        return result, passBecauseStopLossHit, before
            
    def run(symbol, buy, sell, lot, pct_tp=0.02, pct_sl=0.01, magic = 0, stopLossWithAtr=False, stopLossPure=False):

        if buy == True or sell ==True:
            resume = Meta.resume()
            if resume.shape[0] > 0:
                    try:
                        row = resume.loc[(resume["symbol"] == symbol) & (resume["magic"] == magic)]
                        if row.empty:
                            position = None
                            ticket = None
                            magicFromPositon = None
                        else:
                            position = row.values[0][1]
                            ticket = row.values[0][0]
                            magicFromPositon= row.values[0][4]
                    except BaseException as e:
                        exceptMessage = f"An exception has occurred in Meta.run: {str(e)}"
                        print(exceptMessage)
                        if Meta.teleBotMessage:
                            TeleBot().SendMessage(exceptMessage)
            else:
                position = None
                ticket = None
                magicFromPositon = None
            
            # برای بررسی بسته بودن بازار و چاپ پیام مناسب
            marketClosed = False
            # اگر قبل از بستن پوزیشن، استاپ لاس بخوره باید از حلقه صبر برای باز شدن بازار خارج شد
            passBecauseStopLossHit = False

            # سفارش تکراری خرید در یک استراتژی انجام نده
            if buy == True and position == 0 and magic == magicFromPositon:
                buy = False
                
            # اگر سفارش خرید داشتی و الان باید ببندیش                
            elif buy == False and position == 0 and magic == magicFromPositon:
                before = mt5.account_info().balance
                result = Meta.SendOrder(symbol, lot, True, False, ticket=ticket,pct_tp=pct_tp, pct_sl=pct_sl, comment=" No specific comment", magic=magic, stopLossWithAtr=stopLossWithAtr, stopLossPure=stopLossPure)
                
                # درصورتی که بازار بسته بشه بایستی صبر کرد تا زمانی که بازار باز شود و سفارش را ببندیم
                if result.comment == "Market closed":
                    print("Market closed!")
                    marketClosed = True
                    result, passBecauseStopLossHit, before = Meta.WaitUntilMarketOpen(symbol, lot, True, False, ticket, pct_tp, pct_sl, magic, result, stopLossWithAtr=stopLossWithAtr, stopLossPure=stopLossPure)                
                if (marketClosed and passBecauseStopLossHit == False):
                    print("Market open!")
                    marketClosed = False
                if passBecauseStopLossHit:
                    print(f"I try to close a buy trade (magic:{magic}) but stoploss hit! market maybe close or open!")
                    passBecauseStopLossHit = False

                if result != None:
                    after = mt5.account_info().balance
                    print("-"*75)
                    print("Date: ", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "\tSYMBOL:", symbol)
                    print(f"{Fore.LIGHTCYAN_EX}CLOSE {Style.RESET_ALL}BUY POSITION: {result.comment}")
                    pct = np.round(100*(after-before)/before, 6)
                    print(f"your profit:{pct}")
                    if Meta.teleBotMessage:
                        TeleBot().SendMessage(f"CLOSE BUY {symbol}: {result.comment}")
                    if result.comment != "Request executed":
                        print("WARNINGS", result.comment)
                    print("-"*75)   
                else:
                    print(f"{Fore.YELLOW}Warning: {Style.RESET_ALL}The close buy SendOrder result for magic {magic} is None!")
                
            elif sell == True and position == 1 and magic == magicFromPositon:
                sell = False
                
            elif sell == False and position == 1 and magic == magicFromPositon:
                before = mt5.account_info().balance
                result = Meta.SendOrder(symbol, lot, False, True, ticket=ticket,pct_tp=pct_tp, pct_sl=pct_sl, comment=" No specific comment", magic=magic, stopLossWithAtr=stopLossWithAtr, stopLossPure=stopLossPure)

                # درصورتی که بازار بسته بشه بایستی صبر کرد تا زمانی که بازار باز شود و سفارش را ببندیم
                if result.comment == "Market closed":
                    print("Market closed!")
                    marketClosed = True
                    result, passBecauseStopLossHit, before = Meta.WaitUntilMarketOpen(symbol, lot, False, True, ticket, pct_tp, pct_sl, magic, result, stopLossWithAtr=stopLossWithAtr, stopLossPure=stopLossPure)                
                if (marketClosed and passBecauseStopLossHit == False):
                    print("Market open!")
                    marketClosed = False
                if passBecauseStopLossHit:
                    print(f"I try to close a buy trade (magic:{magic}) but stoploss hit! market maybe close or open!")
                    passBecauseStopLossHit = False

                if result != None:
                    print("-"*75)
                    print("Date: ", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "\tSYMBOL:", symbol)
                    print(f"{Fore.LIGHTCYAN_EX}CLOSE {Style.RESET_ALL}SELL POSITION: {result.comment}")
                    after = mt5.account_info().balance                    
                    pct = np.round(100*(after-before)/before, 6)
                    print(f"your profit:{pct}")
                    if Meta.teleBotMessage:
                        TeleBot().SendMessage(f"CLOSE SELL {symbol}: {result.comment}")
                    if result.comment != "Request executed":
                        print("WARNINGS", result.comment)                   
                    print("-"*75)
                else:
                    print(f"{Fore.YELLOW}Warning: {Style.RESET_ALL}The close sell SendOrder result for magic {magic} is None!")

            elif buy == True:
                result =  Meta.SendOrder(symbol, lot, True, False, ticket=None,pct_tp=pct_tp, pct_sl=pct_sl, comment=" No specific comment", magic=magic, stopLossWithAtr=stopLossWithAtr, stopLossPure=stopLossPure)


                if result != None:
                    # درصورتی که بازار بسته بشه بایستی صبر کرد تا زمانی که بازار باز شود و سفارش بگذاریم
                    if result.comment == "Market closed":
                        print("Market closed!")
                        # در سفارش گذاری نیاز به دو متغیر بعد از ریزالت نیست
                        # فقط چون نخواستم دوباره تابع تعریف کنم گذاشتم بمونه
                        result, passBecauseStopLossHit, before = Meta.WaitUntilMarketOpen(symbol, lot, True, False, None, pct_tp, pct_sl, magic, result, stopLossWithAtr=stopLossWithAtr, stopLossPure=stopLossPure)                

                    print("-"*75)
                    print("Date: ", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "\tSYMBOL:", symbol)
                    print(f"{Fore.GREEN if buy == True else Fore.WHITE}BUY: {buy} \t  {Fore.RED if sell == True else Fore.WHITE}SELL: {sell} {Style.RESET_ALL} \t Magic: {magic}")
                    print(f"OPEN BUY POSITION: {result.comment}")
                    print(f"price: {result.request.price} \t SL: {result.request.sl} \t TP: {result.request.tp}")
                    if Meta.teleBotMessage:
                        TeleBot().SendMessage(f"OPEN Buy {symbol}: {result.comment} price:{result.request.price} sl:{result.request.sl} tp:{result.request.tp}")
                    if result.comment != "Request executed":
                        print("WARNINGS", result.comment)
                    print("-"*75)
                else:
                    print(f"{Fore.YELLOW}Warning: {Style.RESET_ALL}The open buy SendOrder result is None!")

            elif sell == True:
                result = Meta.SendOrder(symbol, lot, False, True, ticket=None,pct_tp=pct_tp, pct_sl=pct_sl, comment=" No specific comment", magic=magic, stopLossWithAtr=stopLossWithAtr, stopLossPure=stopLossPure)


                if result != None:
                    # درصورتی که بازار بسته بشه بایستی صبر کرد تا زمانی که بازار باز شود و سفارش بگذاریم
                    if result.comment == "Market closed":
                        print("Market closed!")
                        # در سفارش گذاری نیاز به دو متغیر بعد از ریزالت نیست
                        # فقط چون نخواستم دوباره تابع تعریف کنم گذاشتم بمونه
                        result, passBecauseStopLossHit, before = Meta.WaitUntilMarketOpen(symbol, lot, False, True, None, pct_tp, pct_sl, magic, result, stopLossWithAtr=stopLossWithAtr, stopLossPure=stopLossPure)                
                        
                    print("-"*75)
                    print("Date: ", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "\tSYMBOL:", symbol)
                    print(f"{Fore.GREEN if buy == True else Fore.WHITE}BUY: {buy} \t  {Fore.RED if sell == True else Fore.WHITE}SELL: {sell} {Style.RESET_ALL} \t Magic: {magic}")
                    print(f"OPEN SELL POSITION: {result.comment}")
                    print(f"price: {result.request.price} \t SL: {result.request.sl} \t TP: {result.request.tp}")
                    if Meta.teleBotMessage:
                        TeleBot().SendMessage(f"OPEN SELL {symbol}: {result.comment} price:{result.request.price} sl:{result.request.sl} tp:{result.request.tp}")
                    if result.comment != "Request executed":
                        print("WARNINGS",  result.comment)
                    print("-"*75)
                else:
                    print(f"{Fore.YELLOW}Warning: {Style.RESET_ALL}The open sell SendOrder result is None!")
   
    def LoginAccount(login, password, server):
        if mt5.login(login=login,password=password,server=server):
            print("logged in succesffully")
        else:
            print("login failed, error code: {}".format(mt5.last_error()))

    def InitializeWithLogin(login, password, server):        
        if not mt5.initialize():
            print("initialize() failed, error code {}", mt5.last_error())
        else:
            Meta.LoginAccount(login, password, server)
        