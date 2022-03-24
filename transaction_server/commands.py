#!/usr/bin/env python3
'''
This blueprint provides an API to process all user commands specified in:
https://www.ece.uvic.ca/~seng468/ProjectWebSite/Commands.html
'''
from bson import json_util
from flask import Blueprint, jsonify, request
import json
import time
from transaction_server.cache import Cache
from transaction_server.db import DB
from transaction_server.logging import Logging, CommandType
from transaction_server.quoteserver_client import QuoteServerClient

bp = Blueprint('commands', __name__, url_prefix='/commands')
cache = Cache()

@bp.route('/add', methods=['GET'])
def add():
    '''
	Add the given amount of money to the user's account. GET parameters are:
        command_num: Command number
        userid: Username
        amount: Amount to add to username's account.

    Pre-conditions:
        None
    Post-conditions:
        The user's account is increased by the amount of money specified
    '''
    args = dict(request.args)
    response = {'status': None}

    try:
        assert 'tx_num' in args, 'tx_num paramter not provided'
        assert 'userid' in args, 'userid parameter not provided'
        assert 'amount' in args, 'amount parameter not provided'

        # If account does not exist, create.
        tx_num = int(args['tx_num'])
        user_id = args['userid']
        amount = float(args['amount'])

        Logging.log_debug(transactionNum=tx_num, command=CommandType.ADD, username=user_id)
        db = DB()
        if not db.does_account_exist(user_id):
            db.create_account(user_id)

        matched_count, modified_count = db.add_money_to_account(user_id, amount)

        # Log as AccountTransactionType with updated balance
        Logging.log_account_transaction(transactionNum=tx_num, action='add', username=user_id, funds=float(db.get_account(user_id)['balance']))

        db.close_connection()
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=args.get('tx_num', 99999), command=CommandType.ADD, errorMessage=str(err))
        return jsonify(response)

    Logging.log_user_command(transactionNum=tx_num, command=CommandType.ADD, username=user_id)
    response['status'] = 'success'
    response['matched_count'] = matched_count
    response['modified_count'] = modified_count
    return jsonify(response)

@bp.route('/quote', methods=['GET'])
def quote():
    '''
    Get the current quote for the stock for the specified user.

    Pre-conditions:
        None
    Post-conditions:
        The current price of the specified stock is displayed to the user
    '''
    args = dict(request.args)
    response = {'status': None}

    try:
        assert 'tx_num' in args, 'tx_num paramter not provided'
        assert 'userid' in args, 'userid parameter not provided'
        assert 'stocksymbol' in args, 'stocksymbol parameter not provided'

        tx_num = int(args['tx_num'])
        user_id = args['userid']
        stock_symbol = args['stocksymbol']

        Logging.log_debug(transactionNum=tx_num, command=CommandType.QUOTE, username=user_id)
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=args.get('tx_num', 99999), command=CommandType.QUOTE, errorMessage=str(err))
        return jsonify(response)

    price, symbol, username, timestamp, cryptokey = QuoteServerClient.get_quote(stock_symbol, user_id, tx_num)
    Logging.log_user_command(transactionNum=tx_num, command=CommandType.QUOTE, username=user_id)
    response['status'] = 'success'
    response['price'] = price
    response['symbol'] = symbol
    response['username'] = username
    response['timestamp'] = timestamp
    response['cryptokey'] = cryptokey
    return jsonify(response)

@bp.route('/buy', methods=['GET'])
def buy():
    '''
    Buy the dollar amount of the stock for the specified user at the current price.

    Pre-conditions:
        The user's account must be greater or equal to the amount of the purchase.
    Post-conditions:
        The user is asked to confirm or cancel the transaction
    '''
    args = dict(request.args)
    response = {'status': None}

    try:
        assert 'tx_num' in args, 'tx_num paramter not provided'
        assert 'userid' in args, 'userid parameter not provided'
        assert 'stocksymbol' in args, 'stocksymbol parameter not provided'
        assert 'amount' in args, 'amount parameter not provided'

        tx_num = int(args['tx_num'])
        userid = args['userid']
        stocksymbol = args['stocksymbol']
        amount = float(args['amount'])

        Logging.log_debug(transactionNum=tx_num, command=CommandType.BUY, username=userid)
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)
        return jsonify(response)

    # Ensure account exists and balance is sufficient.
    db = DB()

    if not db.does_account_exist(userid):
        response['status'] = 'failure'
        response['message'] = 'Account does not exist.'

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.BUY, errorMessage=response['message'])
        return jsonify(response)

    # Get account balance
    balance = db.get_account(userid)['balance']
    if balance < amount:
        response['status'] = 'failure'
        response['message'] = 'Not enough money in account to buy.'

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.BUY, errorMessage=response['message'])
        return jsonify(response)

    # Get quote for stock and determine nearest whole number of shares that can be bought.
    price, symbol, username, timestamp, cryptokey = QuoteServerClient.get_quote(args['stocksymbol'], args['userid'], tx_num)
    shares_to_buy = amount//price

    # Add transaction as pending confirmation from user & delete any previous pending transactions
    if db.get_pending_transaction(userid, 'BUY'):
        db.delete_pending_transaction(userid, 'BUY')
    db.add_pending_transaction(userid, 'BUY', stocksymbol, amount, time.time()) # (shares_to_buy * price)
    db.close_connection()

    Logging.log_user_command(transactionNum=tx_num, command=CommandType.BUY, username=args['userid'])

    response['status'] = 'success'
    response['message'] = 'Successfully registered pending transaction. Confirm buy within 60 seconds.'
    response['price'] = price
    response['shares_to_buy'] = shares_to_buy
    response['symbol'] = symbol
    response['username'] = username
    response['timestamp'] = timestamp
    response['cryptokey'] = cryptokey
    return jsonify(response)

@bp.route('/commit_buy', methods=['GET'])
def commit_buy():
    '''
	Commits the most recently executed BUY command.

    Pre-conditions:
        The user must have executed a BUY command within the previous 60 seconds.
    Post-conditions:
        (a) The user's cash account is decreased by the amount used to purchase the stock
        (b) the user's account for the given stock is increased by the purchase amount
    '''
    args = dict(request.args)
    response = {'status': None}

    try:
        assert 'tx_num' in args, 'tx_num paramter not provided'
        assert 'userid' in args, 'userid parameter not provided'

        tx_num = int(args['tx_num'])
        user_id = args['userid']

        Logging.log_debug(transactionNum=tx_num, command=CommandType.COMMIT_BUY, username=user_id)
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=args.get('tx_num', 99999), command=CommandType.COMMIT_BUY, errorMessage=response['message'])
        return jsonify(response)

    # Ensure latest buy command exists and is less than 60 seconds old.
    db = DB()

    pending_transaction = db.get_pending_transaction(user_id, 'BUY')
    if not pending_transaction:
        response['status'] = 'failure'
        response['message'] = 'No pending BUY transaction found.'

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.COMMIT_BUY, errorMessage=response['message'])
        return jsonify(response)

    original_timestamp = pending_transaction['timestamp']
    stock_symbol = pending_transaction['stock_symbol']
    amount = pending_transaction['amount'] # Total share value being bought.
    tx_type = pending_transaction['tx_type']
    db.log_transaction(user_id, tx_type, stock_symbol, amount, original_timestamp)

    current_timestamp = time.time()
    if (current_timestamp - original_timestamp) > 60:
        response['status'] = 'failure'
        response['message'] = 'Most recent BUY command is more than 60 seconds old.'

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.COMMIT_BUY, errorMessage=response['message'])
        return jsonify(response)

    # Delete pending transaction
    deleted_count = db.delete_pending_transaction(user_id, 'BUY')
    assert deleted_count == 1

    # Reduce account balance by specified amount
    matched_count, modified_count = db.remove_money_from_account(user_id, amount)
    assert matched_count == 1
    assert modified_count == 1

    # Log as AccountTransactionType with updated balance
    Logging.log_account_transaction(transactionNum=tx_num, action='remove', username=user_id, funds=float(db.get_account(user_id)['balance']))

    # Increase account amount of stock owned
    portfolio_matched_count, portfolio_modified_count = db.increase_stock_portfolio_amount(user_id, stock_symbol, amount)
    db.close_connection()

    Logging.log_user_command(transactionNum=tx_num, command=CommandType.COMMIT_BUY, username=user_id)

    response['status'] = 'success'
    response['message'] = 'Successfully commited BUY transaction for {} for amount {}'.format(stock_symbol, amount)
    response['matched_count'] = portfolio_matched_count
    response['modified_count'] = portfolio_modified_count
    return jsonify(response)


@bp.route('/cancel_buy', methods=['GET'])
def cancel_buy():
    '''
	Cancels the most recently executed BUY Command

    Pre-conditions:
        The user must have executed a BUY command within the previous 60 seconds
    Post-conditions:
        The last BUY command is canceled and any allocated system resources are reset and released.
    '''
    args = dict(request.args)
    response = {'status': None}

    try:
        assert 'tx_num' in args, 'tx_num paramter not provided'
        assert 'userid' in args, 'userid parameter not provided'

        tx_num = int(args['tx_num'])
        userid = args['userid']

        Logging.log_debug(transactionNum=tx_num, command=CommandType.CANCEL_BUY, username=userid)
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=args.get('tx_num', 99999), command=CommandType.CANCEL_BUY, errorMessage=response['message'])
        return jsonify(response)

    # Ensure latest buy command exists and is less than 60 seconds old.
    db = DB()

    pending_transaction = db.get_pending_transaction(userid, 'BUY')
    if not pending_transaction:
        response['status'] = 'failure'
        response['message'] = 'No pending BUY transaction found.'

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.CANCEL_BUY, errorMessage=response['message'])
        return jsonify(response)

    original_timestamp = pending_transaction['timestamp']

    current_timestamp = time.time()
    if (current_timestamp - original_timestamp) > 60:
        response['status'] = 'failure'
        response['message'] = 'Most recent BUY command is more than 60 seconds old.'

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.CANCEL_BUY, errorMessage=response['message'])
        return jsonify(response)

    Logging.log_user_command(transactionNum=tx_num, command=CommandType.CANCEL_BUY, username=userid)

    # Delete pending BUY transaction such that COMMIT_BUY will not find any pending transactions.
    deleted_count = db.delete_pending_transaction(userid, 'BUY')
    response['status'] = 'success'
    response['message'] = 'Successfully cancelled {} BUY transactions'.format(deleted_count)
    return jsonify(response)


@bp.route('/sell', methods=['GET'])
def sell():
    '''
    Sell the specified dollar mount of the stock currently held by the specified user at the current price.

    Pre-conditions:
        The user's account for the given stock must be greater than or equal to the amount being sold.
    Post-conditions:
        The user is asked to confirm or cancel the given transaction
    '''
    args = dict(request.args)
    response = {'status': None}

    try:
        assert 'tx_num' in args, 'tx_num paramter not provided'
        assert 'userid' in args, 'userid parameter not provided'
        assert 'stocksymbol' in args, 'stocksymbol parameter not provided'
        assert 'amount' in args, 'amount parameter not provided'

        tx_num = int(args['tx_num'])
        userid = args['userid']
        stocksymbol = args['stocksymbol']
        amount = float(args['amount'])

        Logging.log_debug(transactionNum=tx_num, command=CommandType.SELL, username=userid)
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=args.get('tx_num', 99999), command=CommandType.SELL, errorMessage=response['message'])
        return jsonify(response)

    # Ensure account exists and user owns enough stock to sell at the price specified.
    db = DB()

    if not db.does_account_exist(userid):
        response['status'] = 'failure'
        response['message'] = 'Account does not exist.'

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.SELL, errorMessage=response['message'])
        return jsonify(response)

    # Ensure user owns sufficient amount of stock at the current price.
    user_stocks = db.get_account(userid)['stocks']
    if stocksymbol not in user_stocks:
        response['status'] = 'failure'
        response['message'] = 'User does not own any {} stock'.format(stocksymbol)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.SELL, errorMessage=response['message'])
        return jsonify(response)

    # Get quote for stock and determine nearest whole number of shares that can be bought.
    price, symbol, username, timestamp, cryptokey = QuoteServerClient.get_quote(stocksymbol, userid, tx_num)
    total_share_value = amount * price

    if amount > user_stocks[stocksymbol]: # total_share_value
        response['status'] = 'failure'
        #response['message'] = 'Not enough stock owned at current price to sell. Current price: {}, Total share value: {}, Requested amount: {}'.format(price, total_share_value, amount)
        response['message'] = 'Not enough stock owned to sell'

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.SELL, errorMessage=response['message'])
        return jsonify(response)

    # Add transaction as pending confirmation from user.
    # TODO: Replace with Redis?
    # Delete any previous pending transactions
    if db.get_pending_transaction(userid, 'SELL'):
        db.delete_pending_transaction(userid, 'SELL')
    db.add_pending_transaction(userid, 'SELL', stocksymbol, amount, time.time())
    db.close_connection()

    Logging.log_user_command(transactionNum=tx_num, command=CommandType.SELL, username=userid)
    response['status'] = 'success'
    response['message'] = 'Successfully registered pending transaction. Confirm sell within 60 seconds.'
    response['price'] = price
    response['symbol'] = symbol
    response['username'] = username
    response['timestamp'] = timestamp
    response['cryptokey'] = cryptokey
    return jsonify(response)

@bp.route('/commit_sell', methods=['GET'])
def commit_sell():
    '''
	Commits the most recently executed SELL command

    Pre-conditions:
        The user must have executed a SELL command within the previous 60 seconds
    Post-conditions:
        (a) the user's account for the given stock is decremented by the sale amount
        (b) the user's cash account is increased by the sell amount
    '''
    args = dict(request.args)
    response = {'status': None}
    try:
        assert 'tx_num' in args, 'tx_num paramter not provided'
        assert 'userid' in args, 'userid parameter not provided'

        tx_num = int(args['tx_num'])
        user_id = args['userid']

        Logging.log_debug(transactionNum=tx_num, command=CommandType.COMMIT_SELL, username=user_id)
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=args.get('tx_num', 99999), command=CommandType.COMMIT_SELL, errorMessage=response['message'])
        return jsonify(response)

    # Ensure latest sell command exists and is less than 60 seconds old.
    db = DB()

    pending_transaction = db.get_pending_transaction(user_id, 'SELL')
    if not pending_transaction:
        response['status'] = 'failure'
        response['message'] = 'No pending SELL transaction found.'

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.COMMIT_SELL, errorMessage=response['message'])
        return jsonify(response)

    original_timestamp = pending_transaction['timestamp']
    stock_symbol = pending_transaction['stock_symbol']
    amount = pending_transaction['amount']
    tx_type = pending_transaction['tx_type']
    db.log_transaction(user_id, tx_type, stock_symbol, amount, original_timestamp)

    current_timestamp = time.time()
    if (current_timestamp - original_timestamp) > 60:
        response['status'] = 'failure'
        response['message'] = 'Most recent SELL command is more than 60 seconds old.'

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.COMMIT_SELL, errorMessage=response['message'])
        return jsonify(response)

    # Delete pending transaction
    deleted_count = db.delete_pending_transaction(user_id, 'SELL')
    assert deleted_count == 1

    # Decrease account amount of stock owned
    portfolio_matched_count, portfolio_modified_count = db.decrease_stock_portfolio_amount(user_id, stock_symbol, amount)
    db.close_connection()

    # Increase account balance by specified amount
    matched_count, modified_count = db.add_money_to_account(user_id, amount)
    assert matched_count == 1
    assert modified_count == 1

    # Log as AccountTransactionType with updated balance
    Logging.log_account_transaction(transactionNum=tx_num, action='add', username=user_id, funds=float(db.get_account(user_id)['balance']))

    Logging.log_user_command(transactionNum=tx_num, command=CommandType.COMMIT_SELL, username=user_id)
    response['status'] = 'success'
    response['message'] = 'Successfully commited SELL transaction for {} for amount {}'.format(stock_symbol, amount)
    response['matched_count'] = portfolio_matched_count
    response['modified_count'] = portfolio_modified_count
    return jsonify(response)

@bp.route('/cancel_sell', methods=['GET'])
def cancel_sell():
    '''
	Cancels the most recently executed SELL Command

    Pre-conditions:
        The user must have executed a SELL command within the previous 60 seconds
    Post-conditions:
        The last SELL command is canceled and any allocated system resources are reset and released.
    '''
    args = dict(request.args)
    response = {'status': None}

    try:
        assert 'tx_num' in args, 'tx_num paramter not provided'
        assert 'userid' in args, 'userid parameter not provided'

        tx_num = int(args['tx_num'])
        userid = args['userid']

        Logging.log_debug(transactionNum=tx_num, command=CommandType.CANCEL_SELL, username=userid)
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=args.get('tx_num', 99999), command=CommandType.CANCEL_SELL, errorMessage=response['message'])
        return jsonify(response)

    # Ensure latest sell command exists and is less than 60 seconds old.
    db = DB()

    pending_transaction = db.get_pending_transaction(userid, 'SELL')
    if not pending_transaction:
        response['status'] = 'failure'
        response['message'] = 'No pending SELL transaction found.'

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.CANCEL_SELL, errorMessage=response['message'])
        return jsonify(response)

    original_timestamp = pending_transaction['timestamp']

    current_timestamp = time.time()
    if (current_timestamp - original_timestamp) > 60:
        response['status'] = 'failure'
        response['message'] = 'Most recent SELL command is more than 60 seconds old.'

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.CANCEL_SELL, errorMessage=response['message'])
        return jsonify(response)

    Logging.log_user_command(transactionNum=tx_num, command=CommandType.CANCEL_SELL, username=userid)

    # Delete pending SELL transaction such that COMMIT_SELL will not find any pending transactions.
    deleted_count = db.delete_pending_transaction(userid, 'SELL')
    response['status'] = 'success'
    response['message'] = 'Successfully cancelled {} SELL transactions'.format(deleted_count)
    return jsonify(response)

@bp.route('/set_buy_amount', methods=['GET'])
def set_buy_amount():
    '''
    Sets a defined amount of the given stock to buy when the current stock price is less than or equal to the BUY_TRIGGER

    Pre-conditions:
        The user's cash account must be greater than or equal to the BUY amount at the time the transaction occurs
    Post-conditions:
        (a) a reserve account is created for the BUY transaction to hold the specified amount in reserve for when the transaction is triggered
        (b) the user's cash account is decremented by the specified amount
        (c) when the trigger point is reached the user's stock account is updated to reflect the BUY transaction.
    '''
    args = dict(request.args)
    response = {'status': None}

    try:
        assert 'tx_num' in args, 'tx_num paramter not provided'
        assert 'userid' in args, 'userid parameter not provided'
        assert 'stocksymbol' in args, 'stocksymbol parameter not provided'
        assert 'amount' in args, 'amount parameter not provided'

        tx_num = int(args['tx_num'])
        user_id = args['userid']
        stock_symbol = args['stocksymbol']
        amount = float(args['amount'])

        Logging.log_debug(transactionNum=tx_num, command=CommandType.SET_BUY_AMOUNT, username=user_id)
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=args.get('tx_num', 99999), command=CommandType.SET_BUY_AMOUNT, errorMessage=response['message'])
        return jsonify(response)

    # Ensure user has enough cash in their account.
    db = DB()
    balance = db.get_account(user_id)['balance']
    if balance < amount:
        response['status'] = 'failure'
        response['message'] = 'Not enough money in account for set buy amount.'

         # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.SET_BUY_AMOUNT, errorMessage=response['message'])
        return jsonify(response)

    # Remove money from account and set aside in reserve account.
    matched_count, modified_count = db.remove_money_from_account(user_id, amount)
    assert matched_count == 1
    assert modified_count == 1

    # TODO: Replace any other existing buy amounts or just increment?
    reserve_matched_count, reserve_modified_count = db.add_buy_reserve_amount(user_id, stock_symbol, amount)
    db.close_connection()

    Logging.log_user_command(transactionNum=tx_num, command=CommandType.SET_BUY_AMOUNT, username=user_id)
    response['status'] = 'success'
    response['matched_count'] = reserve_matched_count
    response['modified_count'] = reserve_modified_count
    return jsonify(response)

@bp.route('/cancel_set_buy', methods=['GET'])
def cancel_set_buy():
    '''
    Cancels a SET_BUY command issued for the given stock

    Pre-conditions:
        The must have been a SET_BUY Command issued for the given stock by the user
    Post-conditions:
        (a) All accounts are reset to the values they would have had had the SET_BUY Command not been issued
        (b) the BUY_TRIGGER for the given user and stock is also canceled.
    '''
    args = dict(request.args)
    response = {'status': None}

    try:
        assert 'tx_num' in args, 'tx_num paramter not provided'
        assert 'userid' in args, 'userid parameter not provided'
        assert 'stocksymbol' in args, 'stocksymbol parameter not provided'

        tx_num = int(args['tx_num'])
        user_id = args['userid']
        stock_symbol = args['stocksymbol']

        Logging.log_debug(transactionNum=tx_num, command=CommandType.CANCEL_SET_BUY, username=user_id)
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=args.get('tx_num', 99999), command=CommandType.CANCEL_SET_BUY, errorMessage=response['message'])
        return jsonify(response)

    # Ensure account exists
    db = DB()
    if not db.does_account_exist(user_id):
        response['status'] = 'failure'
        response['message'] = 'Account does not exist.'

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.CANCEL_SET_BUY, errorMessage=response['message'])
        return jsonify(response)

    # Cancel, or return that no reserve buys were found.
    cancel_matched, cancel_modified = db.unset_buy_reserve_amount(user_id, stock_symbol)
    if cancel_modified == 0:
        response['status'] = 'failure'
        response['message'] = 'No reserve accounts for stock {} and user {} found.'.format(stock_symbol, user_id)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.CANCEL_SET_BUY, errorMessage=response['message'])
        return jsonify(response)

    # Remove any buy triggers for that stock
    db.unset_trigger('BUY', user_id, stock_symbol)
    db.close_connection()

    Logging.log_user_command(transactionNum=tx_num, command=CommandType.CANCEL_SET_BUY, username=user_id)
    response['status'] = 'success'
    response['matched_count'] = cancel_matched
    response['modified_count'] = cancel_modified
    return jsonify(response)


@bp.route('/set_buy_trigger', methods=['GET'])
def set_buy_trigger():
    '''
    Sets the trigger point base on the current stock price when any SET_BUY will execute.

    Pre-conditions:
        The user must have specified a SET_BUY_AMOUNT prior to setting a SET_BUY_TRIGGER
    Post-conditions:
        The set of the user's buy triggers is updated to include the specified trigger
    '''
    args = dict(request.args)
    response = {'status': None}

    try:
        assert 'tx_num' in args, 'tx_num paramter not provided'
        assert 'userid' in args, 'userid parameter not provided'
        assert 'stocksymbol' in args, 'stocksymbol parameter not provided'
        assert 'amount' in args, 'amount parameter not provided'

        tx_num = int(args['tx_num'])
        user_id = args['userid']
        stock_symbol = args['stocksymbol']
        amount = float(args['amount'])

        Logging.log_debug(transactionNum=tx_num, command=CommandType.SET_BUY_TRIGGER, username=user_id)
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=args.get('tx_num', 99999), command=CommandType.SET_BUY_TRIGGER, errorMessage=response['message'])
        return jsonify(response)

    # Ensure set buy amount exists for user's stock.
    db = DB()
    if stock_symbol not in db.get_account(user_id)['reserve_buy']:
        response['status'] = 'failure'
        response['message'] = 'No buy reserve exists for stock {} for user {}'.format(stock_symbol, user_id)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.SET_BUY_TRIGGER, errorMessage=response['message'])
        return jsonify(response)

    db.set_trigger('BUY', user_id, stock_symbol, amount)
    db.close_connection()

    Logging.log_user_command(transactionNum=tx_num, command=CommandType.SET_BUY_TRIGGER, username=user_id)
    response['status'] = 'success'
    response['message'] = 'Successfully added trigger for user {} for stock {} at price {}'.format(user_id, stock_symbol, amount)
    return jsonify(response)


@bp.route('/set_sell_amount', methods=['GET'])
def set_sell_amount():
    '''
    Sets a defined amount of the specified stock to sell when the current stock price is equal or greater than the sell trigger point

    Pre-conditions:
        The user must have the specified amount of stock in their account for that stock.
    Post-conditions:
        A trigger is initialized for this username/stock symbol combination, but is not complete until SET_SELL_TRIGGER is executed.
    '''
    args = dict(request.args)
    response = {'status': None}

    try:
        assert 'tx_num' in args, 'tx_num paramter not provided'
        assert 'userid' in args, 'userid parameter not provided'
        assert 'stocksymbol' in args, 'stocksymbol parameter not provided'
        assert 'amount' in args, 'amount parameter not provided'

        tx_num = int(args['tx_num'])
        user_id = args['userid']
        stock_symbol = args['stocksymbol']
        amount = float(args['amount'])

        Logging.log_debug(transactionNum=tx_num, command=CommandType.SET_SELL_AMOUNT, username=user_id)
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=args.get('tx_num', 99999), command=CommandType.SET_SELL_AMOUNT, errorMessage=response['message'])
        return jsonify(response)

    # Ensure user owns sufficient amount of stock at the current price.
    db = DB()
    user_stocks = db.get_account(user_id)['stocks']
    if stock_symbol not in user_stocks:
        response['status'] = 'failure'
        response['message'] = 'User does not own any {} stock'.format(stock_symbol)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.SET_SELL_AMOUNT, errorMessage=response['message'])
        return jsonify(response)

    if amount > user_stocks[stock_symbol]: # total_share_value
        response['status'] = 'failure'
        #response['message'] = 'Not enough stock owned at current price to sell. Current price: {}, Total share value: {}, Requested amount: {}'.format(price, total_share_value, amount)
        response['message'] = 'Not enough stock owned to set aside'

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.SET_SELL_AMOUNT, errorMessage=response['message'])
        return jsonify(response)

    # Set SELL trigger with no price specified (until SET_SELL_TRIGGER called)
    trigger_matched_count, trigger_modified_count = db.set_trigger('SELL', user_id, stock_symbol, price=None)

    # Add SELL reserve amount
    reserve_matched_count, reserve_modified_count = db.add_sell_reserve_amount(user_id, stock_symbol, amount)

    db.close_connection()

    Logging.log_user_command(transactionNum=tx_num, command=CommandType.SET_SELL_AMOUNT, username=user_id)
    response['status'] = 'success'
    response['message'] = 'Successfully added trigger for user {} for stock {}.'.format(user_id, stock_symbol)
    response['matched_count'] = reserve_matched_count
    response['modified_count'] = reserve_modified_count
    return jsonify(response)

@bp.route('/set_sell_trigger', methods=['GET'])
def set_sell_trigger():
    '''
    Sets the stock price trigger point for executing any SET_SELL triggers associated with the given stock and user

    Pre-conditions:
        The user must have specified a SET_SELL_AMOUNT prior to setting a SET_SELL_TRIGGER
    Post-coniditons:
        (a) a reserve account is created for the specified amount of the given stock
        (b) the user account for the given stock is reduced by the max number of stocks that could be purchased and
        (c) the set of the user's sell triggers is updated to include the specified trigger.
    '''
    args = dict(request.args)
    response = {'status': None}

    try:
        assert 'tx_num' in args, 'tx_num paramter not provided'
        assert 'userid' in args, 'userid parameter not provided'
        assert 'stocksymbol' in args, 'stocksymbol parameter not provided'
        assert 'amount' in args, 'amount parameter not provided'

        tx_num = int(args['tx_num'])
        user_id = args['userid']
        stock_symbol = args['stocksymbol']
        amount = float(args['amount'])

        Logging.log_debug(transactionNum=tx_num, command=CommandType.SET_SELL_TRIGGER, username=user_id)
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=args.get('tx_num', 99999), command=CommandType.SET_SELL_TRIGGER, errorMessage=response['message'])
        return jsonify(response)

    # Ensure SELL trigger for that stock exists.
    db = DB()
    triggers = db.get_account(user_id)['sell_triggers']
    if stock_symbol not in triggers:
        response['status'] = 'failure'
        response['message'] = 'No sell triggers for stock {}'.format(stock_symbol)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.SET_SELL_TRIGGER, errorMessage=response['message'])
        return jsonify(response)

    # Remove stock amount from account
    matched_count, modified_count = db.decrease_stock_portfolio_amount(user_id, stock_symbol, amount)
    assert matched_count == 1
    assert modified_count == 1

    # Set SELL trigger for stock at that price
    trigger_matched_count, trigger_modified_count = db.set_trigger('SELL', user_id, stock_symbol, amount)
    db.close_connection()

    Logging.log_user_command(transactionNum=tx_num, command=CommandType.SET_SELL_TRIGGER, username=user_id)
    response['status'] = 'success'
    response['matched_count'] = trigger_matched_count
    response['modified_count'] = trigger_modified_count
    return jsonify(response)

@bp.route('/cancel_set_sell', methods=['GET'])
def cancel_set_sell():
    '''
	Cancels the SET_SELL associated with the given stock and user

    Pre-conditions:
        The user must have had a previously set SET_SELL for the given stock
    Post-conditions:
        (a) The set of the user's sell triggers is updated to remove the sell trigger associated with the specified stock
        (b) all user account information is reset to the values they would have been if the given SET_SELL command had not been issued
    '''
    args = dict(request.args)
    response = {'status': None}

    try:
        assert 'tx_num' in args, 'tx_num paramter not provided'
        assert 'userid' in args, 'userid parameter not provided'
        assert 'stocksymbol' in args, 'stocksymbol parameter not provided'

        tx_num = int(args['tx_num'])
        user_id = args['userid']
        stock_symbol = args['stocksymbol']

        Logging.log_debug(transactionNum=tx_num, command=CommandType.CANCEL_SET_SELL, username=user_id)
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=args.get('tx_num', 99999), command=CommandType.CANCEL_SET_SELL, errorMessage=response['message'])
        return jsonify(response)

    # Cancel, or return that no reserve sells were found.
    db = DB()
    cancel_matched, cancel_modified = db.unset_sell_reserve_amount(user_id, stock_symbol)
    if cancel_modified == 0:
        response['status'] = 'failure'
        response['message'] = 'No sell reserve accounts for stock {} and user {} found.'.format(stock_symbol, user_id)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.CANCEL_SET_SELL, errorMessage=response['message'])
        return jsonify(response)

    # Remove any sell triggers for that stock
    db.unset_trigger('SELL', user_id, stock_symbol)
    db.close_connection()

    Logging.log_user_command(transactionNum=tx_num, command=CommandType.CANCEL_SET_SELL, username=user_id)
    response['status'] = 'success'
    response['matched_count'] = cancel_matched
    response['modified_count'] = cancel_modified
    return jsonify(response)


@bp.route('/dumplog', methods=['GET'])
def dumplog():
    '''
    2 possible parameter combinations:

    1) (userid, filename): Print out the history of the users transactions to the user specified file
        Pre-conditions:
            none
        Post-conditions:
            The history of the user's transaction are written to the specified file.

    2) (filename): Print out to the specified file the complete set of transactions that have occurred in the system.
        Pre-conditions:
            Can only be executed from the supervisor (root/administrator) account.
        Post-conditions:
            Places a complete log file of all transactions that have occurred in the system into the file specified by filename

    Output is to specified filename appended with date and time it was created, to keep unique logs.
    '''
    args = dict(request.args)
    response = {'status': None}

    try:
        assert 'tx_num' in args, 'tx_num paramter not provided'
        assert 'filename' in args, 'filename parameter not provided'

        Logging.log_debug(transactionNum=int(args['tx_num']), command=CommandType.DUMPLOG)
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=args.get('tx_num', 99999), command=CommandType.DUMPLOG, errorMessage=response['message'])
        return jsonify(response)

    # Query logs
    filename = '{}-{}'.format(args['filename'], time.strftime('%Y%m%d-%H%M%S'))
    db = DB()
    if 'userid' in args:
        logs = db.get_logs(args['userid'])
    else:
        logs = db.get_logs()
    db.close_connection()

    # Convert logs to XML (Assume logs have been validated when entered.)
    logs_xml = Logging.convert_dicts_to_xml(logs)
    logs_xml.write('logs/{}.xml'.format(filename), encoding='utf-8')

    # Log as SystemEventType
    Logging.log_system_event(transactionNum=int(args['tx_num']), command=CommandType.DUMPLOG, filename=filename)
    Logging.log_user_command(transactionNum=int(args['tx_num']), command=CommandType.DUMPLOG)
    response['status'] = 'success'
    response['message'] = 'Wrote logs to {}'.format(filename)
    return jsonify(response)

@bp.route('/display_summary', methods=['GET'])
def display_summary():
    '''
	Provides a summary to the client of the given user's transaction history and the current status of their accounts as well as any set buy or sell triggers and their parameters

    Pre-conditions:
        none
    Post-conditions:
	    A summary of the given user's transaction history and the current status of their accounts as well as any set buy or sell triggers and their parameters is displayed to the user.
    '''
    args = dict(request.args)
    response = {'status': None}

    try:
        assert 'tx_num' in args, 'tx_num paramter not provided'
        assert 'userid' in args, 'userid parameter not provided'

        Logging.log_debug(transactionNum=int(args['tx_num']), command=CommandType.DISPLAY_SUMMARY, username=args['userid'])
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=args.get('tx_num', 99999), command=CommandType.DISPLAY_SUMMARY, errorMessage=response['message'])
        return jsonify(response)

    db = DB()
    account = json.loads(json_util.dumps(db.get_account(args['userid'])))
    transactions = json.loads(json_util.dumps(db.get_user_transactions(args['userid'])))
    db.close_connection()

    Logging.log_system_event(transactionNum=int(args['tx_num']), command=CommandType.DISPLAY_SUMMARY, username=args['userid'])
    Logging.log_user_command(transactionNum=int(args['tx_num']), command=CommandType.DISPLAY_SUMMARY, username=args['userid'])
    response['transactions'] = transactions
    response['account'] = account
    response['status'] = 'success'
    return jsonify(response)
