#!/usr/bin/env python3
'''
This blueprint provides an API to process all user commands specified in:
https://www.ece.uvic.ca/~seng468/ProjectWebSite/Commands.html 
'''
from flask import Blueprint, jsonify, request
from pymongo.errors import ServerSelectionTimeoutError
from transaction_server.db import DB

bp = Blueprint('commands', __name__, url_prefix='/commands')
RESPONSE_TEMPLATE = {'status': None}

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
    # TODO for 1 user workload
    db = DB()
    # print('Result: {}'.format(db.does_account_exist('user1')))

    return jsonify({'status': 'success', 'message': str(db.does_account_exist('user1'))})

@bp.route('/buy', methods=['GET'])
def buy():
    # TODO for 1 user workload
    pass

@bp.route('/commit_buy', methods=['GET'])
def commit_buy():
    # TODO for 1 user workload
    pass

@bp.route('/cancel_buy', methods=['GET'])
def cancel_buy():
    # TODO for 1 user workload
    pass

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