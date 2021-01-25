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

start_time= date_to_milliseconds("315 minutes ago UTC")
#print(start_time)
start_time_check = pd.to_datetime(start_time,unit='ms')
#print(start_time_check)

bars2=client.get_historical_klines('BTCUSDT','15m',limit= 21,start_str=start_time)

#output_data=[]
#output_data+=bars2
#print (output_data[1])
for line in bars2:
    del line[5:]
    line[0]=pd.to_datetime(line[0], unit='ms')
    #print(line[0])

btc_df=pd.DataFrame(bars2,columns=['date','open','high','low','close'])
#btc_df.set_index('date', inplace=True)
#print(btc_df.head())

#btc_df.to_csv('btc_bars2.csv')

btc_df['20sma']=btc_df.close.rolling(21).mean()
btc_df['20ema']=btc_df.close.ewm(span=21,adjust=False).mean()
print(btc_df.tail(21))





