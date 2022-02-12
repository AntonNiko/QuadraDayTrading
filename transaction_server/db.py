#!/usr/bin/env python3
from pymongo import MongoClient

HOST = 'db'
DB_PORT = 27017
USERNAME = 'root'
PASSWORD = 'rootpassword'

class DB():
    def __init__(self):
        self.client = MongoClient(host=HOST, port=DB_PORT) # , username=USERNAME, password=PASSWORD
        self.db = self.client.day_trading

    def does_account_exist(self, user_id):
        '''
        Determines if an account exists for the specified user_id. Returns tru
        if it exists, False otherwise.
        '''
        assert type(user_id) == str

        result = self.get_account_details(user_id)
        if result is None:
            return False
        return True

    def create_account(self, user_id):
        '''
        Create an account with specified user_id. If account already exsits, raise
        exception. If successful, newly created account has balance 0. Returns inserted 
        object ID
        '''
        assert type(user_id) == str

        insert_one_result = self.db.accounts.insert_one({'userid': user_id, 'balance': 0.0})
        return insert_one_result.inserted_id

    def add_money_to_account(self, user_id, amount):
        '''
        Adds the specified amount of money to user_id's account.
        '''
        assert type(user_id) == str
        assert type(amount) == float

        update_result = self.db.accounts.update_one({'userid': user_id}, {'$inc': {'balance': amount}})
        return update_result.matched_count, update_result.modified_count

    def get_account_details(self, user_id):
        '''
        Get details for the account specified by the user_id. Returns dict if account found,
        otherwise None.
        '''
        assert type(user_id) == str

        result = self.db.accounts.find_one({'userid': user_id})
        return result

    def add_transaction_log(self, log):
        '''
        Appends transaction log to the logs collection. This method does not 
        validate the log format past it being a dictionary.
        '''
        assert type(log) == dict

        insert_one_result = self.db.logs.insert_one(log)
        return insert_one_result.inserted_id

    def add_pending_transaction(self, user_id, stock_symbol, amount, unix_timestamp):
        '''
        Adds the provided transaction as a pending transaction the user
        needs to confirm.
        '''
        assert type(user_id) == str
        assert type(stock_symbol) == str
        assert type(amount) == float
        assert type(unix_timestamp) == float
        
        document_to_insert = {'userid': user_id, 'stock_symbol': stock_symbol, 'amount': amount, 'timestamp': unix_timestamp}
        insert_one_result = self.db.pending_transactions.insert_one(document_to_insert)
        return insert_one_result.inserted_id

    def get_pending_transaction(self, user_id):
        '''
        Returns the pending transaciton, if one exists.
        '''
        assert type(user_id) == str

        result = self.db.pending_transactions.find_one({'userid': user_id})
        return result

    def delete_pending_transaction(self, user_id):
        '''
        Deletes the pending transaction associated with the user ID, fi one 
        exists.
        '''
        assert type(user_id) == str

        delete_result = self.db.pending_transactions.delete_one({'userid': user_id})
        return delete_result.deleted_count

    def close_connection(self):
        self.client.close()