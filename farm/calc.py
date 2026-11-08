"""
Core business calculations shared by the dashboard, bills and reports
endpoints. Mirrors the logic of the original single-file MVP 1:1 so
numbers never drift between the two: liters -> bill amount -> balance
carried forward month to month.
"""
from datetime import date
from decimal import Decimal

from django.db.models import Sum

from .models import Customer, Delivery, Expense, Payment, Production

ZERO = Decimal('0')


def month_bounds(month_str):
    """'YYYY-MM' -> (first_day, first_day_of_next_month)."""
    year, month = (int(p) for p in month_str.split('-'))
    first = date(year, month, 1)
    next_first = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return first, next_first


def liters_total(customer_id, start=None, end=None):
    qs = Delivery.objects.filter(customer_id=customer_id)
    if start is not None:
        qs = qs.filter(date__gte=start)
    if end is not None:
        qs = qs.filter(date__lt=end)
    return qs.aggregate(total=Sum('liters'))['total'] or ZERO


def payments_total(customer_id, start=None, end=None):
    qs = Payment.objects.filter(customer_id=customer_id)
    if start is not None:
        qs = qs.filter(date__gte=start)
    if end is not None:
        qs = qs.filter(date__lt=end)
    return qs.aggregate(total=Sum('amount'))['total'] or ZERO


def bill(customer, month_str):
    """Per-customer bill for one month, carrying forward any prior balance."""
    first, next_first = month_bounds(month_str)
    rate = customer.rate

    liters = liters_total(customer.id, start=first, end=next_first)
    amount = liters * rate

    liters_before = liters_total(customer.id, end=first)
    payments_before = payments_total(customer.id, end=first)
    prev = liters_before * rate - payments_before

    paid = payments_total(customer.id, start=first, end=next_first)
    balance = prev + amount - paid

    return {
        'customer_id': customer.id,
        'liters': liters,
        'amount': amount,
        'prev': prev,
        'paid': paid,
        'balance': balance,
    }


def month_stats(month_str):
    first, next_first = month_bounds(month_str)
    customers = list(Customer.objects.all())
    bills = [bill(c, month_str) for c in customers]

    exp = Expense.objects.filter(date__gte=first, date__lt=next_first).aggregate(
        total=Sum('amount'))['total'] or ZERO
    prod_agg = Production.objects.filter(date__gte=first, date__lt=next_first).aggregate(
        am=Sum('am'), pm=Sum('pm'))
    prod = (prod_agg['am'] or ZERO) + (prod_agg['pm'] or ZERO)

    sale = sum((b['amount'] for b in bills), ZERO)
    delivered = sum((b['liters'] for b in bills), ZERO)
    received = sum((b['paid'] for b in bills), ZERO)
    pending = sum((b['balance'] for b in bills), ZERO)
    profit = sale - exp
    cpl = (exp / prod) if prod else ZERO

    return {
        'sale': sale,
        'delivered': delivered,
        'exp': exp,
        'prod': prod,
        'received': received,
        'pending': pending,
        'profit': profit,
        'cpl': cpl,
    }


def category_totals(month_str):
    first, next_first = month_bounds(month_str)
    rows = (
        Expense.objects.filter(date__gte=first, date__lt=next_first)
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    return [{'category': r['category'], 'total': r['total']} for r in rows]


def day_total(d):
    return Delivery.objects.filter(date=d).aggregate(total=Sum('liters'))['total'] or ZERO
