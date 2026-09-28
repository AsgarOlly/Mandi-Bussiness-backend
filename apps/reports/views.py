import datetime
from decimal import Decimal
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.purchases.models import PurchaseOrder, PurchaseOrderItem, SupplierTruckPayment
from apps.sales.models import SalesOrder, SalesOrderItem
from apps.customers.models import Customer
from apps.suppliers.models import Supplier

@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_summary(request):
    today = datetime.date.today()

    # Today's Purchases
    today_pos = PurchaseOrder.objects.filter(purchase_date=today)
    today_purchase_amt = sum(p.grand_total for p in today_pos)
    today_boxes_in = sum(
        sum(item.quantity_boxes for item in p.items.all()) for p in today_pos
    )

    # Today's Sales
    today_sos = SalesOrder.objects.filter(order_date=today)
    today_sales_amt = sum(s.grand_total for s in today_sos)
    today_boxes_sold = sum(
        sum(item.quantity_boxes for item in s.items.all()) for s in today_sos
    )
    today_weight_sold = sum(
        sum(float(item.net_weight) for item in s.items.all()) for s in today_sos
    )

    # Stock Valuation from Purchase and Sales items
    total_in_boxes = sum(item.quantity_boxes for item in PurchaseOrderItem.objects.all())
    total_sold_boxes = sum(item.quantity_boxes for item in SalesOrderItem.objects.all())
    total_stock_boxes = max(0, total_in_boxes - total_sold_boxes)

    total_in_weight = sum(float(item.net_weight) for item in PurchaseOrderItem.objects.all())
    total_sold_weight = sum(float(item.net_weight) for item in SalesOrderItem.objects.all())
    total_stock_weight = max(0.0, total_in_weight - total_sold_weight)

    total_in_val = sum(float(item.line_total) for item in PurchaseOrderItem.objects.all())
    total_sold_val = sum(float(item.line_total) for item in SalesOrderItem.objects.all())
    total_stock_value = max(0.0, total_in_val - total_sold_val)

    # Outstanding Balances
    cust_outstanding = sum(c.current_balance for c in Customer.objects.all())
    supp_outstanding = sum(s.current_balance for s in Supplier.objects.all())

    # Top selling fruits
    top_items = (
        SalesOrderItem.objects.values('product__name')
        .annotate(total_boxes=Sum('quantity_boxes'), total_rev=Sum('line_total'))
        .order_by('-total_boxes')[:5]
    )
    top_fruits = [
        {'name': item['product__name'], 'boxes': item['total_boxes'] or 0, 'revenue': float(item['total_rev'] or 0)}
        for item in top_items
    ]

    # Recent Trucks from Truck Payments or Purchase Orders
    recent_payments = SupplierTruckPayment.objects.order_by('-payment_date', '-id')[:6]
    truck_data = [
        {
            'id': p.id,
            'truck_number': p.truck_number,
            'party': p.supplier.supplier_name if p.supplier else 'Produce Transport',
            'slot': 'Produce Arrival',
            'status': 'ACTIVE',
            'net_weight': float(p.no_of_boxes * 20),
            'purpose': f'{p.fruit_name} ({p.no_of_boxes} boxes)'
        } for p in recent_payments
    ]

    # 7-day Sales vs Purchases trend
    chart_data = []
    for i in range(6, -1, -1):
        d = today - datetime.timedelta(days=i)
        d_str = d.strftime('%d %b')
        s_val = sum(s.grand_total for s in SalesOrder.objects.filter(order_date=d))
        p_val = sum(p.grand_total for p in PurchaseOrder.objects.filter(purchase_date=d))
        chart_data.append({
            'date': d_str,
            'sales': float(s_val),
            'purchases': float(p_val)
        })

    return Response({
        'today_purchase': float(today_purchase_amt),
        'today_sales': float(today_sales_amt),
        'stock_value': float(total_stock_value),
        'boxes_in': today_boxes_in,
        'boxes_sold': today_boxes_sold,
        'weight_sold_kg': today_weight_sold,
        'wastage_boxes': 0,
        'wastage_loss': 0.0,
        'customer_outstanding': float(cust_outstanding),
        'supplier_outstanding': float(supp_outstanding),
        'total_stock_boxes': total_stock_boxes,
        'total_stock_weight_kg': total_stock_weight,
        'top_fruits': top_fruits,
        'recent_trucks': truck_data,
        'trend_chart': chart_data
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def daily_sales_report(request):
    date_str = request.GET.get('date', str(datetime.date.today()))
    orders = SalesOrder.objects.filter(order_date=date_str).select_related('customer')
    total_orders = orders.count()
    total_boxes = sum(sum(item.quantity_boxes for item in o.items.all()) for o in orders)
    total_weight = sum(sum(float(item.net_weight) for item in o.items.all()) for o in orders)
    gross_sales = sum(o.subtotal for o in orders)
    total_discount = sum(o.discount for o in orders)
    total_tax = sum(o.tax_amount for o in orders)
    net_sales = sum(o.grand_total for o in orders)
    total_received = sum(o.paid_amount for o in orders)
    outstanding = sum(o.due_amount for o in orders)

    return Response({
        'date': date_str,
        'total_orders': total_orders,
        'total_boxes': total_boxes,
        'total_weight_kg': total_weight,
        'gross_sales': float(gross_sales),
        'discount': float(total_discount),
        'tax': float(total_tax),
        'net_sales': float(net_sales),
        'received': float(total_received),
        'outstanding': float(outstanding)
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def profit_loss_report(request):
    sales = SalesOrder.objects.all()
    total_revenue = sum(s.grand_total for s in sales)
    total_cogs = Decimal('0')
    total_margin = Decimal('0')

    for s in sales:
        for item in s.items.all():
            cost = item.cost_rate * (item.net_weight if item.net_weight > 0 else Decimal(str(item.quantity_boxes)))
            total_cogs += cost
            total_margin += item.gross_margin

    return Response({
        'revenue': float(total_revenue),
        'cogs': float(total_cogs),
        'gross_profit': float(total_margin),
        'expenses': 0.0,
        'wastage_loss': 0.0,
        'net_profit': float(total_margin),
    })
