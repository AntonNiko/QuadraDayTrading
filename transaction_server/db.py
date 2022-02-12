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

        result = self.db.accounts.find_one({"userid": user_id})
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

    def close_connection(self):
        self.client.close()