from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Customer
from .serializers import CustomerSerializer
from apps.accounts.permissions import CanManageSales

from django.db import transaction

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all().order_by('-id')
    serializer_class = CustomerSerializer
    permission_classes = [CanManageSales]

    def destroy(self, request, *args, **kwargs):
        customer = self.get_object()
        with transaction.atomic():
            customer.ledger_entries.all().delete()
            for so in customer.sales_orders.all():
                so.items.all().delete()
                so.delete()
            customer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['delete', 'post'], url_path='clear-all')
    def clear_all(self, request):
        with transaction.atomic():
            from apps.sales.models import SalesOrder, SalesOrderItem
            from apps.payments.models import CustomerLedger
            CustomerLedger.objects.all().delete()
            SalesOrderItem.objects.all().delete()
            SalesOrder.objects.all().delete()
            Customer.objects.all().delete()
        return Response({'detail': 'All customers and customer records cleared successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def ledger(self, request, pk=None):
        customer = self.get_object()
        entries = customer.ledger_entries.all().order_by('-transaction_date', '-id')
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
