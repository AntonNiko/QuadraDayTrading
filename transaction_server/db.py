from pymongo import MongoClient

HOST = '127.0.0.1'
DB_PORT = 27018

class DB():
    def __init__(self):
        self.client = MongoClient(host=HOST, port=DB_PORT)
        self.db = self.client.day_trading

    def does_account_exist(self, user_id):
        '''
        Determines if an account exists for the specified user_id. Returns tru
        if it exists, False otherwise.
        '''
        assert type(user_id) == str

        result = self.db.accounts.find_one({"userid": user_id})
        print(result)


    def create_account(self, user_id):
        '''
        Create an account with specified user_id. If account already exsits, raise
        exception. If successful, newly created account has balance 0.
        '''

    def add_money_to_account(self, user_id, amount):
        '''
        Adds the specified amount of money to user_id's account.
        '''
        assert type(user_id) == str
        assert type(amount) == float

        # transaction_id = self.db.accounts.