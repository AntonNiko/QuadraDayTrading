from json import dumps, loads
import redis

cache = redis.StrictRedis(host='redis', port=6379)

CACHE_PENDING_BUY_TX_NAME = 'pending_buy_transactions'
CACHE_PENDING_SELL_TX_NAME = 'pending_sell_transactions'

class Cache():
    def __init__(self):
        pass

    def add_pending_transaction(self, user_id, tx_type, stock_symbol, amount, unix_timestamp):
        '''
        Adds the provided transaction as a pending transaction the user
        needs to confirm.
        '''
        assert type(user_id) == str
        assert tx_type in ['BUY', 'SELL']
        assert type(stock_symbol) == str
        assert type(amount) == float
        assert type(unix_timestamp) == float

        element_to_insert = {'tx_type': tx_type, 'stock_symbol': stock_symbol, 'amount': amount, 'timestamp': unix_timestamp}

        if tx_type == 'BUY':
            cache.hset(CACHE_PENDING_BUY_TX_NAME, user_id, dumps(element_to_insert))
        else:
            cache.hset(CACHE_PENDING_SELL_TX_NAME, user_id, dumps(element_to_insert))

    def get_pending_transaction(self, user_id, tx_type):
        '''
        Returns the pending transaction, if one exists.
        '''
        if tx_type == 'BUY':
            value = cache.hget(CACHE_PENDING_BUY_TX_NAME, user_id)
        else:
            value = cache.hget(CACHE_PENDING_SELL_TX_NAME, user_id)

        # Convert to JSON
        if value:
            return loads(value)
        return value

    def delete_pending_transaction(self, user_id, tx_type):
        '''
        Deletes the pending transaction associated with the user ID, if one
        exists.
        '''     
        if tx_type == 'BUY':
            return cache.hdel(CACHE_PENDING_BUY_TX_NAME, user_id)
        else:
            return cache.hdel(CACHE_PENDING_SELL_TX_NAME, user_id)



