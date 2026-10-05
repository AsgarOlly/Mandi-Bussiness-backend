import datetime
import io
import openpyxl
from decimal import Decimal
from django.db import transaction
from django.http import HttpResponse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import PurchaseOrder, PurchaseOrderItem, SupplierTruckPayment
from .serializers import PurchaseOrderSerializer, PurchaseOrderItemSerializer, SupplierTruckPaymentSerializer
from apps.products.models import Product, ProductVariety, Category
from apps.suppliers.models import Supplier
from apps.payments.models import SupplierLedger
from apps.inventory.models import InventoryLot, InventoryTransaction
from apps.accounts.permissions import CanManagePurchases

class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all().select_related('supplier').prefetch_related(
        'items', 'items__product', 'items__variety'
    ).order_by('-purchase_date', '-id')
    serializer_class = PurchaseOrderSerializer
    permission_classes = [CanManagePurchases]

    def destroy(self, request, *args, **kwargs):
        po = self.get_object()
        with transaction.atomic():
            SupplierLedger.objects.filter(reference_id=po.purchase_no).delete()
            po.items.all().delete()
            po.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['delete', 'post'], url_path='clear-all')
    def clear_all(self, request):
        with transaction.atomic():
            SupplierTruckPayment.objects.all().delete()
            PurchaseOrderItem.objects.all().delete()
            PurchaseOrder.objects.all().delete()
        return Response({'detail': 'All purchases and truck payments cleared successfully.'}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        items_data = data.pop('items', [])

        with transaction.atomic():
            truck_val = data.get('truck_number') or data.get('truck')
            if truck_val:
                data['truck_number'] = str(truck_val).strip().upper()

            # Resolve supplier
            supplier_val = data.get('supplier')
            supplier_name = (data.get('supplier_name') or '').strip()

            supplier_obj = None
            if supplier_val and str(supplier_val).isdigit():
                supplier_obj = Supplier.objects.filter(id=int(supplier_val)).first()

            if not supplier_obj and supplier_name:
                supplier_obj = Supplier.objects.filter(supplier_name__iexact=supplier_name).first()
                if not supplier_obj:
                    count = Supplier.objects.count() + 1
                    supplier_obj = Supplier.objects.create(
                        supplier_code=f"SUP-{count:04d}",
                        supplier_name=supplier_name,
                        phone=data.get('phone', '') or ''
                    )
            elif not supplier_obj and not Supplier.objects.exists():
                supplier_obj = Supplier.objects.create(
                    supplier_code="SUP-0001",
                    supplier_name="Default Supplier",
                    phone="9876543210"
                )
            elif not supplier_obj:
                return Response(
                    {'error': 'Valid supplier ID or supplier_name is required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            data['supplier'] = supplier_obj.id

            if not data.get('purchase_no'):
                count = PurchaseOrder.objects.count() + 1
                today_str = datetime.date.today().strftime('%Y%m%d')
                data['purchase_no'] = f"PO-{today_str}-{count:04d}"

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            po = serializer.save()

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
                    return Response(
                        {'error': 'Product ID or valid fruit name is required for each purchase item.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

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
                rate = Decimal(str(item_info.get('purchase_rate', 0)))
                dmg_boxes = int(item_info.get('damage_boxes', 0))
                acc_boxes = int(item_info.get('accepted_boxes', max(0, qty_boxes - dmg_boxes)))

                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    product=prod_obj,
                    variety=var_obj,
                    quantity_boxes=qty_boxes,
                    purchase_rate=rate,
                    damage_boxes=dmg_boxes,
                    accepted_boxes=acc_boxes,
                )

            po.calculate_totals()

            if data.get('status') == 'RECEIVED':
                self._execute_receive(po, user=request.user)

            return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        po = self.get_object()
        if po.status in ['RECEIVED', 'COMPLETED']:
            return Response({'error': 'Order has already been received.'}, status=status.HTTP_400_BAD_REQUEST)
        if po.status == 'CANCELLED':
            return Response({'error': 'Cannot receive a cancelled order.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            self._execute_receive(po, user=request.user)

        return Response(PurchaseOrderSerializer(po).data)

    def _execute_receive(self, po, user=None):
        po.status = 'RECEIVED'

        # Create or update Inventory Lots & Transactions for each item
        for item in po.items.all():
            landed_box = (item.line_total / Decimal(str(item.quantity_boxes))) if item.quantity_boxes > 0 else item.purchase_rate

            lot_no = f"LOT-{po.purchase_no}-{item.id}"
            lot, lot_created = InventoryLot.objects.get_or_create(
                lot_number=lot_no,
                defaults={
                    'supplier': po.supplier,
                    'truck_number': po.truck_number,
                    'product': item.product,
                    'variety': item.variety,
                    'warehouse_name': po.warehouse_name,
                    'purchase_order_item': item,
                    'purchase_date': po.purchase_date,
                    'received_boxes': item.accepted_boxes,
                    'available_boxes': item.accepted_boxes,
                    'received_weight': Decimal('0'),
                    'available_weight': Decimal('0'),
                    'landed_cost_per_box': landed_box,
                    'landed_cost_per_kg': Decimal('0'),
                    'status': 'ACTIVE'
                }
            )

            if lot_created:
                InventoryTransaction.objects.create(
                    lot=lot,
                    product=item.product,
                    variety=item.variety,
                    warehouse_name=po.warehouse_name,
                    transaction_type='PURCHASE_RECEIPT',
                    reference_type='PURCHASE_ORDER',
                    reference_id=po.purchase_no,
                    quantity_boxes=item.accepted_boxes,
                    weight_kg=Decimal('0'),
                    unit_cost=landed_box,
                    total_cost=item.line_total,
                    created_by=user if (user and user.is_authenticated) else None,
                    notes=f"Received via Purchase Order {po.purchase_no} (Truck: {po.truck_number or 'N/A'})"
                )

        # Update Supplier Ledger idempotently
        ledger_exists = SupplierLedger.objects.filter(
            supplier=po.supplier,
            transaction_type='PURCHASE_BILL',
            reference_id=po.purchase_no
        ).exists()

        if not ledger_exists:
            po.supplier.current_balance += po.grand_total
            po.supplier.save()

            SupplierLedger.objects.create(
                supplier=po.supplier,
                transaction_date=po.purchase_date,
                transaction_type='PURCHASE_BILL',
                reference_type='PURCHASE_ORDER',
                reference_id=po.purchase_no,
                credit=po.grand_total,
                debit=Decimal('0'),
                balance=po.supplier.current_balance,
                description=f"Purchase Bill {po.purchase_no} from {po.supplier.supplier_name}"
            )

        po.save()

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        po = self.get_object()
        if po.status == 'CANCELLED':
            return Response({'error': 'Order is already cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if po.status in ['RECEIVED', 'COMPLETED']:
                # Verify lots are not partially sold
                for item in po.items.all():
                    for lot in item.inventory_lots.all():
                        if lot.available_boxes < lot.received_boxes:
                            return Response(
                                {'error': f'Cannot cancel purchase order. Lot {lot.lot_number} has already had boxes sold.'},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        lot.status = 'DEPLETED'
                        lot.available_boxes = 0
                        lot.available_weight = Decimal('0')
                        lot.save()

                        InventoryTransaction.objects.create(
                            lot=lot,
                            product=lot.product,
                            variety=lot.variety,
                            warehouse_name=lot.warehouse_name,
                            transaction_type='PURCHASE_RETURN',
                            reference_type='PURCHASE_ORDER_CANCEL',
                            reference_id=po.purchase_no,
                            quantity_boxes=-lot.received_boxes,
                            weight_kg=-lot.received_weight,
                            unit_cost=lot.landed_cost_per_box,
                            total_cost=-item.line_total,
                            created_by=request.user if request.user.is_authenticated else None,
                            notes=f"Reversal of Purchase Order {po.purchase_no}"
                        )

                # Reversal in supplier ledger
                po.supplier.current_balance = max(Decimal('0'), po.supplier.current_balance - po.grand_total)
                po.supplier.save()

                SupplierLedger.objects.create(
                    supplier=po.supplier,
                    transaction_date=datetime.date.today(),
                    transaction_type='PURCHASE_RETURN',
                    reference_type='PURCHASE_CANCEL',
                    reference_id=po.purchase_no,
                    debit=po.grand_total,
                    credit=Decimal('0'),
                    balance=po.supplier.current_balance,
                    description=f"Reversal / Cancellation of Purchase Order {po.purchase_no}"
                )

            po.status = 'CANCELLED'
            po.save()

        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=False, methods=['post'], url_path='import_excel')
    def import_excel(self, request):
        rows = request.data.get('rows', [])
        if not rows:
            return Response({'error': 'No rows provided for import.'}, status=status.HTTP_400_BAD_REQUEST)

        results = {'success': 0, 'errors': [], 'created_orders': []}
        today = datetime.date.today()

        with transaction.atomic():
            for idx, r in enumerate(rows):
                sup_name = str(r.get('Supplier') or r.get('supplier') or '').strip()
                fruit_name = str(r.get('Fruit') or r.get('fruit') or '').strip()
                variety_name = str(r.get('Variety') or r.get('variety') or '').strip() or 'Standard'
                truck = str(r.get('Truck') or r.get('truck') or '').strip().upper()

                try:
                    boxes = int(r.get('Boxes') or r.get('boxes') or 0)
                    weight = Decimal(str(r.get('NetWeight') or r.get('net_weight') or 0))
                    rate = Decimal(str(r.get('PurchaseRate') or r.get('purchase_rate') or 0))
                except (ValueError, TypeError) as num_err:
                    results['errors'].append({'row': idx + 1, 'error': f'Invalid numbers in row: {num_err}'})
                    continue

                if not sup_name or not fruit_name or boxes <= 0 or rate <= 0:
                    results['errors'].append({'row': idx + 1, 'error': 'Missing required fields (Supplier, Fruit, Boxes > 0, Rate > 0).'})
                    continue

                # Find or create supplier
                supplier = Supplier.objects.filter(supplier_name__iexact=sup_name).first()
                if not supplier:
                    count = Supplier.objects.count() + 1
                    supplier = Supplier.objects.create(
                        supplier_code=f"SUP-{count:04d}",
                        supplier_name=sup_name
                    )

                # Find or create category and product
                cat = Category.objects.first() or Category.objects.create(name='Fresh Fruits')
                product = Product.objects.filter(name__iexact=fruit_name).first()
                if not product:
                    count = Product.objects.count() + 1
                    product = Product.objects.create(
                        category=cat,
                        name=fruit_name,
                        product_code=f"PROD-{count:04d}"
                    )

                # Find or create variety
                variety = ProductVariety.objects.filter(product=product, variety_name__iexact=variety_name).first()
                if not variety:
                    variety = ProductVariety.objects.create(
                        product=product,
                        variety_name=variety_name
                    )

                po_count = PurchaseOrder.objects.count() + 1
                today_str = today.strftime('%Y%m%d')
                po_no = f"PO-{today_str}-{po_count:04d}"

                po = PurchaseOrder.objects.create(
                    purchase_no=po_no,
                    supplier=supplier,
                    truck_number=truck,
                    purchase_date=today,
                    status='RECEIVED',
                    warehouse_name=r.get('warehouse_name', 'Central Cold Hub')
                )

                item = PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    product=product,
                    variety=variety,
                    quantity_boxes=boxes,
                    purchase_rate=rate,
                    accepted_boxes=boxes
                )

                po.calculate_totals()
                self._execute_receive(po, user=request.user)
                results['success'] += 1
                results['created_orders'].append(po_no)

        return Response(results, status=status.HTTP_201_CREATED if results['success'] > 0 else status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Purchases"

        headers = [
            "Purchase No", "Supplier", "Warehouse", "Truck", "Date",
            "Fruit", "Variety", "Boxes", "Rate/Box", "Total"
        ]
        ws.append(headers)

        for po in self.get_queryset():
            for item in po.items.all():
                ws.append([
                    po.purchase_no,
                    po.supplier.supplier_name,
                    po.warehouse_name,
                    po.truck_number or "-",
                    str(po.purchase_date),
                    item.product.name,
                    item.variety.variety_name,
                    item.quantity_boxes,
                    float(item.purchase_rate),
                    float(item.line_total)
                ])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = 'attachment; filename="purchases_export.xlsx"'
        return response


class SupplierTruckPaymentViewSet(viewsets.ModelViewSet):
    queryset = SupplierTruckPayment.objects.all().select_related('supplier').order_by('-payment_date', '-id')
    serializer_class = SupplierTruckPaymentSerializer
    permission_classes = [CanManagePurchases]

    def destroy(self, request, *args, **kwargs):
        stp = self.get_object()
        with transaction.atomic():
            stp.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        qs = super().get_queryset()
        supplier_id = self.request.query_params.get('supplier') or self.request.query_params.get('supplier_id')
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        truck = self.request.query_params.get('truck_number') or self.request.query_params.get('truck')
        if truck:
            qs = qs.filter(truck_number__iexact=truck)
        return qs

    def create(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        supplier_id = data.get('supplier')
        clean_sup_name = (data.get('supplier_name') or '').strip()

        supplier_obj = None
        if supplier_id and str(supplier_id).isdigit():
            supplier_obj = Supplier.objects.filter(id=int(supplier_id)).first()

        if not supplier_obj and clean_sup_name:
            supplier_obj = Supplier.objects.filter(supplier_name__iexact=clean_sup_name).first()

        if not supplier_obj and clean_sup_name:
            count = Supplier.objects.count() + 1
            code = f"SUP-{count:04d}"
            while Supplier.objects.filter(supplier_code=code).exists():
                count += 1
                code = f"SUP-{count:04d}"
            supplier_obj = Supplier.objects.create(
                supplier_code=code,
                supplier_name=clean_sup_name,
                phone=data.get('phone', '') or ''
            )

        if not supplier_obj:
            return Response(
                {'error': 'Supplier is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        data['supplier'] = supplier_obj.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(SupplierTruckPaymentSerializer(obj).data, status=status.HTTP_201_CREATED)
