import datetime
from decimal import Decimal
from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response

from .models import CustomerLedger, SupplierLedger, Payment
from .serializers import CustomerLedgerSerializer, SupplierLedgerSerializer, PaymentSerializer
from apps.customers.models import Customer
from apps.suppliers.models import Supplier

class CustomerLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomerLedger.objects.all().select_related('customer').order_by('-transaction_date', '-id')
    serializer_class = CustomerLedgerSerializer
    permission_classes = [permissions.AllowAny]

class SupplierLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SupplierLedger.objects.all().select_related('supplier').order_by('-transaction_date', '-id')
    serializer_class = SupplierLedgerSerializer
    permission_classes = [permissions.AllowAny]

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().select_related('customer', 'supplier').order_by('-payment_date', '-id')
    serializer_class = PaymentSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        if not data.get('party_type'):
            if data.get('customer') or data.get('payment_type') == 'INWARD':
                data['party_type'] = 'CUSTOMER'
            elif data.get('supplier') or data.get('payment_type') == 'OUTWARD':
                data['party_type'] = 'SUPPLIER'
            else:
                data['party_type'] = 'CUSTOMER'

        if not data.get('payment_method') and data.get('payment_mode'):
            data['payment_method'] = data.get('payment_mode')
        if not data.get('transaction_reference') and data.get('reference_number'):
            data['transaction_reference'] = data.get('reference_number')
        if not data.get('notes') and data.get('description'):
            data['notes'] = data.get('description')

        if not data.get('payment_no'):
            count = Payment.objects.count() + 1
            today_str = datetime.date.today().strftime('%Y%m%d')
            data['payment_no'] = f"PAY-{today_str}-{count:04d}"

        with transaction.atomic():
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            payment = serializer.save()


            amt = Decimal(str(payment.amount))

            if payment.party_type == 'CUSTOMER' and payment.customer:
                cust = payment.customer
                cust.current_balance = max(Decimal('0'), cust.current_balance - amt)
                cust.save()

                CustomerLedger.objects.create(
                    customer=cust,
                    transaction_date=payment.payment_date,
                    transaction_type='PAYMENT_RECEIVED',
                    reference_type='PAYMENT',
                    reference_id=payment.payment_no,
                    debit=0,
                    credit=amt,
                    balance=cust.current_balance,
                    description=f"Payment received via {payment.payment_method} Ref: {payment.transaction_reference or '-'}"
                )

            elif payment.party_type == 'SUPPLIER' and payment.supplier:
                supp = payment.supplier
                supp.current_balance = max(Decimal('0'), supp.current_balance - amt)
                supp.save()

                SupplierLedger.objects.create(
                    supplier=supp,
                    transaction_date=payment.payment_date,
                    transaction_type='PAYMENT_MADE',
                    reference_type='PAYMENT',
                    reference_id=payment.payment_no,
                    debit=amt,
                    credit=0,
                    balance=supp.current_balance,
                    description=f"Payment made via {payment.payment_method} Ref: {payment.transaction_reference or '-'}"
                )

            return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
