from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
import datetime
from apps.accounts.models import Role, UserProfile
from apps.customers.models import Customer
from apps.suppliers.models import Supplier
from apps.products.models import Category, Product, ProductVariety
from apps.purchases.models import PurchaseOrder, PurchaseOrderItem
from apps.sales.models import SalesOrder, SalesOrderItem
from apps.inventory.models import InventoryLot

class ReportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.super_role, _ = Role.objects.get_or_create(code='SUPER_ADMIN', defaults={'name': 'Super Admin'})
        self.user = User.objects.create_user(username='director', password='SecurePassword123!')
        UserProfile.objects.create(user=self.user, role=self.super_role)
        self.client.force_authenticate(user=self.user)

        self.category = Category.objects.create(name='Fresh Fruits')
        self.product = Product.objects.create(category=self.category, name='Banana', product_code='PROD-BAN-01')
        self.variety = ProductVariety.objects.create(product=self.product, variety_name='Robusta')
        self.supplier = Supplier.objects.create(supplier_code='SUP-BAN', supplier_name='South Farms', current_balance=Decimal('25000'))
        self.customer = Customer.objects.create(customer_code='CUST-BAN', customer_name='Mandi Buyer', current_balance=Decimal('15000'))

        self.lot = InventoryLot.objects.create(
            lot_number='LOT-BAN-01',
            supplier=self.supplier,
            truck_number='KA01MN1234',
            product=self.product,
            variety=self.variety,
            warehouse_name='Central Cold Hub',
            purchase_date=datetime.date.today(),
            received_boxes=200,
            available_boxes=150,
            received_weight=4000,
            available_weight=3000,
            landed_cost_per_box=Decimal('300'),
            status='ACTIVE'
        )

    def test_dashboard_summary_report(self):
        res = self.client.get('/api/v1/reports/dashboard/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('stock_value', res.data)
        self.assertIn('total_stock_boxes', res.data)
        self.assertEqual(res.data['total_stock_boxes'], 150)
        self.assertEqual(res.data['customer_outstanding'], 15000.0)
        self.assertEqual(res.data['supplier_outstanding'], 25000.0)

    def test_profit_loss_report(self):
        res = self.client.get('/api/v1/reports/profit-loss/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('revenue', res.data)
        self.assertIn('cogs', res.data)
        self.assertIn('gross_profit', res.data)
        self.assertIn('net_profit', res.data)
