from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
import datetime
from apps.accounts.models import Role, UserProfile
from apps.customers.models import Customer
from apps.suppliers.models import Supplier
from apps.payments.models import CustomerLedger, SupplierLedger

class LedgerTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.super_role, _ = Role.objects.get_or_create(code='SUPER_ADMIN', defaults={'name': 'Super Admin'})
        self.user = User.objects.create_user(username='accountant', password='SecurePassword123!')
        UserProfile.objects.create(user=self.user, role=self.super_role)
        self.client.force_authenticate(user=self.user)

        self.customer = Customer.objects.create(
            customer_code='CUST-PAY-01',
            customer_name='Super Retailers',
            current_balance=Decimal('5000')
        )
        self.supplier = Supplier.objects.create(
            supplier_code='SUP-PAY-01',
            supplier_name='National Exim',
            current_balance=Decimal('8000')
        )

        CustomerLedger.objects.create(
            customer=self.customer,
            transaction_date=datetime.date.today(),
            transaction_type='SALES_INVOICE',
            reference_type='SALES_ORDER',
            reference_id='SO-0001',
            debit=Decimal('5000'),
            credit=Decimal('0'),
            balance=Decimal('5000'),
            description='Test invoice'
        )

        SupplierLedger.objects.create(
            supplier=self.supplier,
            transaction_date=datetime.date.today(),
            transaction_type='PURCHASE_BILL',
            reference_type='PURCHASE_ORDER',
            reference_id='PO-0001',
            debit=Decimal('0'),
            credit=Decimal('8000'),
            balance=Decimal('8000'),
            description='Test purchase bill'
        )

    def test_customer_ledger_list(self):
        res = self.client.get(f'/api/v1/payments/customer-ledger/?customer={self.customer.id}')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(len(res.data) >= 1)

    def test_supplier_ledger_list(self):
        res = self.client.get(f'/api/v1/payments/supplier-ledger/?supplier={self.supplier.id}')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(len(res.data) >= 1)
