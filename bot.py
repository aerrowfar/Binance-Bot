import os
#simple python file with two variables:API keys.
import keys
import dateparser 
from datetime import datetime
import pytz
import pandas as pd

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

start_time= date_to_milliseconds("250 minutes ago UTC")
#print(start_time)
start_time_check = pd.to_datetime(start_time,unit='ms')
#print(start_time_check)

bars2=client.get_historical_klines('BTCUSDT','5m',limit= 200,start_str=start_time)

#output_data=[]
#output_data+=bars2
#print (output_data[1])
for line in bars2:
    del line[5:]
    line[0]=pd.to_datetime(line[0], unit='ms')
    #print(line[0])
    #line[1:4].apply(lambda x: float(x))
    #print(type(line[2]))


btc_df=pd.DataFrame(bars2,columns=['date','open','high','low','close'])
#btc_df['open'].apply(lambda x: float(x))
#btc_df['open']=btc_df['open'].astype(float)
#btc_df.apply(pd.to_numeric,errors='coerce')
btc_df[['open','high','low','close']]=btc_df[['open','high','low','close']].apply(pd.to_numeric,errors='coerce')


#btc_df[['close']].describe()

#btc_df["ap"]=btc_df['open']+btc_df['close']/3
btc_df["ap"]=(btc_df['high']+btc_df['low']+btc_df['close'])/3
#btc_df=pd.DataFrame.insert(loc=7,column='ap',value=2,allow_duplicates=False)
#btc_df.set_index('date', inplace=True)
#print(btc_df.head())
btc_df['esa']=btc_df['ap'].ewm(span=10, min_periods=10,adjust=False,ignore_na=False).mean()
btc_df['d']=(abs(btc_df['ap']-btc_df['esa'])).ewm(span=10,min_periods=10,adjust=False,ignore_na=False).mean()
btc_df['ci']=(btc_df['ap']-btc_df['esa'])/(0.015*btc_df['d']) 
btc_df['wt1']=btc_df['ci'].ewm(span=21,min_periods=21,adjust=False,ignore_na=False).mean()
btc_df['wt2']=btc_df['wt1'].ewm(span=4,min_periods=4,adjust=False,ignore_na=False).mean()
#btc_df.to_csv('btc_bars2.csv')

#btc_df['20sma']=btc_df.close.rolling(21).mean()
#btc_df['20ema']=btc_df.close.ewm(span=21,adjust=False).mean()
btc_df.info()
#print(btc_df['esa'])
#print(btc_df.head(2))
#print(btc_df.tail(2))
print(btc_df)





