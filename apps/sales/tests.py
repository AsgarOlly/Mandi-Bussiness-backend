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
from apps.inventory.models import InventoryLot, InventoryTransaction
from apps.sales.models import SalesOrder, SalesOrderItem
from apps.payments.models import CustomerLedger

class SalesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.super_role, _ = Role.objects.get_or_create(code='SUPER_ADMIN', defaults={'name': 'Super Admin'})
        self.user = User.objects.create_user(username='salesman', password='SecurePassword123!')
        UserProfile.objects.create(user=self.user, role=self.super_role)
        self.client.force_authenticate(user=self.user)

        self.category = Category.objects.create(name='Fresh Fruits')
        self.product = Product.objects.create(category=self.category, name='Mango', product_code='PROD-MNG-01')
        self.variety = ProductVariety.objects.create(product=self.product, variety_name='Dasheri')
        self.supplier = Supplier.objects.create(supplier_code='SUP-001', supplier_name='UP Orchards')
        self.customer = Customer.objects.create(customer_code='CUST-001', customer_name='City Retailers')

        # Create active inventory lot with 50 boxes
        self.lot = InventoryLot.objects.create(
            lot_number='LOT-MNG-01',
            supplier=self.supplier,
            truck_number='UP32AB0001',
            product=self.product,
            variety=self.variety,
            warehouse_name='Central Cold Hub',
            purchase_date=datetime.date.today(),
            received_boxes=50,
            available_boxes=50,
            received_weight=1000,
            available_weight=1000,
            landed_cost_per_box=Decimal('500'),
            status='ACTIVE'
        )

    def test_create_and_dispatch_sale_consumes_inventory(self):
        payload = {
            'customer': self.customer.id,
            'order_date': str(datetime.date.today()),
            'status': 'DRAFT',
            'items': [
                {
                    'product': self.product.id,
                    'variety': self.variety.id,
                    'quantity_boxes': 20,
                    'selling_rate': 750,
                }
            ]
        }
        res = self.client.post('/api/v1/sales/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        so_id = res.data['id']

        # Dispatch sale
        dispatch_res = self.client.post(f'/api/v1/sales/{so_id}/dispatch/')
        self.assertEqual(dispatch_res.status_code, status.HTTP_200_OK)

        # Check lot available boxes reduced by 20 (50 - 20 = 30)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.available_boxes, 30)

        # Check Customer Ledger updated
        ledger = CustomerLedger.objects.filter(customer=self.customer, transaction_type='SALES_INVOICE').first()
        self.assertIsNotNone(ledger)

    def test_cancel_sale_restores_inventory(self):
        so = SalesOrder.objects.create(
            sales_order_no='SO-TEST-CANCEL',
            customer=self.customer,
            order_date=datetime.date.today(),
            status='DRAFT',
            grand_total=Decimal('10000')
        )
        item = SalesOrderItem.objects.create(
            sales_order=so,
            product=self.product,
            variety=self.variety,
            quantity_boxes=10,
            selling_rate=Decimal('1000'),
            line_total=Decimal('10000')
        )
        # Dispatch
        self.client.post(f'/api/v1/sales/{so.id}/dispatch/')
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.available_boxes, 40)

        # Cancel
        cancel_res = self.client.post(f'/api/v1/sales/{so.id}/cancel/')
        self.assertEqual(cancel_res.status_code, status.HTTP_200_OK)

        # Stock must be restored back to 50
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.available_boxes, 50)
