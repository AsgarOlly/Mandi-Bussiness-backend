from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Customer
from .serializers import CustomerSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all().order_by('-id')
    serializer_class = CustomerSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=['get'])
    def ledger(self, request, pk=None):
        customer = self.get_object()
        entries = customer.ledger_entries.all().order_by('-transaction_date')
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
            'customer_name': customer.customer_name,
            'current_balance': float(customer.current_balance),
            'entries': data
        })
