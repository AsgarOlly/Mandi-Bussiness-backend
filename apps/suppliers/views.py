from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Supplier
from .serializers import SupplierSerializer
from apps.payments.models import SupplierLedger
from apps.accounts.permissions import CanManagePurchases

from django.db import transaction

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by('-id')
    serializer_class = SupplierSerializer
    permission_classes = [CanManagePurchases]

    def destroy(self, request, *args, **kwargs):
        supplier = self.get_object()
        with transaction.atomic():
            supplier.ledger_entries.all().delete()
            supplier.truck_payments.all().delete()
            for po in supplier.purchases.all():
                po.items.all().delete()
                po.delete()
            supplier.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['delete', 'post'], url_path='clear-all')
    def clear_all(self, request):
        with transaction.atomic():
            from apps.purchases.models import PurchaseOrder, SupplierTruckPayment
            SupplierLedger.objects.all().delete()
            SupplierTruckPayment.objects.all().delete()
            for po in PurchaseOrder.objects.all():
                po.items.all().delete()
                po.delete()
            Supplier.objects.all().delete()
        return Response({'detail': 'All suppliers and supplier records cleared successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def ledger(self, request, pk=None):
        supplier = self.get_object()
        entries = supplier.ledger_entries.all().order_by('-transaction_date', '-id')
        data = [{
            'id': e.id,
            'date': e.transaction_date,
            'type': e.transaction_type,
            'reference': e.reference_id,
            'debit': float(e.debit),
            'credit': float(e.credit),
            'balance': float(e.balance),
            'description': e.description,
        } for e in entries]
        return Response({
            'supplier_name': supplier.supplier_name,
            'current_balance': float(supplier.current_balance),
            'entries': data
        })
