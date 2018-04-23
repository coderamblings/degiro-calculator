#!/bin/python

# The idea of this app is to take a yearly transaction report from Degiro
# and process the transactions in order to calculate the profit / loss
# for taxation purposes

import pymysql as m
import pymysql.cursors

def process_purchase(row):
    """Gets a row read from inut table, picks selected columns and inserts into proper table"""
    """Removes double and single quotes from stock names"""
    normalized_name = row["stock_name"]
    normalized_name = normalized_name.replace('"','')
    normalized_name = normalized_name.replace("'","")
    #Table name which contains spaces needs to be surrounded by ticks, thus u0060
    table_name = u"\u0060" + normalized_name + u"\u0060"
    print 'Performing an insert of a purchase operation into' + table_name
    #Row value which contains spaces needs to be surrounded by quotes, thus u0022
    stock_name = u"\u0022" + normalized_name + u"\u0022"
    sql = "INSERT INTO %s (date, stock_name, trx_value_pln, available_stock_no, orig_stock_no, purchase_price_pln) VALUES (\"%s\",%s,%s,%s,%s,%s)"
    k.execute(sql % (table_name,row["date"],stock_name,row["trx_value_pln"],row["stock_no"],row["stock_no"],abs(row["trx_value_pln"]/row["stock_no"])))
    return None

def update_stock_inventory(row, table, stock_left):
    """Invoked to subtract sold stock from given stock inventory table"""
    sql = "UPDATE %s SET available_stock_no = %i where ID = %i"
    u = connection.cursor()
    u.execute(sql % (table, stock_left,row["ID"]))
    u.connection.commit()
    u.close()
    return None

def update_sales_table(row, stock_name, sale_value, purchase_cost):
    #comment = "Sold %s of stock for %s, while the purchase cost was %s" % (abs(row["stock_no"]), sale_value, purchase_cost)
    sql_sale_result = "INSERT INTO sales VALUES(\"%s\",\"%s\",%s,%s,%i,%s,%s)"
    i = connection.cursor()
    i.execute(sql_sale_result % (row["date"], stock_name, abs(sale_value / row["stock_no"]), sale_value, abs(row["stock_no"]), purchase_cost, sale_value - abs(purchase_cost)))
    i.connection.commit()
    i.close()
    return None

def process_sale(row):
    """The heart of this app"""
    stock_to_sale_no = abs(row["stock_no"])
    sale_value = row["trx_value_pln"] #defined only for convinience
    purchase_cost = 0.0
    normalized_name = row["stock_name"]
    normalized_name = normalized_name.replace('"','')
    normalized_name = normalized_name.replace("'","")
    table_name = u"\u0060" + normalized_name + u"\u0060"
    s = connection.cursor()
    sql = "SELECT * from %s WHERE available_stock_no > 0 ORDER BY ID"
    s.execute(sql % table_name)
    result_sales = s.fetchall()
    #Here we start iterating through the given stock table
    #We update values in the stock table to maintain a valid state, row after row
    #In order to be able to compare sale value vs purchse costs

    for row_s in result_sales:
        print 'Starting sale of ' + normalized_name + ", there's " + str(row_s["available_stock_no"]) + " available in the first stock table, row ID " + str(row_s["ID"])
        #If there's less stock to be sold than there are available stock in the first row of the given stock database, we just subtract one from the other and that's it
        if row_s["available_stock_no"] >= stock_to_sale_no:
            print "Now finishing sale of %s, using row ID: %s" % (normalized_name, row_s["ID"])
            purchase_cost = purchase_cost + stock_to_sale_no * row_s["purchase_price_pln"]

            #update DB
            update_stock_inventory(row_s, table_name, (row_s["available_stock_no"] - stock_to_sale_no))
            update_sales_table(row, normalized_name, sale_value,purchase_cost)
            stock_to_sale_no = 0
            break #if stock_to_sale_no is 0, we're done with this operation

        #If the sale is greater than the number of stock in the first registered purchase of that stock, we must sell all that stock, then move onto another row and keep selling
        elif row_s["available_stock_no"] < stock_to_sale_no:
            purchase_cost = purchase_cost + row_s["available_stock_no"] * row_s["purchase_price_pln"]
            stock_to_sale_no = stock_to_sale_no - row_s["available_stock_no"]
            print "Processing the sale using row ID: %s" % row_s["ID"]
            print "Updated stock_to_sale_no " + str(stock_to_sale_no)
            print "Updated purchase_cost " + str(purchase_cost)
            all_sold = 0 #used only because we can't pass a 0 as a function parameter!
            #Update DB
            update_stock_inventory(row_s, table_name, all_sold)
        s.close()
    return None



connection = m.connect(host='localhost', user='stockprofit', db='stockprofit', port=3306, cursorclass=pymysql.cursors.DictCursor)
k = connection.cursor()
k.execute('SELECT * FROM input')
result = k.fetchall()
if len(result) == 0:
    print "Couldn't find any rows in the 'input' table, double check the DB."
for row in result:
    print "Now processing %s, stock: %s, volume: %i" %(row["date"], row["stock_name"], row["stock_no"])
    if row["stock_no"] > 0:
        process_purchase(row)
    elif row["stock_no"] < 0:
        process_sale(row)
    k.connection.commit()
k.close()
