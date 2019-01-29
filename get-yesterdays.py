import datetime
import os
from typing import List

from get_some_transactions import get_some_transactions


def get_yesterdays_transactions() -> List[dict]:
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

    transactions = []

    for access_id in [('CHASE_ACCESS_TOKEN'), ('DISCOVER_ACCESS_TOKEN'), ('AMEX_ACCESS_TOKEN')]:
        transactions += get_some_transactions(access_id, yesterday, yesterday)

    return transactions
