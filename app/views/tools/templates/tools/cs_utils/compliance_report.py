"""
compliance_report.py - Merge payments made vs payments due.

Copyright (c) 2021 by Thomas J. Daley. All Rights Reserved.
See accopmanying LICENSE file for license information.
"""
from datetime import datetime
from decimal import Decimal
import locale
import operator

DELIMITER = '\t'
INDICTMENT = """
According to the terms of the Child Support Order, Obligor was required to pay {amount} to Obligee on {date} for {description}.
Obligor violated the Child Support Order by failing to pay the full amount of {amount} on or before {date}.
Obligor instead paid a total of {paid}{payment_list}, leaving {remainder} in arrears.
"""


def compliance_report(
    payments_due: list,
    payments_made: list,
) -> list:
    """
    Create a date-sorted list of payments due and payments made

    Creates a list of payments made and due to import into Excel or such
    for a child support compliance report.

    Args:
        payments_due (list[dict]): List of payments that have become due.
        payments_made (list[dict]): List of payments that have been made

    Returns:
        (list[dict]): A list of payments

    Throws:
        None.

    Side Effects:
        None.

    Sample Use:
        Sample code
    """
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    combined_list = payments_due + payments_made
    combined_list.sort(key=operator.itemgetter('date', 'type'))
    report = [DELIMITER.join(["Date", "Description", "Amount Due", "Amount Paid", "Notes"])]
    total_due = Decimal(0.00)
    total_paid = Decimal(0.00)
    for pay_record_item in combined_list:
        if pay_record_item['type'] == 'A':
            print(pay_record_item['amount'], locale.currency(pay_record_item['amount'], grouping=True))
            report_item = [
                pay_record_item['date'].strftime('%m/%d/%Y'),
                pay_record_item['description'],
                locale.currency(pay_record_item['amount'], grouping=True),
                '',
                pay_record_item.get('note', '')
            ]
            total_due += pay_record_item['amount']
        else:
            report_item = [
                pay_record_item['date'].strftime('%m/%d/%Y'),
                pay_record_item['description'],
                '',
                locale.currency(pay_record_item['amount'], grouping=True),
                pay_record_item.get('note', '')
            ]
            total_paid += pay_record_item['amount']
        report.append(DELIMITER.join(report_item))
    report.append(DELIMITER.join(
        [
            '',
            "TOTALS",
            locale.currency(total_due, grouping=True),
            locale.currency(total_paid, grouping=True),
            f"Arrearage: {locale.currency(total_due-total_paid, grouping=True)}"
        ]))
    return report


def enforcement_report(
    payments_due: list,
    payments_made: list,
) -> list:
    """
    Apply payments that were made to payments that were due.

    Creates a list of payments made and due to import into Excel or such
    for a child support compliance report. This report applies payments to
    obligations so that you can see which obligations were eventually
    paid and which were never paid. This is the basis of a contempt
    motion.

    Args:
        payments_due (list[dict]): List of payments that have become due.
        payments_made (list[dict]): List of payments that have been made

    Returns:
        (list[dict]): A list of payments that were due, each having a list
            of payments that were applied.

    Throws:
        None.

    Side Effects:
        None.
    """
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    combined_list = payments_due + payments_made
    combined_list.sort(key=operator.itemgetter('date', 'type'))

    payment_idx = __next_payment_idx(combined_list, 0)

    while payment_idx:
        due_idx = __prev_due_idx(combined_list, payment_idx)
        __apply_payment(payment_idx, due_idx, combined_list)
        payment_idx = __next_payment_idx(combined_list, payment_idx)
    return combined_list


def violations(enforcement_report: list) -> list:
    """
    Create a list violations to include in enforcement pleadings.

    Enforcement pleadings need to contain a mini-indictment for each violation.
    This function generates the text of those mini-indictments based on the
    enforcement report.

    Args:
        enforcement_report (list[dict]): Output from csutils.enforcement_report()

    Returns:
        (list[str]): A list of enforcement pleadings

    Throws:
        None.

    Side Effects:
        None.
    """
    violations = []
    for pay_record in enforcement_report:
        if pay_record['type'] == 'A' and pay_record['remaining_amount'] > 0:
            due_date = datetime.strftime(pay_record['date'], '%B %d, %Y').replace(' 0', ' ')
            indictment = INDICTMENT \
                .replace('{amount}', locale.currency(pay_record['amount'], grouping=True)) \
                .replace('{date}', due_date) \
				.replace('{description}', pay_record['description'].lower()) \
                .replace('{paid}', locale.currency(pay_record['amount'] - pay_record['remaining_amount'], grouping=True)) \
				.replace('{payment_list}', __payment_list(pay_record)) \
                .replace('{remainder}', locale.currency(pay_record['remaining_amount'], grouping=True)) \
                .replace('\n', " ")
            violations.append(indictment)
    return violations


def __payment_list(pay_record: dict) -> str:
    """
    Create a text string listing the payments that were made.
    """
    payment_list = ''
    payments = pay_record.get('payments', [])
    if not payments:
        return payment_list

    for payment in payments:
        payment_amount = locale.currency(payment['amount'], grouping=True)
        payment_date = datetime.strftime(payment['date'], '%B %d, %Y').replace(' 0', ' ')
        if payment_list != '':
            payment_list += "; "
        if pay_record['date'] <= payment['date']:
            payment_list += f"{payment_amount} on {payment_date}"
        else:
            payment_list += f"{payment_amount} carried forward from {payment_date}"

    return f" ({payment_list})"


def __apply_payment(payment_idx: int, due_idx: int, the_list: list):
    payment = the_list[payment_idx]
    due = the_list[due_idx]

    applied_amount = Decimal(min(payment['remaining_amount'], due['remaining_amount']))
    payment['remaining_amount'] -= applied_amount
    due['remaining_amount'] -= applied_amount
    if 'payments' not in due:
        due['payments'] = []
    due['payments'].append({'date': payment['date'], 'amount': applied_amount, 'leaves': due['remaining_amount']})


def __next_payment_idx(the_list: list, start_idx: int = 0) -> int:
    """
    Find first payment record having a *remaining_amount* > 0.
    """
    for idx in range(start_idx, len(the_list)):
        pay_record = the_list[idx]
        if pay_record['type'] == 'Z' and pay_record['remaining_amount'] > 0:
            return idx
    return None


def __prev_due_idx(the_list: list, start_idx: int) -> int:
    """
    Find the first payment due record, going backward from the given index.
    """
    for idx in range(start_idx-1, -1, -1):
        pay_record = the_list[idx]
        # print(f"\t\t << IDX: {idx}  Type: {pay_record['type']}  Bal: {pay_record['remaining_amount']}")
        if pay_record['type'] == 'A' and pay_record['remaining_amount'] > 0:
            return idx
    #
    # Looks like we're all caught up. Look for a future payable to apply the payment
    # to. (TJD 2022-Jan-25)
    #
    for idx in range(start_idx+1, len(the_list)):
        pay_record = the_list[idx]
        # print(f"\t\t >> IDX: {idx}  Type: {pay_record['type']}  Bal: {pay_record['remaining_amount']}")
        if pay_record['type'] == 'A' and pay_record['remaining_amount'] > 0:
            return idx
    return None


def main():
    from combined_payment_schedule import combined_payment_schedule
    from payments_made import payments_made
    children = [
        {
            'name': "Tom",
            'dob': datetime(2000, 1, 29)
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

    start_date = datetime(2020, 3, 1)
    cs_payment = Decimal(387.5)
    health_ins_payment = Decimal(100.00)
    dental_ins_payment = Decimal(0.00)

    payments_due = combined_payment_schedule(
        children=children,
        initial_child_support_payment=cs_payment,
        health_insurance_payment=health_ins_payment,
        dental_insurance_payment=dental_ins_payment,
        confirmed_arrearage=None,
        start_date=start_date,
        num_children_not_before_court=0
    )

    payments = payments_made('', filename='harris_ag_pay_record.txt')

    __test_enforcement_report(payments_due, payments)


def __test_enforcement_report(payments_due, payments):
    report = enforcement_report(payments_due, payments)
    for pay_record_item in report:
        if pay_record_item['type'] == 'Z':
            continue
        print(
            pay_record_item['date'].strftime('%m/%d/%Y'),
            pay_record_item['description'].ljust(20, ' '),
            locale.currency(pay_record_item['amount'], grouping=True).rjust(15, ' '),
            locale.currency(pay_record_item['remaining_amount'], grouping=True).rjust(15, ' '),
        )
        for payment in pay_record_item.get('payments', []):
            print(
                ' '*10,
                payment['date'].strftime('%m/%d/%Y'),
                locale.currency(payment['amount'], grouping=True).rjust(15, ' ')
            )
    indictments = violations(report)
    for violation_number, indictment in enumerate(indictments):
        print(f"VIOLATION {violation_number+1}: {indictment}\n\n")


def __test_compliance_report(payments_due, payments):
    report = compliance_report(payments_due, payments)
    for line in report:
        v = line.split(DELIMITER)
        print(
            str(v[0]).ljust(15, ' '),
            v[1].ljust(25, ' '),
            str(v[2]).rjust(15, ' '),
            str(v[3]).rjust(15, ' '),
            str(v[4])
        )


if __name__ == '__main__':
    main()
