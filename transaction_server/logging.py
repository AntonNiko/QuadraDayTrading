#!/usr/bin/env python3
from enum import Enum
from transaction_server.db import DB
import xml.etree.ElementTree as ET

MIN_TIMESTAMP_LIMIT = 1641024000000
MAX_TIMESTAMP_LIMIT = 1651388400000

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
    SET_SELL_AMOUNT = 'SET_SELL_TRIGGER'
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
    @staticmethod
    def __log_transaction(log_dict):
        db = DB()
        inserted_id = db.add_log(log_dict)
        db.close_connection()
        return inserted_id     

    @staticmethod
    def log_user_command(log_dict):
        # Validate format is correct, then record to database.
        assert 'timestamp' in log_dict
        assert 'server' in log_dict
        assert 'transactionNum' in log_dict
        assert 'command' in log_dict

        assert is_unix_timestamp_in_range(log_dict['timestamp'])
        assert type(log_dict['server']) == str
        assert type(log_dict['transactionNum']) == int
        assert log_dict['transactionNum'] > 0
        assert type(log_dict['command']) == CommandType

        # Ensure log type recorded
        log_dict['logtype'] = LogType.USER_COMMAND.value

        return Logging.__log_transaction(log_dict)

    @staticmethod
    def log_quote_server_hit(log_dict):
        # Validate format is correct, then record to database.
        assert 'timestamp' in log_dict
        assert 'server' in log_dict
        assert 'transactionNum' in log_dict
        assert 'price' in log_dict
        assert 'stockSymbol' in log_dict
        assert 'username' in log_dict
        assert 'quoteServerTime' in log_dict
        assert 'cryptokey' in log_dict

        assert is_unix_timestamp_in_range(log_dict['timestamp'])
        assert type(log_dict['server']) == str
        assert type(log_dict['transactionNum']) == int
        assert log_dict['transactionNum'] > 0
        assert type(log_dict['price']) == float
        assert is_stock_symbol(log_dict['stockSymbol'])
        assert type(log_dict['username']) == str
        assert type(log_dict['quoteServerTime']) == int
        assert type(log_dict['cryptokey']) == str

        # Ensure log type recorded
        log_dict['logtype'] = LogType.QUOTE_SERVER.value

        return Logging.__log_transaction(log_dict)

    @staticmethod
    def log_account_transaction(log_dict):
        # Validate format is correct, then record to database.
        assert 'timestamp' in log_dict
        assert 'server' in log_dict
        assert 'transactionNum' in log_dict
        assert 'action' in log_dict
        assert 'username' in log_dict
        assert 'funds' in log_dict

        assert is_unix_timestamp_in_range(log_dict['timestamp'])
        assert type(log_dict['server']) == str
        assert type(log_dict['transactionNum']) == int
        assert log_dict['transactionNum'] > 0
        assert type(log_dict['action']) == str
        assert type(log_dict['username']) == str
        assert type(log_dict['funds']) == float

        # Ensure log type recorded
        log_dict['logtype'] = LogType.ACCOUNT_TRANSACTION.value

        return Logging.__log_transaction(log_dict)       

# TODO: All 3 calls below are the same, centralize logic.

    @staticmethod
    def log_system_event(log_dict):
        # Validate format is correct, then record to database.
        assert 'timestamp' in log_dict
        assert 'server' in log_dict
        assert 'transactionNum' in log_dict       
        assert 'command' in log_dict 

        assert is_unix_timestamp_in_range(log_dict['timestamp'])
        assert type(log_dict['server']) == str
        assert type(log_dict['transactionNum']) == int
        assert log_dict['transactionNum'] > 0
        assert type(log_dict['command']) == CommandType

        # Ensure log type recorded
        log_dict['logtype'] = LogType.SYSTEM_EVENT.value

        return Logging.__log_transaction(log_dict)  

    @staticmethod
    def log_error_event(log_dict):
        # Validate format is correct, then record to database.
        assert 'timestamp' in log_dict
        assert 'server' in log_dict
        assert 'transactionNum' in log_dict       
        assert 'command' in log_dict 

        assert is_unix_timestamp_in_range(log_dict['timestamp'])
        assert type(log_dict['server']) == str
        assert type(log_dict['transactionNum']) == int
        assert log_dict['transactionNum'] > 0
        assert type(log_dict['command']) == CommandType

        # Ensure log type recorded
        log_dict['logtype'] = LogType.ERROR_EVENT.value

        return Logging.__log_transaction(log_dict) 

    @staticmethod
    def log_debug(log_dict):
        # Validate format is correct, then record to database.
        assert 'timestamp' in log_dict
        assert 'server' in log_dict
        assert 'transactionNum' in log_dict       
        assert 'command' in log_dict 

        assert is_unix_timestamp_in_range(log_dict['timestamp'])
        assert type(log_dict['server']) == str
        assert type(log_dict['transactionNum']) == int
        assert log_dict['transactionNum'] > 0
        assert type(log_dict['command']) == CommandType

        # Ensure log type recorded
        log_dict['logtype'] = LogType.DEBUG_EVENT.value

        return Logging.__log_transaction(log_dict)

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

        return ET.ElementTree(xml_root)