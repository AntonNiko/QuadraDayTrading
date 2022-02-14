#!/usr/bin/env python3
'''
This blueprint provides an API to process all user commands specified in:
https://www.ece.uvic.ca/~seng468/ProjectWebSite/Commands.html 
'''
from flask import Blueprint, jsonify, request
import time
from transaction_server.db import DB
from transaction_server.quoteserver_client import QuoteServerClient

bp = Blueprint('commands', __name__, url_prefix='/commands')

@bp.route('/add', methods=['GET'])
def add():
    '''
	Add the given amount of money to the user's account. GET parameters are:
        userid: Username
        amount: Amount to add to username's account.

    Pre-conditions:
        None
    Post-conditions:
        The user's account is increased by the amount of money specified
    '''
    response = {'status': None}
    args = dict(request.args)

    try:
        assert 'userid' in args, 'userid parameter not provided'
        assert 'amount' in args, 'amount parameter not provided'

        # If account does nto exist, create.
        user_id = args['userid']
        amount = float(args['amount'])
        db = DB()
        if not db.does_account_exist(user_id):
            db.create_account(user_id)

        matched_count, modified_count = db.add_money_to_account(user_id, amount)
        db.close_connection()
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)
        return jsonify(response)

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
    response = {'status': None}
    args = dict(request.args)

    try:
        assert 'userid' in args, 'userid parameter not provided'
        assert 'stocksymbol' in args, 'stocksymbol parameter not provided'
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)
        return jsonify(response)

    price, symbol, username, timestamp, cryptokey = QuoteServerClient.get_quote(args['stocksymbol'], args['userid'])

    response['status'] = 'success'
    response['price'] = price
    response['symbol'] = symbol
    response['username'] = username
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
    response = {'status': None}
    args = dict(request.args)

    try:
        assert 'userid' in args, 'userid parameter not provided'
        assert 'stocksymbol' in args, 'stocksymbol parameter not provided'
        assert 'amount' in args, 'amount parameter not provided'
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)
        return jsonify(response)

    # Ensure account exists and balance is sufficient.
    db = DB()
    userid = args['userid']
    stocksymbol = args['stocksymbol']
    amount = float(args['amount'])

    if not db.does_account_exist(userid):
        response['status'] = 'failure'
        response['message'] = 'Account does not exist.'
        return jsonify(response)

    # Get account balance
    balance = db.get_account_details(userid)['balance']
    if balance < amount:
        response['status'] = 'failure'
        response['message'] = 'Not enough money in account to buy.'
        return jsonify(response)

    # Add transaction as pending confirmation from user.
    # TODO: Replace with Redis?
    # Delete any previous pending transactions
    if db.get_pending_transaction(userid, 'BUY'):
        db.delete_pending_transaction(userid, 'BUY')
    db.add_pending_transaction(userid, 'BUY', stocksymbol, amount, time.time())
    db.close_connection()

    response['status'] = 'success'
    response['message'] = 'Successfully registered pending transaction. Confirm buy within 60 seconds.'
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
    response = {'status': None}
    args = dict(request.args)

    try:
        assert 'userid' in args, 'userid parameter not provided'
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)
        return jsonify(response)

    # Ensure latest buy command exists and is less than 60 seconds old.
    db = DB()
    userid = args['userid']

    pending_transaction = db.get_pending_transaction(userid, 'BUY')
    if not pending_transaction:
        response['status'] = 'failure'
        response['message'] = 'No pending BUY transaction found.'
        return jsonify(response)

    original_timestamp = pending_transaction['timestamp']
    stock_symbol = pending_transaction['stock_symbol']
    amount = pending_transaction['amount']

    current_timestamp = time.time()
    if (current_timestamp - original_timestamp) > 60:
        response['status'] = 'failure'
        response['message'] = 'Most recent BUY command is more than 60 seconds old.'
        return jsonify(response)

    # Delete pending transaction
    deleted_count = db.delete_pending_transaction(userid, 'BUY')
    assert deleted_count == 1

    # Reduce account balance by specified amount
    matched_count, modified_count = db.remove_money_from_account(userid, amount)
    assert matched_count == 1
    assert modified_count == 1

    # Increase account amount of stock owned
    portfolio_matched_count, portfolio_modified_count = db.increase_stock_portfolio_amount(userid, stock_symbol, amount)
    db.close_connection()

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
    response = {'status': None}
    args = dict(request.args)

    try:
        assert 'userid' in args, 'userid parameter not provided'
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)
        return jsonify(response)

    # Ensure latest buy command exists and is less than 60 seconds old.
    db = DB()
    userid = args['userid']

    pending_transaction = db.get_pending_transaction(userid, 'BUY')
    if not pending_transaction:
        response['status'] = 'failure'
        response['message'] = 'No pending BUY transaction found.'
        return jsonify(response)

    original_timestamp = pending_transaction['timestamp']

    current_timestamp = time.time()
    if (current_timestamp - original_timestamp) > 60:
        response['status'] = 'failure'
        response['message'] = 'Most recent BUY command is more than 60 seconds old.'
        return jsonify(response)

    # Delete pending BUY transaction such that COMMIT_BUY will not find any pending transactions.
    deleted_count = db.delete_pending_transaction(userid, 'BUY')
    response['status'] = 'success'
    response['message'] = 'Successfully cancelled {} BUY transactions'.format(deleted_count)
    return jsonify(response)


@bp.route('/sell', methods=['GET'])
def sell():
    # TODO for 1 user workload
    pass

@bp.route('/commit_sell', methods=['GET'])
def commit_sell():
    # TODO for 1 user workload
    pass

@bp.route('/cancel_sell', methods=['GET'])
def cancel_sell():
    # TODO for 1 user workload
    pass

@bp.route('/set_buy_amount', methods=['GET'])
def set_buy_amount():
    # TODO for 1 user workload
    pass

@bp.route('/cancel_set_buy', methods=['GET'])
def cancel_set_buy():
    # TODO for 1 user workload
    pass

@bp.route('/set_buy_trigger', methods=['GET'])
def set_buy_trigger():
    pass

@bp.route('/set_sell_amount', methods=['GET'])
def set_sell_amount():
    # TODO for 1 user workload
    pass

@bp.route('/set_sell_trigger', methods=['GET'])
def set_sell_trigger():
    # TODO for 1 user workload
    pass

@bp.route('/cancel_set_sell', methods=['GET'])
def cancel_set_sell():
    # TODO for 1 user workload
    pass

@bp.route('/dumplog', methods=['GET'])
def dumplog():
    # TODO for 1 user workload
    pass

@bp.route('/display_summary', methods=['GET'])
def display_summary():
    # TODO for 1 user workload
    pass