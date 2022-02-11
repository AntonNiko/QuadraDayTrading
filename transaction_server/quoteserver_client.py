#!/usr/bin/env python3
import socket

HOST = '192.168.4.2'
PORT = 4444

class QuoteServerClient():

    @staticmethod
    def get_quote(symbol, username):
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

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(str.encode('{} {}\n'.format(symbol, username)))
            data = s.recv(1024)

        data_str_trimmed = data.decode('utf-8')[:-1]
        price, symbol, username, timestamp, cryptographickey = data_str_trimmed.split(',')

        return float(price), symbol, username, int(timestamp), cryptographickey
