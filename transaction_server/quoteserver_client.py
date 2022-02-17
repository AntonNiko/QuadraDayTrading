#!/usr/bin/env python3
import socket
from transaction_server.logging import Logging

HOST = '192.168.4.2'
PORT = 4444

class QuoteServerClient():

    @staticmethod
    def get_quote(symbol, username, tx_num):
        '''
        Get price of stock by specified symbol.

        Parameter:
            symbol (str): The stock's symbol
            username (str): Username associated with originating request
        Returns
            price (float): Stock price
            symbol (str): Symbol returned.
            username (str): Returned username (?)
            timestamp (int): Time request was processed (UNIX timestamp)
            cryptographickey (str): (?)
        '''
        assert type(symbol) == str
        assert type(username) == str
        assert type(tx_num) == int

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(str.encode('{} {}\n'.format(symbol, username)))
            data = s.recv(1024)

        data_str_trimmed = data.decode('utf-8')[:-1]
        price, symbol, username, timestamp, cryptokey = data_str_trimmed.split(',')

        # Log as QuoteServerType
        Logging.log_quote_server_hit(transactionNum=tx_num, price=price, stockSymbol=symbol, username=username, quoteServerTime=timestamp, cryptokey=cryptokey)

        return float(price), symbol, username, int(timestamp), cryptokey
