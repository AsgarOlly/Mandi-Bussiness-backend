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

class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all().select_related('supplier').prefetch_related('items', 'items__product', 'items__variety').order_by('-purchase_date', '-id')
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        items_data = data.pop('items', [])

        with transaction.atomic():
            # Handle truck_number
            truck_val = data.get('truck_number') or data.get('truck')
            if truck_val:
                data['truck_number'] = str(truck_val).strip().upper()

            # Ensure valid supplier
            supplier_val = data.get('supplier')
            if not supplier_val or not Supplier.objects.filter(id=supplier_val).exists():
                supp = Supplier.objects.first()
                if not supp:
                    supp = Supplier.objects.create(supplier_code="SUP-0001", supplier_name="Default Supplier", phone="9876543210", city="Delhi")
                data['supplier'] = supp.id

            if not data.get('purchase_no'):
                count = PurchaseOrder.objects.count() + 1
                today_str = datetime.date.today().strftime('%Y%m%d')
                data['purchase_no'] = f"PO-{today_str}-{count:04d}"

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            po = serializer.save()

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

                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    product_id=prod_id,
                    variety_id=var_id,
                    quantity_boxes=int(item_info.get('quantity_boxes', 0)),
                    gross_weight=Decimal(str(item_info.get('gross_weight', 0))),
                    tare_weight=Decimal(str(item_info.get('tare_weight', 0))),
                    net_weight=Decimal(str(item_info.get('net_weight', 0))),
                    purchase_rate=Decimal(str(item_info.get('purchase_rate', 0))),
                    discount=Decimal(str(item_info.get('discount', 0))),
                    tax_rate=Decimal(str(item_info.get('tax_rate', 0))),
                    quality_grade=item_info.get('quality_grade', 'Grade A'),
                    damage_boxes=int(item_info.get('damage_boxes', 0)),
                    accepted_boxes=int(item_info.get('accepted_boxes', item_info.get('quantity_boxes', 0))),
                )

            po.calculate_totals()

            if data.get('status') == 'RECEIVED':
                self._execute_receive(po)

            return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        po = self.get_object()
        if po.status == 'RECEIVED' or po.status == 'COMPLETED':
            return Response({'error': 'Order already received'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            self._execute_receive(po)

        return Response(PurchaseOrderSerializer(po).data)

    def _execute_receive(self, po):
        po.status = 'RECEIVED'
        total_weight = sum(item.net_weight for item in po.items.all()) or Decimal('1.0')
        total_charges = po.transport_charge + po.loading_charge + po.unloading_charge + po.commission_charge
        charge_per_kg = (total_charges / total_weight) if total_weight > 0 else Decimal('0')

        for item in po.items.all():
            landed = item.purchase_rate + charge_per_kg
            item.landed_cost_per_kg = landed
            item.save()

        # Update Supplier Ledger & Outstanding
        po.supplier.current_balance += po.grand_total
        po.supplier.save()

        SupplierLedger.objects.create(
            supplier=po.supplier,
            transaction_date=po.purchase_date,
            transaction_type='PURCHASE_BILL',
            reference_type='PURCHASE_ORDER',
            reference_id=po.purchase_no,
            credit=po.grand_total,
            debit=0,
            balance=po.supplier.current_balance,
            description=f"Purchase Bill {po.purchase_no} from {po.supplier.supplier_name}"
        )

        po.save()

    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Purchases"

        headers = [
            "Purchase No", "Supplier", "Warehouse", "Truck", "Date",
            "Fruit", "Variety", "Boxes", "Net Weight (KG)", "Rate/KG", "Total"
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
                    float(item.net_weight),
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
    permission_classes = [permissions.AllowAny]

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
                company_name=clean_sup_name,
                phone="9876543210",
                city="Delhi"
            )
        elif not supplier_obj:
            supplier_obj = Supplier.objects.first()
            if not supplier_obj:
                supplier_obj = Supplier.objects.create(
                    supplier_code="SUP-0001",
                    supplier_name="Default Supplier",
                    phone="9876543210",
                    city="Delhi"
                )

        data['supplier'] = supplier_obj.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
