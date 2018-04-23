# Kalkulator zysków / strat Degiro
TBD: 
- manual in English
- further automation of preparatory steps
- rewrite for python3


Programik napisany, by móc przejrzeć historię swoich dokonań na giełdzie, wyliczyć średnią cenę zakupu trzymanych akcji, ew. wyliczyć zyski / straty, gdyby Degiro nie dostarczyło rocznego raportu (zalecałbym jednak ostrożność, w tej chwili programik generuje różnice rzędu 25gr na 100K PLN obrotu względem raportu Degiro).

Skrócony opis wykorzystania programu:

1. Przygotuj bazę danych + użytkownika.
2. Załaduj raport transakcji degiro do źródłowej tabeli, wygeneruj tabele dla poszczególnych firm / akcji.
3. Odpal program.
4. Analizuj.

## Przygotuj bazę danych + użytkownika.

```
create database stockprofit;
create user 'stockprofit'@'localhost';
grant all privileges on stockprofit.* to 'stockprofit'@'localhost';
grant file on *.* to 'stockprofit'@'localhost';
flush privileges;
```

Wygeneruj raport transakcji w Degiro (od początku przygody z brokerem), w formacie CSV.
Wrzuć plik z transakcjami (**Transactions.csv**) do katalogu bazy stockprofit (/var/lib/mysql/stockprofit/).

## Załaduj raport transakcji degiro do źródłowej tabeli, wygeneruj tabele dla poszczególnych firm.

Domyślnie Degiro generuje raport posortowany po dacie od operacji najnowszych, do najstarszych, potrzebujemy odwrócić tę kolejność, albo w arkuszu kalkulacyjnym, albo BASHem:
```
tac Transactions.csv > trx_tmp.csv
head -n -1 trx_tmp.csv > Transactions.csv
rm trx_tmp.csv
```

Odpal sesję w bazie użytkowikiem stockprofit, stwórz tabelę źródłową, załaduj to niej raport Degiro:
```
mysql stockprofit -ustockprofit
create table input(date DATE, time date, stock_name varchar(150), ISIN varchar(20), stock_market varchar(7), stock_no int, currency1 varchar(3), stock_rate float, currency2 varchar(3), trx_local_value float, currency3 varchar(3), trx_value_pln float, exchange_rate float, currency4 varchar(3), degiro_fee float, currency5 varchar(3), total_cost float);

create table sales (date date, stock_name varchar(150), sale_price_pln float, sale_value_pln float, sold_stock_no int, purchase_value_pln float, profit float);

load data infile '/var/lib/mysql/stockprofit/Transactions.csv' into table input 
FIELDS TERMINATED BY ',' 
IGNORE 1 LINES
(@c1, time, stock_name, ISIN, stock_market, stock_no, currency1, stock_rate, currency2, trx_local_value, currency3, trx_value_pln, exchange_rate, currency4, degiro_fee, currency5, total_cost) 
SET date = str_to_date(@c1, '%d-%m-%Y')
;
```

Teraz trzeba sprawdzić poprawność wgranych danych - najczęstszy błąd: przecinek w nazwie akcji, który rozbija ilość kolumn w danym wierszu.
```
select * from input where stock_no = 0;
select * from input where LENGTH(ISIN) <> 12;
````
Jeśli któraś z powyższych kwerend zwraca wynik inny niż 0, dane wejściowe prawdopodobnie wymagają poprawki. Usuń nadmiarowe przecinki lub inne niespodzianki, przeczyść tabelę (`delete from input;`) i załaduj dane ponownie (`load data infile ...`).

Skoro plik Transactions.csv został przeczyszczony, wracamy do BASHa i generujemy komendy do stworzenia tabel per firmy, przy okazji usuwając z nich cudzysłowy
```
awk -F ',' ' {print $3}' Transactions.csv | sort | uniq > table_list.txt
sed -i 's/\"//g' table_list.txt
sed -i "s/'//g" table_list.txt

IFS=$'\n'
for name in `cat table_list.txt`; do echo "create table \`$name\` (ID int NOT NULL AUTO_INCREMENT PRIMARY KEY, date date, stock_name varchar(150), trx_value_pln float, available_stock_no int, orig_stock_no int, purchase_price_pln float);" >> table_list.sql; done;
mysql -ustockprofit stockprofit < table_list.sql
```
Przy okazji, warto w tym miejscu przygotować sobie komendy to czyszczenia tych wszystkich tabel, gdyby skrypt po drodze się gdzieś wysypał, albo gdy zaktualizujemy dane źródłowe. Wykorzystujemy stworzony przed chwilą plik `table_list.txt`.
```
for name in `cat table_list.txt`; do echo "delete from  \`$name\`;" >> clear_tables.sql; done;
echo "delete from sales;" >> clear_tables.sql
```
Jeśli trzeba będzie przeczyścić tabele, `mysql -ustockprofit stockprofit < clear_tables.sql`.

Zweryfikuj poprawne stworzenie tabel  przy pomocy `show tables` odpalonym w bazie stockprofit - powinieneś zobaczyć tyle i takie tabele, ile i jakimi akcjami obracałeś.

## Odpal program
Jedyna zależność skryptu to pymysql, `pip install pymysql`, globalnie lub w śrdowisku virtualnym powinno załatwić sprawę.
`python stock_profit.py`

## Analizuj
Np.
```
select sum(profit) from sales where YEAR(date) = 2017;
select YEAR(date), sum(profit) from sales where stock_name = 'CI GAMES SA' group by YEAR(date);
```
