'''
This blueprint provides an API to process all user commands specified in:
https://www.ece.uvic.ca/~seng468/ProjectWebSite/Commands.html 
'''
from flask import Blueprint, request

bp = Blueprint('commands', __name__, url_prefix='/commands')

RESPONSE_TEMPLATE = {'status': None}

@bp.route('/add', methods=['GET'])
def add():
    # TODO for 1 user workload
    '''
	Add the given amount of money to the user's account. GET parameters are:
        userid: Username
        amount: Amount to add to username's account.

    Pre-conditions:
        None
    Post-conditions:
        The user's account is increased by the amount of money specified
    '''
    response = RESPONSE_TEMPLATE.copy()
    args = dict(request.args)
    
    try:
        assert 'userid' in args, 'userid parameter not provided'
        assert 'amount' in args, 'amount parameter not provided'
    except AssertionError as err:
        response['status'] = 'failure'
        response['message'] = str(err)
        return response

    user_id = args['userid']
    amount = float(args['amount'])


@bp.route('/quote', methods=['GET'])
def quote():
    # TODO for 1 user workload
    pass

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