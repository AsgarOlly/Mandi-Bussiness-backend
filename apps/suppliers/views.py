from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Supplier
from .serializers import SupplierSerializer
from apps.payments.models import SupplierLedger

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by('-id')
    serializer_class = SupplierSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=['get'])
    def ledger(self, request, pk=None):
        supplier = self.get_object()
        entries = supplier.ledger_entries.all().order_by('-transaction_date')
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
