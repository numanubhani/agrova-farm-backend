"""
Deterministic demo data generator — mirrors the original MVP's seed()
function (same linear-congruential RNG) so the demo dataset tells the
same story: a dairy farm with ~6 customers, a month and a half of
delivery + production history, a handful of expenses, and partial
payments leaving some customers with an outstanding balance.
"""
from datetime import date, timedelta

from .models import Customer, Delivery, Expense, Farm, Payment, Production

CUSTOMERS = [
    ('Haji Aslam', '0300-0000001', 220, 4),
    ('Bismillah Sweets', '0300-0000002', 210, 25),
    ('Rizwan Sahab', '0300-0000003', 220, 2),
    ('Al-Madina Hotel', '0300-0000004', 205, 30),
    ('Baji Nasreen', '0300-0000005', 220, 3),
    ('Chaudhry Milk Shop', '0300-0000006', 200, 40),
]

CATS = [
    'Chara (Feed)', 'Wanda / Khal', 'Medicine / Doctor', 'Labour Salary',
    'Bijli', 'Diesel / Transport', 'Maintenance', 'Other',
]

# (day-of-month, category index, amount, note)
EXPENSE_PLAN = [
    (1, 3, 60000, '2 workers'),
    (3, 0, 45000, 'Tuuri + green fodder'),
    (5, 1, 38000, '20 bori'),
    (9, 2, 6200, 'Vaccination'),
    (12, 4, 14500, 'Monthly bill'),
    (15, 5, 9000, 'Delivery bike'),
    (20, 6, 4000, 'Shed repair'),
]


def _add_months(d, months):
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    return date(year, month, 1)


def seed_demo_data(reset=False):
    if reset:
        Delivery.objects.all().delete()
        Production.objects.all().delete()
        Expense.objects.all().delete()
        Payment.objects.all().delete()
        Customer.objects.all().delete()

    farm = Farm.load()
    farm.name = 'Demo Dairy Farm'
    farm.save()

    today = date.today()
    start = _add_months(today, -1)

    customers = [
        Customer.objects.create(name=n, phone=p, rate=r, qty=q, active=True)
        for n, p, r, q in CUSTOMERS
    ]

    state = [7]

    def rnd():
        state[0] = (state[0] * 9301 + 49297) % 233280
        return state[0] / 233280

    delivery_objs = []
    deliveries_by_month = {}
    d = start
    while d <= today:
        for c in customers:
            liters = 0 if rnd() < 0.06 else float(c.qty)
            delivery_objs.append(Delivery(customer=c, date=d, liters=liters))
            deliveries_by_month.setdefault(d.strftime('%Y-%m'), {}).setdefault(c.id, 0)
            deliveries_by_month[d.strftime('%Y-%m')][c.id] += liters
        Production.objects.create(date=d, am=55 + round(rnd() * 8), pm=50 + round(rnd() * 7))
        d += timedelta(days=1)
    Delivery.objects.bulk_create(delivery_objs)

    for off in (0, 1):
        base = _add_months(today, -1 + off)
        for day, cat_idx, amount, note in EXPENSE_PLAN:
            k = date(base.year, base.month, day)
            if k <= today:
                Expense.objects.create(date=k, category=CATS[cat_idx], amount=amount, note=note)

    pay_month = start.strftime('%Y-%m')
    pay_day = date(today.year, today.month, 5)
    if pay_day <= today:
        for i, c in enumerate(customers):
            if i % 3 == 2:
                continue
            liters = deliveries_by_month.get(pay_month, {}).get(c.id, 0)
            factor = 0.8 if i % 2 else 1
            amount = round(liters * float(c.rate) * factor / 100) * 100
            Payment.objects.create(customer=c, date=pay_day, amount=amount, note='Cash')
