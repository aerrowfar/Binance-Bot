import os
#simple python file with two variables:API keys.
import keys
import dateparser 
from datetime import datetime
import pytz
import pandas as pd
import parameters as pam
import math

from binance.client import Client

api_key= keys.binance_api
api_secret=keys.binance_secret

client= Client(api_key,api_secret)

client.API_URL= 'https://testnet.binance.vision/api'

def date_to_milliseconds(date_str):
    epoch=datetime.utcfromtimestamp(0).replace(tzinfo=pytz.utc)
    d= dateparser.parse(date_str)
    if d.tzinfo is None or d.tzinfo.utcoffset(d) is None:
        d=d.replace(tzinfo=pytz.utc)

    return int((d-epoch).total_seconds()*1000.0)

##print(date_to_milliseconds("11 hours ago UTC"))
##print(date_to_milliseconds("now UTC"))

#print(client.get_account())

#print(client.get_asset_balance(asset='BTC'))
##print(client.futures_account_balance())
##print(client.get_margin_account())

#btc_price = client.get_symbol_ticker(symbol="ETHBTC")

#print(btc_price)
#print(btc_price["price"])

##timestamp = client._get_earliest_valid_timestamp('BTCUSDT',"1d")
##print(timestamp)

#bars=client.get_historical_klines('BTCUSDT','15m',timestamp,limit=21)

start_time= date_to_milliseconds(pam.start_time_UTC)
#print(start_time)
start_time_check = pd.to_datetime(start_time,unit='ms')
#print(start_time_check)

bars=client.get_historical_klines(pam.pair,pam.candles,limit= pam.limit,start_str=start_time)

#output_data=[]
#output_data+=bars
#print (output_data[1])
for line in bars:
    del line[5:]
    line[0]=pd.to_datetime(line[0], unit='ms')
    #print(line[0])
    #line[1:4].apply(lambda x: float(x))
    #print(type(line[2]))


crypto_df=pd.DataFrame(bars,columns=['date','open','high','low','close'])
#crypto_df['open'].apply(lambda x: float(x))
#crypto_df['open']=crypto_df['open'].astype(float)
#crypto_df.apply(pd.to_numeric,errors='coerce')
crypto_df[['open','high','low','close']]=crypto_df[['open','high','low','close']].apply(pd.to_numeric,errors='coerce')


#crypto_df[['close']].describe()

#crypto_df["ap"]=crypto_df['open']+crypto_df['close']/3
crypto_df["ap"]=(crypto_df['high']+crypto_df['low']+crypto_df['close'])/3
#crypto_df=pd.DataFrame.insert(loc=7,column='ap',value=2,allow_duplicates=False)
#crypto_df.set_index('date', inplace=True)
#print(crypto_df.head())
crypto_df['esa']=crypto_df['ap'].ewm(span=pam.channel_length, min_periods=pam.channel_length,adjust=False,ignore_na=False).mean()
crypto_df['d']=(abs(crypto_df['ap']-crypto_df['esa'])).ewm(span=pam.channel_length,min_periods=pam.channel_length,adjust=False,ignore_na=False).mean()
crypto_df['ci']=(crypto_df['ap']-crypto_df['esa'])/(0.015*crypto_df['d']) 
crypto_df['wt1']=crypto_df['ci'].ewm(span=pam.average_length,min_periods=pam.average_length,adjust=False,ignore_na=False).mean()
crypto_df['wt2']=crypto_df['wt1'].ewm(span=4,min_periods=4,adjust=False,ignore_na=False).mean()
crypto_df.to_csv('final_bars.csv')

#crypto_df['20sma']=crypto_df.close.rolling(21).mean()
#crypto_df['20ema']=crypto_df.close.ewm(span=21,adjust=False).mean()
crypto_df.info()
#print(crypto_df['esa'])
#print(crypto_df.head(2))
#print(crypto_df.tail(2))


print(crypto_df.tail(5))

if crypto_df['wt1'].iloc[-1]>pam.over_bought_level:
    if crypto_df.at[49,'wt1'] > crypto_df.at[49,'wt2']:
        print('condition reached')
    else:
        print('waves not crossing')
elif math.isnan(crypto_df['wt1'].iloc[-1]):
    print('Value not available')
else:
    print(crypto_df['wt1'].iloc[-1])
   
print('wt1 max is ' + str(crypto_df['wt1'].max()))
print('wt1 min is ' + str(crypto_df['wt1'].min()))
print('wt2 max is ' + str(crypto_df['wt2'].max()))
print('wt2 max is ' + str(crypto_df['wt2'].min()))







