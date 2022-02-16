#!/usr/bin/env python3
'''
This blueprint provides an API to process all user commands specified in:
https://www.ece.uvic.ca/~seng468/ProjectWebSite/Commands.html 
'''
from flask import Blueprint, jsonify, request
import time
from transaction_server.db import DB
from transaction_server.logging import Logging, CommandType
from transaction_server.quoteserver_client import QuoteServerClient

# Keep track of transactions for logging purposes.
# TODO: Ensure it is thread-safe.
current_tx_num = 1

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
    tx_num = current_tx_num
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

        # Log as AccountTransactionType with updated balance
        Logging.log_account_transaction(transactionNum=tx_num, action='add', username=user_id, funds=float(db.get_account(user_id)['balance']))

        db.close_connection()
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.ADD, errorMessage=str(err))
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
    tx_num = current_tx_num
    response = {'status': None}
    args = dict(request.args)

    try:
        assert 'userid' in args, 'userid parameter not provided'
        assert 'stocksymbol' in args, 'stocksymbol parameter not provided'
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.QUOTE, errorMessage=str(err))
        return jsonify(response)

    price, symbol, username, timestamp, cryptokey = QuoteServerClient.get_quote(args['stocksymbol'], args['userid'])

    # Log as QuoteServerType
    Logging.log_quote_server_hit(transactionNum=tx_num, price=price, stockSymbol=symbol, username=username, quoteServerTime=timestamp, cryptokey=cryptokey)

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
    tx_num = current_tx_num
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
    tx_num = current_tx_num
    response = {'status': None}
    args = dict(request.args)

    try:
        assert 'userid' in args, 'userid parameter not provided'
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.COMMIT_BUY, errorMessage=response['message'])      
        return jsonify(response)

    # Ensure latest buy command exists and is less than 60 seconds old.
    db = DB()
    user_id = args['userid']

    pending_transaction = db.get_pending_transaction(user_id, 'BUY')
    if not pending_transaction:
        response['status'] = 'failure'
        response['message'] = 'No pending BUY transaction found.'

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.COMMIT_BUY, errorMessage=response['message'])      
        return jsonify(response)

    original_timestamp = pending_transaction['timestamp']
    stock_symbol = pending_transaction['stock_symbol']
    amount = pending_transaction['amount']

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
    tx_num = current_tx_num
    response = {'status': None}
    args = dict(request.args)

    try:
        assert 'userid' in args, 'userid parameter not provided'
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.CANCEL_BUY, errorMessage=response['message'])      
        return jsonify(response)

    # Ensure latest buy command exists and is less than 60 seconds old.
    db = DB()
    userid = args['userid']

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
    tx_num = current_tx_num
    response = {'status': None}
    args = dict(request.args)

    try:
        assert 'userid' in args, 'userid parameter not provided'
        assert 'stocksymbol' in args, 'stocksymbol parameter not provided'
        assert 'amount' in args, 'amount parameter not provided'
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.SELL, errorMessage=response['message'])    
        return jsonify(response)

    # Ensure account exists and user owns enough stock to sell.
    db = DB()
    userid = args['userid']
    stocksymbol = args['stocksymbol']
    amount = float(args['amount'])

    if not db.does_account_exist(userid):
        response['status'] = 'failure'
        response['message'] = 'Account does not exist.'

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.SELL, errorMessage=response['message']) 
        return jsonify(response)

    # Ensure user owns sufficient amount of stock
    user_stocks = db.get_account(userid)['stocks']
    if stocksymbol not in user_stocks:
        response['status'] = 'failure'
        response['message'] = 'User does not own any {} stock'.format(stocksymbol)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.SELL, errorMessage=response['message']) 
        return jsonify(response)

    if amount > user_stocks[stocksymbol]:
        response['status'] = 'failure'
        response['message'] = 'Not enough stock owned to sell.'

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

    response['status'] = 'success'
    response['message'] = 'Successfully registered pending transaction. Confirm sell within 60 seconds.'
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
    tx_num = current_tx_num
    response = {'status': None}
    args = dict(request.args)

    try:
        assert 'userid' in args, 'userid parameter not provided'
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.COMMIT_SELL, errorMessage=response['message']) 
        return jsonify(response)

    # Ensure latest sell command exists and is less than 60 seconds old.
    db = DB()
    user_id = args['userid']

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
    tx_num = current_tx_num
    response = {'status': None}
    args = dict(request.args)

    try:
        assert 'userid' in args, 'userid parameter not provided'
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.CANCEL_SELL, errorMessage=response['message']) 
        return jsonify(response)

    # Ensure latest sell command exists and is less than 60 seconds old.
    db = DB()
    userid = args['userid']

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

    # Delete pending SELL transaction such that COMMIT_SELL will not find any pending transactions.
    deleted_count = db.delete_pending_transaction(userid, 'SELL')
    response['status'] = 'success'
    response['message'] = 'Successfully cancelled {} SELL transactions'.format(deleted_count)
    return jsonify(response)

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
    '''
    tx_num = current_tx_num
    response = {'status': None}
    args = dict(request.args)

    try:
        assert 'filename' in args, 'filename parameter not provided'
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)

        # Log as ErrorEventType
        Logging.log_error_event(transactionNum=tx_num, command=CommandType.DUMPLOG, errorMessage=response['message']) 
        return jsonify(response)

    # Query logs
    db = DB()
    if 'userid' in args:
        logs = db.get_logs(args['userid'])
    else:
        logs = db.get_logs()
    db.close_connection()

    # Convert logs to XML (Assume logs have been validated when entered.)
    logs_xml = Logging.convert_dicts_to_xml(logs)
    logs_xml.write('logs/{}'.format(args['filename']), encoding='utf-8')

    response['status'] = 'success'
    response['message'] = 'Wrote logs to {}'.format(args['filename'])
    return jsonify(response) 

@bp.route('/display_summary', methods=['GET'])
def display_summary():
    # TODO for 1 user workload
    pass