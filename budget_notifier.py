from typing import List
import datetime
import math
from plaid import Client as PlaidClient
import boto3


def budget_notifier(event, context):
    def get_creds(session):
        ssm = session.client('ssm')
        client_id = ssm.get_parameter(Name= '/daily_budget_notification/client_id', WithDecryption=True)
        secret_key = ssm.get_parameter(Name= '/daily_budget_notification/secret_key', WithDecryption=True)
        public_key = ssm.get_parameter(Name= '/daily_budget_notification/public_key', WithDecryption=True)
        environment = ssm.get_parameter(Name= '/daily_budget_notification/environment')
        discover_tkn = ssm.get_parameter(Name= '/daily_budget_notification/tokens/discover', WithDecryption=True)
        chase_tkn = ssm.get_parameter(Name= '/daily_budget_notification/tokens/chase', WithDecryption=True)
        amex_tkn = ssm.get_parameter(Name= '/daily_budget_notification/tokens/amex', WithDecryption=True)
        steven_cell = ssm.get_parameter(Name= '/daily_budget_notification/contact/steven_cell', WithDecryption=True)
        michelle_cell = ssm.get_parameter(Name= '/daily_budget_notification/contact/michelle_cell', WithDecryption=True)

        cl_id = client_id['Parameter']['Value']
        s_key = secret_key['Parameter']['Value']
        p_key = public_key['Parameter']['Value']
        envmnt = environment['Parameter']['Value']
        d_tkn = discover_tkn['Parameter']['Value']
        c_tkn = chase_tkn['Parameter']['Value']
        a_tkn = amex_tkn['Parameter']['Value']
        s_cell = steven_cell['Parameter']['Value']
        m_cell = michelle_cell['Parameter']['Value']

        return cl_id, s_key, p_key, envmnt, d_tkn, c_tkn, a_tkn, s_cell, m_cell


    def get_some_transactions(access_token: str, start_date: str, end_date: str) -> List[dict]:
        MAX_TRANSACTIONS_PER_PAGE = 500
        OMIT_CATEGORIES = ["Credit", "Deposit", "Payment"]
        OMIT_ACCOUNT_SUBTYPES = ['cd', 'savings', 'checking']

        account_ids = [account['account_id'] for account in plaid_client.Accounts.get(access_token)['accounts']
            if account['subtype'] not in OMIT_ACCOUNT_SUBTYPES]
        
        num_available_transactions = plaid_client.Transactions.get(access_token, start_date, end_date, account_ids=account_ids)['total_transactions']
        num_pages = math.ceil(num_available_transactions / MAX_TRANSACTIONS_PER_PAGE)
        transactions = []
        
        for page_num in range(num_pages):
            transactions += [transaction for transaction in plaid_client.Transactions.get(access_token, start_date, end_date,
                            account_ids=account_ids,offset=page_num * MAX_TRANSACTIONS_PER_PAGE, count=MAX_TRANSACTIONS_PER_PAGE)['transactions']
                            if transaction['category'] is None
                            or not any(category in OMIT_CATEGORIES
                            for category in transaction['category'])
                            ]
        
        return transactions


    def get_yesterdays_transactions() -> List[dict]:
        today = datetime.date.today()
        idx = (today.weekday() + 3) % 7
        yesterday = (today - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        start = (today - datetime.timedelta(idx)).strftime('%Y-%m-%d')
        


        y_trx = []
        for access_id in [c_tkn, d_tkn, a_tkn]:
            y_trx += get_some_transactions(access_id, yesterday, yesterday)
        
        w_trx = []
        for access_id in [c_tkn, d_tkn, a_tkn]:
            w_trx += get_some_transactions(access_id, start, yesterday)

        return y_trx, w_trx, start, idx


    def sms(session, y_trx, w_trx):
        y_total_spent = round(sum(transaction['amount'] for transaction in y_trx),2)
        w_total_spent = round(sum(transaction['amount'] for transaction in w_trx),2)
        y_body = '${} spent yesterday.'.format(y_total_spent)
        w_body = '${} spent this week.'.format(w_total_spent)
        r_body = '${} available for the next {} days.'.format(round(500-w_total_spent,2), (7-idx)
        sns = session.client('sns')
        contact_list = [s_cell, m_cell]
        for num in contact_list:
            try:
                sns.publish(
                    PhoneNumber = num,
                        Message = (str(y_body) + '\n' + str(w_body)+ '\n' + str(r_body))
                        )
                print('sns number sent to ' + str(num))
            except Exception as e: print(e)

    session = boto3.session.Session()
    cl_id, s_key, p_key, envmnt, d_tkn, c_tkn, a_tkn, s_cell, m_cell = get_creds(session)
    plaid_client = PlaidClient(client_id=cl_id, secret=s_key,public_key=p_key, environment=envmnt)
    y_trx, w_trx, start, idx = get_yesterdays_transactions()
    try:
        sms(session, y_trx,w_trx)
        print('yesterdays value: ' + str(y_trx) + ', week value: ' + str(w_trx))
    except Exception as e: print(e)
