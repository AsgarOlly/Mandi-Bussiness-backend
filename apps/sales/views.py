import datetime
import io
import openpyxl
from decimal import Decimal
from django.db import transaction
from django.http import HttpResponse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import SalesOrder, SalesOrderItem
from .serializers import SalesOrderSerializer, SalesOrderItemSerializer
from apps.products.models import Product, ProductVariety, Category
from apps.customers.models import Customer
from apps.payments.models import CustomerLedger
from apps.inventory.models import InventoryLot, InventoryTransaction
from apps.accounts.permissions import CanManageSales

class SalesOrderViewSet(viewsets.ModelViewSet):
    queryset = SalesOrder.objects.all().select_related('customer').prefetch_related(
        'items', 'items__product', 'items__variety'
    ).order_by('-order_date', '-id')
    serializer_class = SalesOrderSerializer
    permission_classes = [CanManageSales]

    def destroy(self, request, *args, **kwargs):
        so = self.get_object()
        with transaction.atomic():
            CustomerLedger.objects.filter(reference_id=so.sales_order_no).delete()
            so.items.all().delete()
            so.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['delete', 'post'], url_path='clear-all')
    def clear_all(self, request):
        with transaction.atomic():
            SalesOrderItem.objects.all().delete()
            SalesOrder.objects.all().delete()
        return Response({'detail': 'All sales orders cleared successfully.'}, status=status.HTTP_200_OK)

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

            # Customer resolution
            cust_id = data.get('customer')
            cust_name = str(data.get('customer_name') or '').strip()

            cust_obj = None
            if cust_id and str(cust_id).isdigit():
                cust_obj = Customer.objects.filter(id=int(cust_id)).first()

            if not cust_obj and cust_name:
                cust_obj = Customer.objects.filter(customer_name__iexact=cust_name).first()
                if not cust_obj:
                    count = Customer.objects.count() + 1
                    cust_obj = Customer.objects.create(
                        customer_code=f"CUST-{count:04d}",
                        customer_name=cust_name,
                        phone=data.get('phone', '') or ''
                    )
            elif not cust_obj and not Customer.objects.exists():
                cust_obj = Customer.objects.create(
                    customer_code="CUST-0001",
                    customer_name="Walk-in Customer",
                    phone="9876543210"
                )
            elif not cust_obj:
                return Response(
                    {'error': 'Customer ID or customer_name is required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            data['customer'] = cust_obj.id

            # Support single item shorthand from board
            if not items_data and (data.get('crates_sold') or data.get('boxes')):
                boxes_count = int(data.get('crates_sold') or data.get('boxes') or 0)
                rate_val = Decimal(str(data.get('rate_per_crate') or data.get('rate_per_box') or data.get('selling_rate') or 0))
                items_data = [{
                    'product_name': data.get('product_name') or data.get('fruit') or 'Produce',
                    'quantity_boxes': boxes_count,
                    'selling_rate': rate_val,
                }]

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            so = serializer.save()

            for item_info in items_data:
                prod_id = item_info.get('product')
                prod_name = (item_info.get('product_name') or item_info.get('fruit') or '').strip()

                prod_obj = None
                if prod_id and str(prod_id).isdigit():
                    prod_obj = Product.objects.filter(id=int(prod_id)).first()

                if not prod_obj and prod_name:
                    prod_obj = Product.objects.filter(name__iexact=prod_name).first()
                    if not prod_obj:
                        cat = Category.objects.first() or Category.objects.create(name='Fresh Fruits')
                        count = Product.objects.count() + 1
                        prod_obj = Product.objects.create(
                            category=cat,
                            name=prod_name,
                            product_code=f"PROD-{count:04d}"
                        )
                elif not prod_obj:
                    prod_obj = Product.objects.first()
                    if not prod_obj:
                        cat = Category.objects.first() or Category.objects.create(name='Fresh Fruits')
                        prod_obj = Product.objects.create(category=cat, name='General Fruit', product_code='PROD-GEN-01')

                var_id = item_info.get('variety')
                var_name = (item_info.get('variety_name') or '').strip()

                var_obj = None
                if var_id and str(var_id).isdigit():
                    var_obj = ProductVariety.objects.filter(id=int(var_id), product=prod_obj).first()

                if not var_obj and var_name:
                    var_obj = ProductVariety.objects.filter(product=prod_obj, variety_name__iexact=var_name).first()
                    if not var_obj:
                        var_obj = ProductVariety.objects.create(
                            product=prod_obj,
                            variety_name=var_name
                        )
                elif not var_obj:
                    var_obj = ProductVariety.objects.filter(product=prod_obj).first()
                    if not var_obj:
                        var_obj = ProductVariety.objects.create(
                            product=prod_obj,
                            variety_name='Standard'
                        )

                qty_boxes = int(item_info.get('quantity_boxes', 0))
                selling_rate = Decimal(str(item_info.get('selling_rate', 0)))

                SalesOrderItem.objects.create(
                    sales_order=so,
                    product=prod_obj,
                    variety=var_obj,
                    quantity_boxes=qty_boxes,
                    selling_rate=selling_rate,
                )

            so.calculate_totals()

            # If paid_amount passed from frontend
            if data.get('amount_paid') or data.get('paid_amount'):
                so.paid_amount = Decimal(str(data.get('amount_paid') or data.get('paid_amount')))
                so.due_amount = max(Decimal('0'), so.grand_total - so.paid_amount)
                so.save(update_fields=['paid_amount', 'due_amount'])

            if data.get('status') == 'DISPATCHED':
                self._execute_dispatch(so, user=request.user)

            return Response(SalesOrderSerializer(so).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='dispatch')
    def mark_dispatch(self, request, pk=None):
        so = self.get_object()
        if so.status in ['DISPATCHED', 'DELIVERED', 'COMPLETED']:
            return Response({'error': 'Order has already been dispatched.'}, status=status.HTTP_400_BAD_REQUEST)
        if so.status == 'CANCELLED':
            return Response({'error': 'Cannot dispatch a cancelled order.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            self._execute_dispatch(so, user=request.user)

        return Response(SalesOrderSerializer(so).data)

    def _execute_dispatch(self, so, user=None):
        so.status = 'DISPATCHED'

        # Inventory deduction
        for item in so.items.all():
            matched_lot = InventoryLot.objects.filter(
                product=item.product,
                variety=item.variety,
                status='ACTIVE',
                available_boxes__gte=item.quantity_boxes
            ).order_by('purchase_date', 'id').first()

            if not matched_lot:
                matched_lot = InventoryLot.objects.filter(
                    product=item.product,
                    status='ACTIVE',
                    available_boxes__gte=item.quantity_boxes
                ).order_by('purchase_date', 'id').first()

            if matched_lot:
                matched_lot.available_boxes = max(0, matched_lot.available_boxes - item.quantity_boxes)
                matched_lot.update_status()

                InventoryTransaction.objects.create(
                    lot=matched_lot,
                    product=item.product,
                    variety=item.variety,
                    warehouse_name=matched_lot.warehouse_name,
                    transaction_type='SALES_ISSUE',
                    reference_type='SALES_ORDER',
                    reference_id=so.sales_order_no,
                    quantity_boxes=-item.quantity_boxes,
                    weight_kg=Decimal('0'),
                    unit_cost=matched_lot.landed_cost_per_box,
                    total_cost=Decimal(str(item.quantity_boxes)) * matched_lot.landed_cost_per_box,
                    created_by=user if (user and user.is_authenticated) else None,
                    notes=f"Dispatched via Sales Order {so.sales_order_no} to {so.customer.customer_name}"
                )

        # Update Customer Balance and Ledger idempotently
        ledger_exists = CustomerLedger.objects.filter(
            customer=so.customer,
            transaction_type='SALES_INVOICE',
            reference_id=so.sales_order_no
        ).exists()

        if not ledger_exists:
            so.customer.current_balance += so.due_amount
            so.customer.save()

            CustomerLedger.objects.create(
                customer=so.customer,
                transaction_date=so.order_date,
                transaction_type='SALES_INVOICE',
                reference_type='SALES_ORDER',
                reference_id=so.sales_order_no,
                debit=so.grand_total,
                credit=so.paid_amount,
                balance=so.customer.current_balance,
                description=f"Sales Order {so.sales_order_no} for {so.customer.customer_name}"
            )

        so.save()

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        so = self.get_object()
        if so.status == 'CANCELLED':
            return Response({'error': 'Order is already cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if so.status in ['DISPATCHED', 'DELIVERED', 'COMPLETED']:
                # Return inventory
                for item in so.items.all():
                    lot = InventoryLot.objects.filter(product=item.product, variety=item.variety).first() or \
                          InventoryLot.objects.filter(product=item.product).first()
                    if lot:
                        lot.available_boxes += item.quantity_boxes
                        lot.update_status()

                        InventoryTransaction.objects.create(
                            lot=lot,
                            product=item.product,
                            variety=item.variety,
                            warehouse_name=lot.warehouse_name,
                            transaction_type='SALES_RETURN',
                            reference_type='SALES_ORDER_CANCEL',
                            reference_id=so.sales_order_no,
                            quantity_boxes=item.quantity_boxes,
                            weight_kg=Decimal('0'),
                            unit_cost=lot.landed_cost_per_box,
                            total_cost=Decimal(str(item.quantity_boxes)) * lot.landed_cost_per_box,
                            created_by=request.user if request.user.is_authenticated else None,
                            notes=f"Restored stock from cancelled Sales Order {so.sales_order_no}"
                        )

                # Reverse customer balance
                so.customer.current_balance = max(Decimal('0'), so.customer.current_balance - so.due_amount)
                so.customer.save()

                CustomerLedger.objects.create(
                    customer=so.customer,
                    transaction_date=datetime.date.today(),
                    transaction_type='SALES_RETURN',
                    reference_type='SALES_CANCEL',
                    reference_id=so.sales_order_no,
                    debit=Decimal('0'),
                    credit=so.grand_total,
                    balance=so.customer.current_balance,
                    description=f"Cancellation reversal of Sales Order {so.sales_order_no}"
                )

            so.status = 'CANCELLED'
            so.save()

        return Response(SalesOrderSerializer(so).data)

    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sales"

        headers = [
            "Sales Order No", "Customer", "Truck", "Order Date",
            "Fruit", "Variety", "Boxes", "Selling Rate", "Line Total"
        ]
        ws.append(headers)

        for so in self.get_queryset():
            for item in so.items.all():
                ws.append([
                    so.sales_order_no,
                    so.customer.customer_name,
                    so.truck_number or "-",
                    str(so.order_date),
                    item.product.name,
                    item.variety.variety_name,
                    item.quantity_boxes,
                    float(item.selling_rate),
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
