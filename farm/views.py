from datetime import date as date_cls
from decimal import Decimal, InvalidOperation

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import calc
from .models import Customer, Delivery, Expense, Farm, Payment, Production
from .serializers import (
    CustomerSerializer, DeliverySerializer, ExpenseSerializer,
    FarmSerializer, PaymentSerializer, ProductionSerializer,
)


def _parse_month(request, default=None):
    m = request.query_params.get('month') if hasattr(request, 'query_params') else request.GET.get('month')
    return m or default or date_cls.today().strftime('%Y-%m')


def _dec(value, default='0'):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return Decimal(default)


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        qs = Expense.objects.all()
        month = self.request.query_params.get('month')
        if month:
            first, next_first = calc.month_bounds(month)
            qs = qs.filter(date__gte=first, date__lt=next_first)
        return qs


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        qs = Payment.objects.all()
        customer_id = self.request.query_params.get('customer')
        month = self.request.query_params.get('month')
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if month:
            first, next_first = calc.month_bounds(month)
            qs = qs.filter(date__gte=first, date__lt=next_first)
        return qs


@api_view(['GET', 'PUT'])
def farm_settings(request):
    farm = Farm.load()
    if request.method == 'PUT':
        serializer = FarmSerializer(farm, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    return Response(FarmSerializer(farm).data)


@api_view(['GET', 'POST'])
def deliveries_for_date(request):
    """GET ?date= -> {customer_id: liters}. POST {date, entries:{customer_id: liters}} upserts."""
    if request.method == 'GET':
        d = request.query_params.get('date') or date_cls.today().isoformat()
        rows = Delivery.objects.filter(date=d)
        return Response({str(r.customer_id): r.liters for r in rows})

    d = request.data.get('date')
    entries = request.data.get('entries') or {}
    if not d:
        return Response({'detail': 'date is required'}, status=status.HTTP_400_BAD_REQUEST)
    for customer_id, liters in entries.items():
        liters_dec = _dec(liters)
        Delivery.objects.update_or_create(
            customer_id=customer_id, date=d,
            defaults={'liters': liters_dec},
        )
    rows = Delivery.objects.filter(date=d)
    return Response({str(r.customer_id): r.liters for r in rows})


@api_view(['GET', 'POST'])
def production_for_date(request):
    """GET ?date= -> {am, pm, total}. POST {date, am, pm} upserts."""
    if request.method == 'GET':
        d = request.query_params.get('date') or date_cls.today().isoformat()
        prod = Production.objects.filter(date=d).first()
        if not prod:
            return Response({'date': d, 'am': 0, 'pm': 0, 'total': 0})
        return Response(ProductionSerializer(prod).data)

    d = request.data.get('date')
    if not d:
        return Response({'detail': 'date is required'}, status=status.HTTP_400_BAD_REQUEST)
    am = _dec(request.data.get('am'))
    pm = _dec(request.data.get('pm'))
    prod, _ = Production.objects.update_or_create(date=d, defaults={'am': am, 'pm': pm})
    return Response(ProductionSerializer(prod).data)


@api_view(['GET'])
def production_recent(request):
    limit = int(request.query_params.get('limit', 10))
    rows = Production.objects.order_by('-date')[:limit]
    out = []
    for p in rows:
        out.append({
            'date': p.date.isoformat(),
            'am': p.am,
            'pm': p.pm,
            'total': p.am + p.pm,
            'delivered': calc.day_total(p.date),
        })
    return Response(out)


@api_view(['GET'])
def dashboard(request):
    month = _parse_month(request)
    today = date_cls.today().isoformat()
    stats = calc.month_stats(month)
    cats = calc.category_totals(month)
    prod_today = Production.objects.filter(date=today).first()
    delivery_today_entered = Delivery.objects.filter(date=today).exists()
    return Response({
        'month': month,
        'stats': stats,
        'categories': cats,
        'today': {
            'date': today,
            'production': {
                'am': prod_today.am if prod_today else 0,
                'pm': prod_today.pm if prod_today else 0,
                'total': (prod_today.am + prod_today.pm) if prod_today else 0,
            } if prod_today else None,
            'delivered': calc.day_total(today),
            'delivery_entered': delivery_today_entered,
        },
    })


@api_view(['GET'])
def bills(request):
    month = _parse_month(request)
    out = []
    for c in Customer.objects.all():
        b = calc.bill(c, month)
        if not c.active and b['liters'] == 0 and abs(b['balance']) < 1:
            continue
        out.append({
            'customer': CustomerSerializer(c).data,
            **{k: v for k, v in b.items() if k != 'customer_id'},
        })
    return Response({'month': month, 'bills': out})


@api_view(['GET'])
def receipt(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)
    month = _parse_month(request)
    b = calc.bill(customer, month)
    first, next_first = calc.month_bounds(month)
    days = (
        Delivery.objects.filter(customer=customer, date__gte=first, date__lt=next_first)
        .order_by('date')
        .values('date', 'liters')
    )
    return Response({
        'customer': CustomerSerializer(customer).data,
        'month': month,
        'bill': {k: v for k, v in b.items() if k != 'customer_id'},
        'days': [{'date': d['date'].isoformat(), 'liters': d['liters']} for d in days],
    })


def _build_report_data(month):
    stats = calc.month_stats(month)
    cats = calc.category_totals(month)
    first, next_first = calc.month_bounds(month)

    bills_data = []
    for c in Customer.objects.all():
        b = calc.bill(c, month)
        bills_data.append({'customer': c.name, 'phone': c.phone, **{k: v for k, v in b.items() if k != 'customer_id'}})

    days = sorted({
        d.isoformat() for d in
        Delivery.objects.filter(date__gte=first, date__lt=next_first).values_list('date', flat=True)
    })
    customers = list(Customer.objects.all())
    daily_delivery = []
    for d in days:
        row = {'date': d}
        rows = {str(r['customer_id']): r['liters'] for r in Delivery.objects.filter(date=d).values('customer_id', 'liters')}
        total = Decimal('0')
        for c in customers:
            v = rows.get(str(c.id), Decimal('0'))
            row[c.name] = v
            total += v
        row['total'] = total
        daily_delivery.append(row)

    production = list(
        Production.objects.filter(date__gte=first, date__lt=next_first).order_by('date').values('date', 'am', 'pm')
    )
    for p in production:
        p['date'] = p['date'].isoformat()
        p['total'] = p['am'] + p['pm']

    expenses = list(
        Expense.objects.filter(date__gte=first, date__lt=next_first).order_by('date').values('date', 'category', 'amount', 'note')
    )
    for e in expenses:
        e['date'] = e['date'].isoformat()

    payments = list(
        Payment.objects.filter(date__gte=first, date__lt=next_first).order_by('date').values('date', 'customer__name', 'amount', 'note')
    )
    for p in payments:
        p['date'] = p['date'].isoformat()
        p['customer'] = p.pop('customer__name')

    farm = Farm.load()
    return {
        'farm': farm.name,
        'month': month,
        'stats': stats,
        'categories': cats,
        'bills': bills_data,
        'daily_delivery': daily_delivery,
        'production': production,
        'expenses': expenses,
        'payments': payments,
    }


@api_view(['GET'])
def reports(request):
    month = _parse_month(request)
    return Response(_build_report_data(month))


@api_view(['GET'])
def reports_export(request):
    """Build the same 6-sheet workbook as the original MVP, server side."""
    import openpyxl
    from openpyxl.styles import Font

    month = _parse_month(request)
    data = _build_report_data(month)
    stats = data['stats']

    wb = openpyxl.Workbook()

    ws = wb.active
    ws.title = 'Summary'
    ws.append([data['farm']])
    ws.append(['Month', month])
    ws.append([])
    ws.append(['Milk produced (L)', float(stats['prod'])])
    ws.append(['Milk sold (L)', float(stats['delivered'])])
    ws.append(['Difference (L)', float(stats['prod'] - stats['delivered'])])
    ws.append(['Milk sale (Rs)', float(stats['sale'])])
    ws.append(['Total expense (Rs)', float(stats['exp'])])
    ws.append(['Profit / Loss (Rs)', float(stats['profit'])])
    ws.append(['Payment received (Rs)', float(stats['received'])])
    ws.append(['Pending balance (Rs)', float(stats['pending'])])
    ws.append(['Expense per liter (Rs)', round(float(stats['cpl']), 2)])
    ws.append([])
    ws.append(['Expense category', 'Amount (Rs)'])
    for c in data['categories']:
        ws.append([c['category'], float(c['total'])])
    ws['A1'].font = Font(bold=True, size=13)

    ws = wb.create_sheet('Bills')
    ws.append(['Customer', 'Phone', 'Liters', 'Rate', 'Bill', 'Previous balance', 'Paid', 'Balance'])
    for b in data['bills']:
        ws.append([b['customer'], b['phone'], float(b['liters']), None, float(b['amount']), float(b['prev']), float(b['paid']), float(b['balance'])])

    ws = wb.create_sheet('Daily Delivery')
    customer_names = [c.name for c in Customer.objects.all()]
    ws.append(['Date', *customer_names, 'Total'])
    for row in data['daily_delivery']:
        ws.append([row['date'], *[float(row.get(n, 0)) for n in customer_names], float(row['total'])])

    ws = wb.create_sheet('Production')
    ws.append(['Date', 'Morning (L)', 'Evening (L)', 'Total (L)'])
    for p in data['production']:
        ws.append([p['date'], float(p['am']), float(p['pm']), float(p['total'])])

    ws = wb.create_sheet('Expenses')
    ws.append(['Date', 'Category', 'Amount (Rs)', 'Note'])
    for e in data['expenses']:
        ws.append([e['date'], e['category'], float(e['amount']), e['note']])

    ws = wb.create_sheet('Payments')
    ws.append(['Date', 'Customer', 'Amount (Rs)', 'Note'])
    for p in data['payments']:
        ws.append([p['date'], p['customer'], float(p['amount']), p['note']])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="farm-report-{month}.xlsx"'
    wb.save(response)
    return response


@api_view(['POST'])
def reset_demo(request):
    from .seed import seed_demo_data
    seed_demo_data(reset=True)
    return Response({'detail': 'Demo data restored.'})


@api_view(['POST'])
def clear_all(request):
    Delivery.objects.all().delete()
    Production.objects.all().delete()
    Expense.objects.all().delete()
    Payment.objects.all().delete()
    Customer.objects.all().delete()
    return Response({'detail': 'All data cleared.'})
