"""
payment_schedule.py - Create a payment schedule based on a payment schedule.

Copyright (c) 2021 by Thomas J. Daley, J.D.
"""
from datetime import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta


def payment_schedule(
    initial_amount: Decimal,
    n_per_year: int,
    start_date: datetime,
    step_down_schedule: list,
    month_days: list = None,
    description: str = 'Child support payment due',
    fixed_payment: bool = False
) -> list:
    """
    Create a payment schedule with one entry for every payment that is due.

    Args:
        initial_amount (Decimal): Initial payment amount. If payable one time per month, then this is
                                full monthly amount. If payable twice per month, then this is
                                half of the full monthly amount. If weekly, then this is the weekly
                                amount.
        n_per_year (int): Number of such payments due per year.
                            12 = Monthly
                            24 = Twice per month (semi-monthly)
                            52 = Weekly
        start_date (datetime): Date on which first payment was due
        step_down_schedule (list): List of step-down dates
        month_days (list[int]): Days of the month child support is payable. If omitted, the following
                                 is used:
                                    n_per_year = 12 . . . . . [1]
                                    n_per_year = 24 . . . . . [1, 15]
                                    n_per_year = else . . . . not used
        description (str): A descriptive string returned in payment list.
        fixed_payment (bool): If True, every payment on the list will be equal to *initial_amount*. This
                              is used for insurance reimbursement schedules where the amount reimbursed
                              does not change based on the number of children. Default = False
    
    Returns:
        (list): List of payments, each being a dict with these keys:
                'type' (str): 'A' to indicate a payment
                'date' (datetime): Date payment is due
                'description' (str): From *description* argument
                'amount' (Decimal): Amount due for that payment
                'note' (str): Any explanation for why the payment amount changed
                'remaining_amount' (Decimal): Amount that has not been paid
    """
    schedule = []

    # Convert start_date from date to datetime
    next_due_date = datetime.combine(start_date, datetime.min.time())
    note = ''
    today = datetime.now()
    should_continue = True  # Set to False when the payment schedule goes past today.

    while step_down_schedule and should_continue:
        next_stepdown = step_down_schedule.pop(0)
        oldest_remaining_child_name = next_stepdown['child']['name']
        if fixed_payment:
            payment_amount = initial_amount
        else:
            payment_amount = next_stepdown['payment_amount']

        while next_due_date <= next_stepdown['last_payment_date']:
            payment = {
                'type': 'A',
                'date': next_due_date,
                'description': description,
                'amount': payment_amount,
                'note': note,
                'remaining_amount': payment_amount
            }
            schedule.append(payment)
            note = ''
            next_due_date = next_due_date + relativedelta(months=+1)
            if next_due_date > today:
                should_continue = False
                break
        note = f"{oldest_remaining_child_name} aged out."
    return schedule


"""
For Testing
"""
def main():
    from stepdown import stepdown

    children = [
        {
            'name': "Tom",
            'dob': datetime(2005, 1, 29)
        },
        {
            'name': "Cindy",
            'dob': datetime(2008, 5, 29)
        },
        {
            'name': "Ava",
            'dob': datetime(2003, 9, 4)
        }
    ]

    initial_cs_payment_due = Decimal(1000.00)

    step_down_schedule = stepdown(
        children=children,
        initial_payment_amount=initial_cs_payment_due,
        num_children_not_before_court=0
    )

    schedule = payment_schedule(
        initial_amount=initial_cs_payment_due,
        n_per_year=12,
        start_date=datetime(2019, 1, 1),
        step_down_schedule=step_down_schedule,
        description="Child support payment due"
    )

    for payment in schedule:
        print(payment['date'], ',', payment['description'], ',', payment['amount'], ',', payment['note'])


if __name__ == '__main__':
    main()
