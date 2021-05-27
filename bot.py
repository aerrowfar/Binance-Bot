import os
import keys
import dateparser 
from datetime import datetime
import pytz
import pandas as pd
import parameters as pam
import math
import time
from binance.client import Client
import gspread
import sheets as sh
from time import sleep
import traceback
from decimal import Decimal
from dotenv import load_dotenv
load_dotenv()
import os

api_key= os.environ.get('binance_api')
api_secret=os.environ.get('binance_secret')

client= Client(api_key,api_secret)

#convert date string to miliseoncds for Binance.
def date_to_milliseconds(date_str):
    epoch=datetime.utcfromtimestamp(0).replace(tzinfo=pytz.utc)
    d= dateparser.parse(date_str)
    if d.tzinfo is None or d.tzinfo.utcoffset(d) is None:
        d=d.replace(tzinfo=pytz.utc)

    return int((d-epoch).total_seconds()*1000.0)

#grab tabular data of crypto price, calculate wave trend variables and include in table.
def crypto_df(start_time_UTC,pair,candles,limit,channel_length,average_length):
    #pulls in data, populates a table, and calculates all necessary variables.

    start_time= date_to_milliseconds(start_time_UTC)
    start_time_check = pd.to_datetime(start_time,unit='ms')

    bars=client.get_historical_klines(pair,candles,limit=limit,start_str=start_time)

    for line in bars:
        del line[5:]
        line[0]=pd.to_datetime(line[0], unit='ms')
   

    crypto_df=pd.DataFrame(bars,columns=['date','open','high','low','close'])
    crypto_df=crypto_df.rename_axis('row')

    crypto_df[['open','high','low','close']]=crypto_df[['open','high','low','close']].apply(pd.to_numeric,errors='coerce')



    crypto_df['ap']=(crypto_df['high']+crypto_df['low']+crypto_df['close'])/3
    crypto_df['esa']=crypto_df['ap'].ewm(span=channel_length, min_periods=channel_length,adjust=False,ignore_na=False).mean()
    crypto_df['d']=(abs(crypto_df['ap']-crypto_df['esa'])).ewm(span=channel_length,min_periods=channel_length,adjust=False,ignore_na=False).mean()
    crypto_df['ci']=(crypto_df['ap']-crypto_df['esa'])/(0.015*crypto_df['d']) 
    crypto_df['wt1']=crypto_df['ci'].ewm(span=average_length,min_periods=average_length,adjust=False,ignore_na=False).mean()
    crypto_df['wt2']=crypto_df['wt1'].ewm(span=4,min_periods=4,adjust=False,ignore_na=False).mean()
    
    
    #crypto_df.to_csv('final_bars.csv')
    #crypto_df.info()
    
    
    return crypto_df

#tabular data of crypto price movement for backtesting purposes.
def back_test_df(start_time_UTC,pair,candles,limit):
    start_time= date_to_milliseconds(start_time_UTC)
    start_time_check = pd.to_datetime(start_time,unit='ms')

    bars=client.get_historical_klines(pair,candles,limit=limit,start_str=start_time)

    for line in bars:
        del line[5:]
        line[0]=pd.to_datetime(line[0], unit='ms')
   
    crypto_df=pd.DataFrame(bars,columns=['date','open','high','low','close'])

    crypto_df[['open','high','low','close']]=crypto_df[['open','high','low','close']].apply(pd.to_numeric,errors='coerce')

    crypto_df['ap']=(crypto_df['high']+crypto_df['low']+crypto_df['close'])/3
    
    return crypto_df

#determines amount to buy in base currency
def trade_size(price=0):
    balance = client.get_asset_balance(asset=pam.base)
    capacity= float(balance['free'])
    #have to use a little less than 100% of the balance to avoid rounding errors with API
    capacity = capacity*0.98
    #8 digit decimal is the correct precision to use with API
    capacity = round(capacity,8)
    
    return capacity

#determines amount to sell in base currency 
def alt_in_BTC(alt_position):
    #grab alt price
    ALTBTC = client.get_symbol_ticker(symbol=pam.pair)
    ALTBTC = float(ALTBTC['price'])
    
    #get base currency trade size using alt balance, at 97% and 8 decimal place to avoid rounding errors
    return (round(alt_position*ALTBTC*0.97,8))

#reformats API confirmation returns into useful format for google sheets 
def dissect_order(order):
    total_qty = 0
    total_commission = 0

    for i in order['fills']:
        total = float(i['price'])*float(i['qty'])
        total_qty = total_qty + float(i['qty'])
        total_commission = total_commission + float(i['commission'])
        commissionAsset = i['commissionAsset']
        
    average_price = total/total_qty
    exec_qty= order.get('executedQty')
    status = order.get('status')
    side = order.get('side')

    return [str(datetime.now()),pam.pair,exec_qty,average_price,side, status,total_commission,commissionAsset]

#making a trade 
def make_trade(pair,asset,data_frame,over_bought_level, over_sold_level,order_min,row):
    #cheks for a cross in over bought or sold levels in the specified row by comparing to previous row
    #if a succesful trade is made, writes to google sheets

    #check if row values are in overbought or oversold area> check if there was a cross > 
    #if no open position, open a position.
    
    if data_frame.loc[row,'wt1']>over_bought_level:
        #chek for cross under
        if data_frame.loc[row,'wt1']<data_frame.at[row,'wt2'] and data_frame.at[(row-1),'wt1'] >= data_frame.at[(row-1),'wt2']:
            #check against open positions
            
            position= client.get_asset_balance(asset=asset)
            print('\n\n')
            print('On iteration: ', i)
            print(position)
            position= float(position['free'])
            #position = round(position, 9)

            #IF WE HAVE SOME ALT, SELL INTO BASE:
            if position>order_min:

                print('\n\nTRIED TO SELL, ALT position is ',position)
                

                use_position = alt_in_BTC(position)
            
                print('order quant to go through is ', use_position)
                order = client.create_order(
                symbol=pam.pair,
                side='SELL',
                type= 'MARKET',
                quoteOrderQty=use_position,
                newOrderRespType='FULL')

                order = dissect_order(order)
                print(order)
                
                sh.insert_row(order)
                
                print('Should have uplaoded to sheets succesfully.')

            else:
                print('No position to close.')
        
        #no cross, pass
        else:
            print('Waves not crossing.')
            
    
    #check oversold zone, trying to BUY
    elif data_frame.at[row,'wt1']<over_sold_level:
        #chek for cross over
        if data_frame.at[row,'wt1']>data_frame.at[row,'wt2'] and data_frame.at[(row-1),'wt1'] <= data_frame.at[(row-1),'wt2']:
            #check against open positions
            position= client.get_asset_balance(asset=asset)
            print('\n\n')
            print('On iteration: ', i)
            print(position)
            position= float(position['free'])

            #Not enough ALT, Buy ALT:
            if position <= order_min:
                print('\n\n')
                print('TRIED TO BUY, ALT position is ',position)

                trade_quant = trade_size()
                print('trade quant is ', trade_quant)
            
                
                order = client.create_order(
                symbol=pam.pair,
                side='BUY',
                type= 'MARKET',
                quoteOrderQty=trade_quant,
                newOrderRespType='FULL')
                
                order = dissect_order(order)
                print(order)
        
                
                sh.insert_row(order)
                print('Should have uplaoded to sheets succesfully.')


            else:
                print('Already open position.')
        
        #no cross, pass
        else:
            print('Waves not crossing.')
            
    
    #Values not available
    elif math.isnan(data_frame.at[row,'wt1']):
        print('Value not available')
        
    #None of the above, pass
    else:
        print('not in overbought or oversold')
        
#backtest paramaters to find optimal values.
def back_test_params(chanlmin,chanlmax,avglmin,avglmax,obsmin,obsmax,trade_size):
    print(client.get_system_status())
    results=pd.DataFrame(columns=['Channel L','Average L','Over b/s L','Ps Opened','Ps Closed','Profit'])
    alt_coing_df= back_test_df(pam.start_time_UTC,pam.pair,pam.candles,pam.limit)
    t=0
    
    
    def back_test(data_frame,asset,limit,pair,channel_length,average_length,over_bought_level, over_sold_level,trade_size):
        BTC_balance=100
        alt_coin_balance=0
        number_of_positions_opened=0
        number_of_positions_closed=0
        position=0
        nonlocal results
        
        
        data_frame=data_frame.copy(deep=True)
        
        data_frame['esa']=data_frame['ap'].ewm(span=channel_length, min_periods=channel_length,adjust=False,ignore_na=False).mean()
        data_frame['d']=(abs(data_frame['ap']-data_frame['esa'])).ewm(span=channel_length,min_periods=channel_length,adjust=False,ignore_na=False).mean()
        data_frame['ci']=(data_frame['ap']-data_frame['esa'])/(0.015*data_frame['d']) 
        data_frame['wt1']=data_frame['ci'].ewm(span=average_length,min_periods=average_length,adjust=False,ignore_na=False).mean()
        data_frame['wt2']=data_frame['wt1'].ewm(span=4,min_periods=4,adjust=False,ignore_na=False).mean()

        

        def back_test_make_trade(pair,data_frame,over_bought_level, over_sold_level,row,trade_size,asset):
            
            nonlocal BTC_balance
            nonlocal alt_coin_balance
            nonlocal number_of_positions_opened
            nonlocal number_of_positions_closed
            nonlocal position

          
            if data_frame.at[row,'wt1']>over_bought_level:
                
                if data_frame.at[row,'wt1']<data_frame.at[row,'wt2'] and data_frame.at[(row-1),'wt1'] >= data_frame.at[(row-1),'wt2']:
                    
                    
                    if position==1:
                        price=(data_frame.at[row,'low']+data_frame.at[row,'high'])/2
                        BTC_balance=BTC_balance+(alt_coin_balance*price)
                        alt_coin_balance=0
                        
                        number_of_positions_closed=number_of_positions_closed+1
                        position=0
                    else:
                        
                        pass
             
                else:
                    
                    pass
            
            
            if data_frame.at[row,'wt1']<over_sold_level:
                
                if data_frame.at[row,'wt1']>data_frame.at[row,'wt2'] and data_frame.at[(row-1),'wt1'] <= data_frame.at[(row-1),'wt2']:
                    
                    if position==0:
                        price=(data_frame.at[row,'low']+data_frame.at[row,'high'])/2
                        alt_coin_balance=trade_size * BTC_balance / price
                        BTC_balance=BTC_balance-(trade_size*BTC_balance)
                        

                        position=1
                        number_of_positions_opened=number_of_positions_opened+1
                    else:
                        
                        pass
                
                else:
                    
                    pass
            
            
            elif math.isnan(data_frame.at[row,'wt1']):
                
                pass
            
            else:
                
                pass
        
        for i in range(limit-1):
            back_test_make_trade(pair,data_frame,over_bought_level, over_sold_level,i+1,trade_size,asset)   

        BTC_value_of_alt_coin=data_frame.at[limit-1,'close']*alt_coin_balance

        results=results.append({'Channel L': channel_length, 'Average L': average_length,'Over b/s L': over_bought_level,'Ps Opened':number_of_positions_opened,'Ps Closed':number_of_positions_closed,'Profit': int(BTC_balance+BTC_value_of_alt_coin)}, ignore_index=True)
    for i in range(chanlmin,chanlmax):
        for j in range(avglmin,avglmax):
            for z in range(obsmin,obsmax):
                try:
                    back_test(alt_coing_df,pam.asset,pam.limit,pam.pair,i,j,z,z*-1,trade_size)
                    t=t+1
                    print(t) 
                except Exception as e:
                    print(e)

    
    results=results.sort_values(by=['Profit'])
    print(results)
    results.to_csv('results_backtest.csv') 

#example of calling backtest:
#back_test_params(2,30,10,50,20,90,1)

#for testing API interaction with orders.
def test_trading(order_min, asset):
    i=0
    while(True):
        
        position= client.get_asset_balance(asset=asset)
        print('\n\n')
        print('On iteration: ', i)
        print(position)
        position= float(position['free'])
        
        if position>order_min:

            print('\n\nTRIED TO SELL, ETH position is ',position)
            

            use_position = alt_in_BTC(position)
            #use_position = round((position*0.99),8)
            print(type(use_position))
            print('order quant to go through is ', use_position)
            order = client.create_order(
            symbol=pam.pair,
            side='SELL',
            type= 'MARKET',
            quoteOrderQty=use_position,
            newOrderRespType='FULL')

            order = dissect_order(order)
            print(order)
            
            
            sh.insert_row(order)
            
            print('should have uplaoded to sheets')
          
        #Not enough ALT, Buy ALT:
        if position <= order_min:
            print('\n\n')
            print('TRIED TO BUY, ALT position is ',position)

            trade_quant = trade_size()
            print('trade quant is ', trade_quant)
           
            
            order = client.create_order(
            symbol=pam.pair,
            side='BUY',
            type= 'MARKET',
            quoteOrderQty=trade_quant,
            newOrderRespType='FULL')
            
            order = dissect_order(order)
            print(order)
      
            
            sh.insert_row(order)
            print('Should have uplaoded to sheets succesfully.')
        
        i +=1


if __name__=='__main__':
    i=1
    start_time=time.time()
    while(True):
        try:
            print('on check: ',i)
            df=crypto_df(pam.start_time_UTC,pam.pair,pam.candles,pam.limit,pam.channel_length,pam.average_length)
            print(df.tail(1))
            print('time is ',datetime.now())
            make_trade(pam.pair,pam.asset,df,pam.over_bought_level,pam.over_sold_level,pam.order_min,999)
            i = i+1
            sleep_time = 300-((time.time()-start_time)%300)
            print('sleep time is ', sleep_time)
            time.sleep(sleep_time)

        except Exception as e:
            error = traceback.format_exc()
            try:
                make_trade(pam.pair,pam.asset,df,pam.over_bought_level,pam.over_sold_level,pam.order_min,998)
            
            except:
                value = [str(datetime.now()),str(e),error]
                
                sh.insert_row(value)
                i = i+1
                sleep_time = 300-((time.time()-start_time)%300)
                print('sleep time is ', sleep_time)
                time.sleep(sleep_time)



