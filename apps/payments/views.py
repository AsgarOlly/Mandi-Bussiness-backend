import datetime
from decimal import Decimal
from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import CustomerLedger, SupplierLedger
from .serializers import CustomerLedgerSerializer, SupplierLedgerSerializer
from apps.customers.models import Customer
from apps.suppliers.models import Supplier
from apps.accounts.permissions import CanManagePayments

class CustomerLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomerLedger.objects.all().select_related('customer').order_by('-transaction_date', '-id')
    serializer_class = CustomerLedgerSerializer
    permission_classes = [CanManagePayments]

    def get_queryset(self):
        qs = super().get_queryset()
        cust_id = self.request.query_params.get('customer')
        if cust_id:
            qs = qs.filter(customer_id=cust_id)
        return qs


class SupplierLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SupplierLedger.objects.all().select_related('supplier').order_by('-transaction_date', '-id')
    serializer_class = SupplierLedgerSerializer
    permission_classes = [CanManagePayments]

    def get_queryset(self):
        qs = super().get_queryset()
        supp_id = self.request.query_params.get('supplier')
        if supp_id:
            qs = qs.filter(supplier_id=supp_id)
        return qs
