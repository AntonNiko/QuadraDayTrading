#!/usr/bin/env python3
import requests
import sys

TX_SERVER_HOST = 'localhost'
TX_SERVER_PORT = 8000
TX_SERVER_URL  = 'http://{}:{}'.format(TX_SERVER_HOST, TX_SERVER_PORT)

# User must provide workload file.
if len(sys.argv) < 2:
    raise Exception('Must provide filename to program.')

if len(sys.argv) > 2:
    raise Exception('Too many arguments.')

# Open workload file
filename = sys.argv[1]
with open(filename, 'r') as f:
    lines = f.readlines()

for line in lines:
    # Parse command and parameters from each line.
    commands_str = line.split(' ')[1]
    commands = commands_str.split(',')
    
    command = commands[0]
    if command == 'ADD':
        user_id = commands[1]
        amount  = commands[2]
        r = requests.get('{}/commands/add?userid={}&amount={}'.format(TX_SERVER_URL, user_id, amount))
        assert r.status_code == 200

    elif command == 'QUOTE':
        user_id = commands[1]
        stock_symbol = commands[2]
        r = requests.get('{}/commands/quote?userid={}&stocksymbol={}'.format(TX_SERVER_URL, user_id, stock_symbol))
        assert r.status_code == 200

    elif command == 'BUY':
        user_id = commands[1]
        stock_symbol = commands[2]
        amount = commands[3]
        r = requests.get('{}/commands/buy?userid={}&stocksymbol={}&amount={}'.format(TX_SERVER_URL, user_id, stock_symbol, amount))
        assert r.status_code == 200

    elif command == 'COMMIT_BUY':
        user_id = commands[1]
        r = requests.get('{}/commands/commit_buy?userid={}'.format(TX_SERVER_URL, user_id))
        assert r.status_code == 200

    elif command == 'CANCEL_BUY':
        user_id = commands[1]
        r = requests.get('{}/commands/cancel_buy?userid={}'.format(TX_SERVER_URL, user_id))
        assert r.status_code == 200

    elif command == 'SELL':
        user_id = commands[1]
        stock_symbol = commands[2]
        amount = commands[3]
        r = requests.get('{}/commands/sell?userid={}&stocksymbol={}&amount={}'.format(TX_SERVER_URL, user_id, stock_symbol, amount))
        assert r.status_code == 200

    elif command == 'COMMIT_SELL':
        user_id = commands[1]
        r = requests.get('{}/commands/commit_sell?userid={}'.format(TX_SERVER_URL, user_id))
        assert r.status_code == 200

    elif command == 'CANCEL_SELL':
        user_id = commands[1]
        r = requests.get('{}/commands/cancel_sell?userid={}'.format(TX_SERVER_URL, user_id))
        assert r.status_code == 200

    elif command == 'SET_BUY_AMOUNT':
        user_id = commands[1]
        stock_symbol = commands[2]
        amount = commands[3]
        r = requests.get('{}/commands/set_buy_amount?userid={}&stocksymbol={}&amount={}'.format(TX_SERVER_URL, user_id, stock_symbol, amount))
        assert r.status_code == 200

    elif command == 'CANCEL_SET_BUY':
        user_id = commands[1]
        stock_symbol = commands[2]
        r = requests.get('{}/commands/cancel_set_buy?userid={}&stocksymbol={}'.format(TX_SERVER_URL, user_id, stock_symbol))
        assert r.status_code == 200

    elif command == 'SET_BUY_TRIGGER':
        user_id = commands[1]
        stock_symbol = commands[2]
        amount = commands[3]
        r = requests.get('{}/commands/set_buy_trigger?userid={}&stocksymbol={}&amount={}'.format(TX_SERVER_URL, user_id, stock_symbol, amount))
        assert r.status_code == 200

    elif command == 'DUMPLOG':
        if len(commands) == 2:
            filename = commands[1].lstrip('./')[:-1]
            r = requests.get('{}/commands/dumplog?filename={}'.format(TX_SERVER_URL, filename))
            assert r.status_code == 200

        elif len(commands) == 3:
            user_id = commands[1]
            filename = commands[2].lstrip('./')[:-1]
            r = requests.get('{}/commands/dumplog?userid={}&filename={}'.format(TX_SERVER_URL, user_id, filename))
            assert r.status_code == 200
