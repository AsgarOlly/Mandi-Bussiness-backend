import datetime
import io
import openpyxl
from decimal import Decimal
from django.db import transaction
from django.http import HttpResponse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import SalesOrder, SalesOrderItem, SalesInvoice
from .serializers import (
    SalesOrderSerializer,
    SalesOrderItemSerializer, SalesInvoiceSerializer
)
from apps.products.models import Product, ProductVariety, Category
from apps.customers.models import Customer
from apps.payments.models import CustomerLedger

class SalesInvoiceViewSet(viewsets.ModelViewSet):
    queryset = SalesInvoice.objects.all().select_related('customer', 'sales_order').order_by('-invoice_date')
    serializer_class = SalesInvoiceSerializer
    permission_classes = [permissions.AllowAny]

class SalesOrderViewSet(viewsets.ModelViewSet):
    queryset = SalesOrder.objects.all().select_related('customer').prefetch_related('items', 'items__product', 'items__variety').order_by('-order_date', '-id')
    serializer_class = SalesOrderSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        items_data = data.pop('items', [])

        with transaction.atomic():
            truck_val = data.get('truck_number') or data.get('truck')
            if truck_val:
                data['truck_number'] = str(truck_val).strip().upper()

            if not data.get('sales_order_no'):
                count = SalesOrder.objects.count() + 1
                today_str = datetime.date.today().strftime('%Y%m%d')
                data['sales_order_no'] = f"SO-{today_str}-{count:04d}"

            # Auto-resolve or create customer from manual input
            if not data.get('customer') and data.get('customer_name'):
                cust_name = str(data.get('customer_name')).strip()
                cust = Customer.objects.filter(customer_name__iexact=cust_name).first()
                if not cust:
                    count = Customer.objects.count() + 1
                    cust = Customer.objects.create(
                        customer_code=f"CUST-{count:03d}",
                        customer_name=cust_name,
                        phone="9876543210",
                        city="Mandi"
                    )
                data['customer'] = cust.id
            elif not data.get('customer') and Customer.objects.exists():
                data['customer'] = Customer.objects.first().id
            elif not data.get('customer'):
                cust = Customer.objects.create(
                    customer_code="CUST-0001",
                    customer_name="Walk-in Customer",
                    phone="9876543210",
                    city="Mandi"
                )
                data['customer'] = cust.id

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            so = serializer.save()

            for item_info in items_data:
                prod_id = item_info.get('product')
                if not prod_id or not Product.objects.filter(id=prod_id).exists():
                    p = Product.objects.first()
                    if not p:
                        cat = Category.objects.first() or Category.objects.create(name='Fresh Fruits')
                        p = Product.objects.create(category=cat, name='General Fruit', product_code='PROD-GEN-01')
                    prod_id = p.id

                var_id = item_info.get('variety')
                if not var_id or not ProductVariety.objects.filter(id=var_id).exists():
                    v = ProductVariety.objects.filter(product_id=prod_id).first()
                    if not v:
                        v = ProductVariety.objects.create(product_id=prod_id, variety_name='Standard', variety_code=f"VAR-{prod_id}-01")
                    var_id = v.id

                SalesOrderItem.objects.create(
                    sales_order=so,
                    product_id=prod_id,
                    variety_id=var_id,
                    lot_reference=str(item_info.get('lot_reference') or item_info.get('batch') or ''),
                    quantity_boxes=int(item_info.get('quantity_boxes', 0)),
                    gross_weight=Decimal(str(item_info.get('gross_weight', 0))),
                    tare_weight=Decimal(str(item_info.get('tare_weight', 0))),
                    net_weight=Decimal(str(item_info.get('net_weight', 0))),
                    selling_rate=Decimal(str(item_info.get('selling_rate', 0))),
                    cost_rate=Decimal(str(item_info.get('cost_rate', 0))),
                    discount=Decimal(str(item_info.get('discount', 0))),
                    tax_rate=Decimal(str(item_info.get('tax_rate', 0))),
                    quality_grade=item_info.get('quality_grade', 'Grade A'),
                )

            so.calculate_totals()

            if data.get('status') == 'DISPATCHED':
                self._execute_dispatch(so)

            return Response(SalesOrderSerializer(so).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='dispatch')
    def mark_dispatch(self, request, pk=None):
        so = self.get_object()
        if so.status in ['DISPATCHED', 'DELIVERED', 'COMPLETED']:
            return Response({'error': 'Order already dispatched'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            self._execute_dispatch(so)

        return Response(SalesOrderSerializer(so).data)

    def _execute_dispatch(self, so):
        so.status = 'DISPATCHED'

        # Generate Sales Invoice
        inv_no = f"INV-{so.sales_order_no.replace('SO-', '')}"
        invoice, _ = SalesInvoice.objects.get_or_create(
            sales_order=so,
            defaults={
                'invoice_no': inv_no,
                'customer': so.customer,
                'invoice_date': so.order_date,
                'due_date': so.delivery_date or (so.order_date + datetime.timedelta(days=7)),
                'subtotal': so.subtotal,
                'discount': so.discount,
                'tax_amount': so.tax_amount,
                'transport_charge': so.transport_charge,
                'grand_total': so.grand_total,
                'paid_amount': so.paid_amount,
                'due_amount': so.due_amount,
                'payment_status': 'PAID' if so.due_amount == 0 else ('PARTIALLY_PAID' if so.paid_amount > 0 else 'UNPAID'),
            }
        )

        # Update Customer Balance and Ledger
        so.customer.current_balance += so.grand_total
        so.customer.save()

        CustomerLedger.objects.create(
            customer=so.customer,
            transaction_date=so.order_date,
            transaction_type='SALES_INVOICE',
            reference_type='SALES_INVOICE',
            reference_id=inv_no,
            debit=so.grand_total,
            credit=0,
            balance=so.customer.current_balance,
            description=f"Sales Invoice {inv_no} for Order {so.sales_order_no}"
        )

        so.save()
        return True, "Dispatched successfully"

    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sales"

        headers = [
            "Sales Order No", "Customer", "Warehouse", "Truck", "Order Date",
            "Fruit", "Variety", "Boxes", "Weight (KG)", "Selling Rate", "Total Margin", "Line Total"
        ]
        ws.append(headers)

        for so in self.get_queryset():
            for item in so.items.all():
                ws.append([
                    so.sales_order_no,
                    so.customer.customer_name,
                    so.warehouse_name,
                    so.truck_number or "-",
                    str(so.order_date),
                    item.product.name,
                    item.variety.variety_name,
                    item.quantity_boxes,
                    float(item.net_weight),
                    float(item.selling_rate),
                    float(item.gross_margin),
                    float(item.line_total)
                ])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = 'attachment; filename="sales_export.xlsx"'
        return response
