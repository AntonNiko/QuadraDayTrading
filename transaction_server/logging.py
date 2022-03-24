#!/usr/bin/env python3
from enum import Enum
import socket
import time
from transaction_server.db import DB
import xml.etree.ElementTree as ET

MIN_TIMESTAMP_LIMIT = 1641024000000
MAX_TIMESTAMP_LIMIT = 1651388400000
SERVER_NAME = socket.gethostname()
db = DB()

# Logging functionality for transaction server. Validation is performed
# according to the following:
# https://www.ece.uvic.ca/~seng468/ProjectWebSite/logfile_xsd.html


class LogType(Enum):
    USER_COMMAND = 'userCommand'
    QUOTE_SERVER = 'quoteServer'
    ACCOUNT_TRANSACTION = 'accountTransaction'
    SYSTEM_EVENT = 'systemEvent'
    ERROR_EVENT = 'errorEvent'
    DEBUG_EVENT = 'debugEvent'

class CommandType(Enum):
    ADD = 'ADD'
    QUOTE = 'QUOTE'
    BUY = 'BUY'
    COMMIT_BUY = 'COMMIT_BUY'
    CANCEL_BUY = 'CANCEL_BUY'
    SELL = 'SELL'
    COMMIT_SELL = 'COMMIT_SELL'
    CANCEL_SELL = 'CANCEL_SELL'
    SET_BUY_AMOUNT = 'SET_BUY_AMOUNT'
    CANCEL_SET_BUY = 'CANCEL_SET_BUY'
    SET_BUY_TRIGGER = 'SET_BUY_TRIGGER'
    SET_SELL_AMOUNT = 'SET_SELL_AMOUNT'
    SET_SELL_TRIGGER = 'SET_SELL_TRIGGER'
    CANCEL_SET_SELL = 'CANCEL_SET_SELL'
    DUMPLOG = 'DUMPLOG'
    DISPLAY_SUMMARY = 'DISPLAY_SUMMARY'

def is_unix_timestamp_in_range(unix_timestamp_sec):
    assert type(unix_timestamp_sec) == int
    return (unix_timestamp_sec > MIN_TIMESTAMP_LIMIT) and (unix_timestamp_sec < MAX_TIMESTAMP_LIMIT)

def is_stock_symbol(symbol):
    assert type(symbol) == str
    return len(symbol) <= 3

class Logging():
    '''
    Every log has a timestamp and server name that this
    class fetches every time.
    '''

    @staticmethod
    def __log_transaction(log_type, log_params):
        # Ensure log timestamp, server, and type recorded
        log_params['logtype'] = log_type
        log_params['server'] = SERVER_NAME
        log_params['timestamp'] = int(time.time() * 1000) # ms

        inserted_id = db.add_log(log_params)
        return inserted_id

    @staticmethod
    def log_user_command(**log_params):
        # Validate format is correct, then record to database.
        assert 'transactionNum' in log_params
        assert 'command' in log_params

        assert type(log_params['transactionNum']) == int
        assert log_params['transactionNum'] > 0
        assert type(log_params['command']) == CommandType
        log_params['command'] = log_params['command'].value

        return Logging.__log_transaction(LogType.USER_COMMAND.value, log_params)

    @staticmethod
    def log_quote_server_hit(**log_params):
        # Validate format is correct, then record to database.
        assert 'transactionNum' in log_params
        assert 'price' in log_params
        assert 'stockSymbol' in log_params
        assert 'username' in log_params
        assert 'quoteServerTime' in log_params
        assert 'cryptokey' in log_params

        assert type(log_params['transactionNum']) == int
        assert log_params['transactionNum'] > 0
        assert type(log_params['price']) == float
        assert is_stock_symbol(log_params['stockSymbol'])
        assert type(log_params['username']) == str
        assert type(log_params['quoteServerTime']) == int
        assert type(log_params['cryptokey']) == str

        return Logging.__log_transaction(LogType.QUOTE_SERVER.value, log_params)

    @staticmethod
    def log_account_transaction(**log_params):
        # Validate format is correct, then record to database.
        assert 'transactionNum' in log_params
        assert 'action' in log_params
        assert 'username' in log_params
        assert 'funds' in log_params

        assert type(log_params['transactionNum']) == int
        assert log_params['transactionNum'] > 0
        assert type(log_params['action']) == str
        assert type(log_params['username']) == str
        assert type(log_params['funds']) == float

        return Logging.__log_transaction(LogType.ACCOUNT_TRANSACTION.value, log_params)

    @staticmethod
    def log_system_event(**log_params):
        # Validate format is correct, then record to database.
        assert 'transactionNum' in log_params
        assert 'command' in log_params

        assert type(log_params['transactionNum']) == int
        assert log_params['transactionNum'] > 0
        assert type(log_params['command']) == CommandType
        log_params['command'] = log_params['command'].value

        return Logging.__log_transaction(LogType.SYSTEM_EVENT.value, log_params)

    @staticmethod
    def log_error_event(**log_params):
        # Validate format is correct, then record to database.
        assert 'transactionNum' in log_params
        assert 'command' in log_params

        assert type(log_params['transactionNum']) == int
        assert log_params['transactionNum'] > 0
        assert type(log_params['command']) == CommandType
        log_params['command'] = log_params['command'].value

        return Logging.__log_transaction(LogType.ERROR_EVENT.value, log_params)

    @staticmethod
    def log_debug(**log_params):
        # Validate format is correct, then record to database.
        assert 'transactionNum' in log_params
        assert 'command' in log_params

        assert type(log_params['transactionNum']) == int
        assert log_params['transactionNum'] > 0
        assert type(log_params['command']) == CommandType
        log_params['command'] = log_params['command'].value

        return Logging.__log_transaction(LogType.DEBUG_EVENT.value, log_params)

    @staticmethod
    def convert_dicts_to_xml(logs):
        assert type(logs) == list

        # For each log entry, append the XML element with corresponding elements.
        xml_root = ET.Element('log')
        for log_entry in logs:
            # Add xml tag with correct name
            xml_log_element = ET.SubElement(xml_root, log_entry['logtype'])

            for log_field in list(log_entry.keys()):
                if log_field == 'logtype': continue
                ET.SubElement(xml_log_element, log_field).text = str(log_entry[log_field])

        tree = ET.ElementTree(xml_root)
        ET.indent(tree, space='\t', level=0)
        return tree
