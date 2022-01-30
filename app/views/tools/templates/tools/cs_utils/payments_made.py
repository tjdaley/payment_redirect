"""
payments_made.py - Converts text to list of dicts of payments made.

Copyright (c) 2021 by Thomas J. Daley. All Rights Reserved.
See accopmanying LICENSE file for license information.
"""
import datetime
from decimal import Decimal
import re

AG_DATE_FORMAT = '%m/%d/%Y'
TSV_DATE_COL = 0
TSV_AMOUNT_COL = 1


def payments_made(tsv: str, filename: str = None) -> list:
    """
    Takes tab-separated values from the OAG web site and converts to a list of dicts.
    
    The AG web site provides payment information in an HTML table. When that is swiped
    by the user and pasted into a text box, it appears as tab-separated values. This
    function converts the TSVs into a list of dicts where there is one list entry per
    payment made and each *payment* dict has at least the following keys:
        'type' (str): 'Z' to indicate a payment made
        'date' (datetime): Date payment was made.
        'description' (str): "Payment made"
        'amount' (Decimal): Amount of payment.
        'remaining_amount' (Decimal): Amount of payment that has not been applied to
            a payment that is due. This starts as the same value as *payment_amount*
            and then the consuming application decrements this to zero as the payment
            is applied to outstanding balances.
    
    Args:
        tsv (str): Tab-separated values from AG web site
        filename (str): Filename to use instead of *tsv*, for testing.
    
    Returns:
        (list[dict]): List of payment dicts, described above
    
    Throws:
        AttributeError - If *tsv* is not of type *str*.
        IndexError - If the *tsv* data contains a row without enough values, i.e. is missing a column
        ValueError - If the payment amount or date are not parseable.
    
    Side Effects:
        None.
    
    Sample Use:
        from csutils import payments_made
        tsv = '01/01/2021\t387.50\txxxxxxx\n02/01/2020\t387.50\txxxxxxx'
        payments = payments_made(tsv)
        print(payments)
        >>>
        [
            {type: 'Z', date: datetime(2021,1,1,0,0), amount: 387.50, remaining_amount: 387.50, description='Payment made'},
            {type: 'Z', date: datetime(2021,2,1,0,0), amount: 387.50, remaining_amount: 387.50, description='Payment made'},
        ]
    """
    payments = []

    if filename:
        payment_rows = __load_file(filename).split('\n')
    else:
        payment_rows = tsv.split('\n')

    row_number = 0
    for payment_row in payment_rows:
        row_number += 1
        fields = payment_row.split('\t')
        try:
            payment_date = datetime.datetime.strptime(fields[TSV_DATE_COL], AG_DATE_FORMAT)
        except Exception:
            raise ValueError(f"Invalid date value of '{fields[TSV_DATE_COL]}' in row # {row_number}")

        try:
            c_value = re.sub('[^0-9\.]', '', fields[TSV_AMOUNT_COL])  # strip whitespace and leading dollar sign
            payment_amount = Decimal(c_value)  
        except Exception:
            raise ValueError(f"Invalid payment amount of '{fields[TSV_AMOUNT_COL]}' in row # {row_number}")

        payment = {
            'type': 'Z',
            'date': payment_date,
            'description': "Payment made",
            'amount': payment_amount,
            'remaining_amount': payment_amount
        }
        payments.append(payment)

    return sorted(payments, key=lambda k: k['date'])


def __load_file(filename: str) -> str:
    with open(filename, 'r') as pay_record:
        tsv = pay_record.read()
    return tsv

def main():
    print(payments_made('', filename='../data/ag_pay_record.txt'))


if __name__ == '__main__':
    main()
