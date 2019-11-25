SUM# Kalkulator zysków / strat Degiro
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

Wygeneruj raport transakcji w Degiro (od początku przygody z brokerem - zakładla "Transakcje" w panelu Degiro), w formacie CSV.
Wrzuć plik z transakcjami (**Transactions.csv**) do katalogu bazy stockprofit
#### Ubuntu
/var/lib/mysql-files/
#### Fedora / starszy MySQL
 (/var/lib/mysql/stockprofit/)
#### Jak sprawdzić
`show variables like '%secure_file_priv%';` pokaże, który katalog wskazują zmienne Twojej bazy

## Załaduj raport transakcji degiro do źródłowej tabeli, wygeneruj tabele dla poszczególnych firm.

Domyślnie Degiro generuje raport posortowany po dacie od operacji najnowszych, do najstarszych, potrzebujemy odwrócić tę kolejność, albo w arkuszu kalkulacyjnym, albo BASHem:
```
tac Transactions.csv > trx_tmp.csv
head -n -1 trx_tmp.csv > Transactions.csv
rm trx_tmp.csv
```

Szybkie sprawdzenie, czy nie pojawiają się nazwy akcji z przecinkami (i ich usunięcie):
```
grep ", " Transactions.csv
sed -i 's/, / /g' Transactions.csv
```

Odpal sesję w bazie użytkowikiem stockprofit, stwórz tabelę źródłową, załaduj to niej raport Degiro:
```
mysql stockprofit -ustockprofit
create table input(date DATE, time date, stock_name varchar(150), ISIN varchar(20), stock_market varchar(7), stock_no int, stock_currency varchar(3), stock_rate DOUBLE, trx_currency varchar(3), trx_local_value DOUBLE, target_currency varchar(3), trx_target_value DOUBLE, exchange_rate DOUBLE, fee_currency varchar(3), degiro_fee DOUBLE, total_currency varchar(3), total_cost DOUBLE, trx_id varchar(40));

create table sales (date date, stock_name varchar(150), sale_price DOUBLE, sale_currency varchar(3), sale_value DOUBLE, sold_stock_no int, purchase_value DOUBLE, profit DOUBLE);

load data infile '/var/lib/mysql-files/Transactions.csv' into table input
FIELDS TERMINATED BY ',' (@c1, @c2, stock_name, ISIN, stock_market, stock_no, stock_currency, stock_rate, trx_currency, trx_local_value, target_currency, trx_target_value, @rate, fee_currency, @fee, total_currency, total_cost, trx_id)
SET date = str_to_date(@c1, '%d-%m-%Y'),
time = NULL,
exchange_rate = NULLIF(@rate, ''),
degiro_fee = NULLIF(@fee, '');
```

Teraz trzeba sprawdzić poprawność wgranych danych - najczęstszy błąd: przecinek w nazwie akcji, który rozbija ilość kolumn w danym wierszu.
```
select * from input where stock_no = 0;
select * from input where LENGTH(ISIN) <> 12;
````
Jeśli któraś z powyższych kwerend zwraca wynik inny niż 0, dane wejściowe prawdopodobnie wymagają poprawki. Usuń nadmiarowe przecinki lub inne niespodzianki, przeczyść tabelę (`delete from input;`) i załaduj dane ponownie (`load data infile ...`).

Czasem sprawę czyszczenia załatwia szybki sed: `sed -i 's/, / /g' Transactions.csv`

Skoro plik Transactions.csv został przeczyszczony, wracamy do BASHa i generujemy komendy do stworzenia tabel per firmy, przy okazji usuwając z nich cudzysłowy
```
awk -F ',' ' {print $3}' Transactions.csv | sort | uniq > table_list.txt
sed -i 's/\"//g' table_list.txt
sed -i "s/'//g" table_list.txt

IFS=$'\n'
for name in `cat table_list.txt`; do echo "create table \`$name\` (ID int NOT NULL AUTO_INCREMENT PRIMARY KEY, date date, stock_name varchar(150), trx_value DOUBLE, stock_currency varchar(3), available_stock_no int, orig_stock_no int, purchase_price DOUBLE);" >> table_list.sql; done;
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
1. Jak poszedł mi dany rok?
2. Jak poszły mi ostatnie lata?
3. Jaki osiągnąłem zysk na wybranych akcjach na przestrzeni lat?
4. Na jaką kwotę dokonałem sprzedaży w danym roku?


```
1. SELECT YEAR(date), sale_currency, ROUND(SUM(profit)) FROM sales WHERE YEAR(date) = 2019 GROUP BY YEAR(date), sale_currency;
2. SELECT  YEAR(date), sale_currency, ROUND(SUM(profit)) FROM sales GROUP BY YEAR(date), sale_currency;
3. SELECT stock_name, sale_currency, ROUND(SUM(profit)) FROM sales  GROUP BY stock_name, sale_currency;
5. SELECT ROUND(SUM(trx_local_value)), stock_currency FROM input where YEAR(DATE) = 2017 AND trx_local_value > 0 GROUP BY stock_currency;
```
Powyższe wyliczenia nie uwzględniają opłat Degiro, te można zliczyć z tabeli input np.
```
select ROUND(SUM(degiro_fee)) from input where YEAR(date) = 2017;
```
