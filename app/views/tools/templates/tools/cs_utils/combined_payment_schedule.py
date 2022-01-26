"""
combined_payment_schedule.py - Create a child support arrearage report.

Copyright (c) 2021 by Thomas J. Daley, J.D.
"""
from datetime import datetime
from decimal import Decimal
import operator
from views.tools.templates.tools.cs_utils.payment_schedule import payment_schedule
from views.tools.templates.tools.cs_utils.stepdown import stepdown


def combined_payment_schedule(
    children: list,
    initial_child_support_payment: Decimal,
    health_insurance_payment: Decimal,
    dental_insurance_payment: Decimal,
    confirmed_arrearage: Decimal,
    start_date: datetime,
    num_children_not_before_court: int = 0
) -> list:
    """
    Create a combined payment schedule for regular child support, health insurance, and
    dental insurance.

    Each child in the children list must contain the following keys:
        * name (str) - The child's name
        * dob (datetime) - The child's date of birth
    The child can have other keys and they'll be returned to the caller.

    Args:
        children (list): List of dicts where each item is a child.
        initial_child_support_payment (Decimal): Amount of regular child support, not including arrearage payoff
        health_insurance_payment (Decimal): Amount of health insurance reimbursement or None
        dental_insurance_payment (Decimal): Amount of dental insurance reimbrusement or None
        confirmed_arrearage (Decimal): Total arrearage judgment that was previously confirmed.
        start_date (datetime): Start date for schedule. If *confirmed_arrearage* is provided, then this should be
                               the date after the first payment was due following the date on which the
                               arrearage was confirmed.
        num_children_not_before_court (int): Number of children obligor must support who are not part of this action.

    Returns:
        (list): List of payments due where each payment is dict with at least these keys:
                'due_date' (datetime): Date payment is due
                'description' (str): From *description* argument
                'amount_due' (Decimal): Amount due for that payment
                'note' (str): Any explanation for why the payment amount changed.

    """
    stepdown_schedule = stepdown(children, initial_child_support_payment, num_children_not_before_court)
    regular_schedule = payment_schedule(
        initial_amount=initial_child_support_payment,
        n_per_year=12,
        start_date=start_date,
        step_down_schedule=stepdown_schedule,
        description='Child support due'
    )

    if health_insurance_payment:
        stepdown_schedule = stepdown(children, initial_child_support_payment, num_children_not_before_court)
        health_insurance_schedule = payment_schedule(
            initial_amount=health_insurance_payment,
            n_per_year=12,
            start_date=start_date,
            step_down_schedule=stepdown_schedule,
            description='Medical support due',
            fixed_payment=True
        )
    else:
        health_insurance_schedule = []
    
    if dental_insurance_payment:
        stepdown_schedule = stepdown(children, initial_child_support_payment, num_children_not_before_court)
        dental_insurance_schedule = payment_schedule(
            initial_amount=dental_insurance_payment,
            n_per_year=12,
            start_date=start_date,
            step_down_schedule=stepdown_schedule,
            description='Dental support due',
            fixed_payment=True
        )
    else:
        dental_insurance_schedule = []

    combined_schedule = regular_schedule + health_insurance_schedule + dental_insurance_schedule
    combined_schedule.sort(key = operator.itemgetter('date', 'description'))
    return combined_schedule


"""
For Testing.
"""
def main():
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

    start_date = datetime(2019, 5, 1)
    cs_payment = Decimal(1000.00)
    health_ins_payment = Decimal(350.00)
    dental_ins_payment = Decimal(50.00)

    payments_due = combined_payment_schedule(
        children=children,
        initial_child_support_payment=cs_payment,
        health_insurance_payment=health_ins_payment,
        dental_insurance_payment=dental_ins_payment,
        confirmed_arrearage=None,
        start_date=start_date,
        num_children_not_before_court=0
    )

    for payment_due in payments_due:
        print(payment_due)


if __name__ == '__main__':
    main()
