import gspread
from oauth2client.service_account import ServiceAccountCredentials


scope= ['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']
creds= ServiceAccountCredentials.from_json_keyfile_name("goog_keys.json",scope)

client=gspread.authorize(creds)

sheet=client.open("Binance Bot").sheet1


def insert_cell(type_val,row,value):
    if type_val=='date':
        sheet.update_cell(row,1,value)
    elif type_val=='pair':
        sheet.update_cell(row,2,value)
    elif type_val=='quantity':
        sheet.update_cell(row,3,value)
    elif type_val=='open_price':
        sheet.update_cell(row,4,value)
    elif type_val=='close_price':
        sheet.update_cell(row,5,value)
    elif type_val=='profit':
        sheet.update_cell(row,6,value)
    elif type_val=='profit%':
        sheet.update_cell(row,7,value)
    else:
        print('Bad Type on Google Sheets Cell Input')
    

def insert_row(values,row=2):
    sheet.insert_row(values,row)

