from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from decimal import Decimal
from .models import InventoryLot, InventoryTransaction
from .serializers import (
    InventoryLotSerializer,
    InventoryTransactionSerializer
)
from apps.accounts.permissions import CanManageInventory

class InventoryLotViewSet(viewsets.ModelViewSet):
    queryset = InventoryLot.objects.all().select_related(
        'supplier', 'product', 'variety'
    ).order_by('-purchase_date', '-id')
    serializer_class = InventoryLotSerializer
    permission_classes = [CanManageInventory]

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())
        supplier_id = self.request.query_params.get('supplier')
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        truck = self.request.query_params.get('truck_number')
        if truck:
            qs = qs.filter(truck_number__iexact=truck.strip())
        product_id = self.request.query_params.get('product')
        if product_id:
            qs = qs.filter(product_id=product_id)
        return qs

    @action(detail=True, methods=['post'])
    def record_wastage(self, request, pk=None):
        lot = self.get_object()
        boxes = int(request.data.get('boxes', 0))
        weight = Decimal(str(request.data.get('weight_kg', 0)))
        notes = request.data.get('notes', 'Damaged / rotten produce written off')

        if boxes <= 0 and weight <= 0:
            return Response({'error': 'Specify positive boxes or weight for wastage.'}, status=status.HTTP_400_BAD_REQUEST)

        if boxes > lot.available_boxes or weight > lot.available_weight:
            return Response({'error': 'Wastage exceeds available stock in this lot.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            lot.available_boxes = max(0, lot.available_boxes - boxes)
            lot.available_weight = max(Decimal('0'), lot.available_weight - weight)
            lot.update_status()

            cost = (Decimal(str(boxes)) * lot.landed_cost_per_box) if lot.landed_cost_per_box > 0 else (weight * lot.landed_cost_per_kg)
            InventoryTransaction.objects.create(
                lot=lot,
                product=lot.product,
                variety=lot.variety,
                warehouse_name=lot.warehouse_name,
                transaction_type='WASTAGE',
                reference_type='LOT_WASTAGE',
                reference_id=lot.lot_number,
                quantity_boxes=-boxes,
                weight_kg=-weight,
                unit_cost=lot.landed_cost_per_box or lot.landed_cost_per_kg,
                total_cost=cost,
                created_by=request.user if request.user.is_authenticated else None,
                notes=notes
            )

        return Response(InventoryLotSerializer(lot).data)

    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        lot = self.get_object()
        new_boxes = int(request.data.get('new_boxes', lot.available_boxes))
        notes = request.data.get('notes', 'Physical audit stock adjustment')

        diff_boxes = new_boxes - lot.available_boxes
        with transaction.atomic():
            lot.available_boxes = max(0, new_boxes)
            lot.update_status()

            cost = abs(diff_boxes) * lot.landed_cost_per_box
            InventoryTransaction.objects.create(
                lot=lot,
                product=lot.product,
                variety=lot.variety,
                warehouse_name=lot.warehouse_name,
                transaction_type='STOCK_ADJUSTMENT',
                reference_type='MANUAL_ADJUSTMENT',
                reference_id=lot.lot_number,
                quantity_boxes=diff_boxes,
                weight_kg=0,
                unit_cost=lot.landed_cost_per_box,
                total_cost=cost,
                created_by=request.user if request.user.is_authenticated else None,
                notes=f"{notes} (Diff: {diff_boxes:+d} BX)"
            )

        return Response(InventoryLotSerializer(lot).data)


class InventoryTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InventoryTransaction.objects.all().select_related(
        'lot', 'product', 'variety', 'created_by'
    ).order_by('-date_time', '-id')
    serializer_class = InventoryTransactionSerializer
    permission_classes = [CanManageInventory]

    def get_queryset(self):
        qs = super().get_queryset()
        tx_type = self.request.query_params.get('type')
        if tx_type:
            qs = qs.filter(transaction_type=tx_type.upper())
        lot_id = self.request.query_params.get('lot')
        if lot_id:
            qs = qs.filter(lot_id=lot_id)
        product_id = self.request.query_params.get('product')
        if product_id:
            qs = qs.filter(product_id=product_id)
        return qs

