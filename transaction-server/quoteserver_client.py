#!/usr/bin/env python3
import socket

HOST = '192.168.4.2'
PORT = 4444

class QuoteServerClient():

    @staticmethod
    def get_quote(symbol):
        '''
        Get price of stock by specified symbol.

        Parameter:
            symbol (str): The stock's symbol
        Returns
            price (float): Stock price
        '''

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(str.encode('SYM {}'.format(symbol)))
            data = s.recv(1024)

