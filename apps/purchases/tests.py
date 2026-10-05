from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
import datetime
from apps.accounts.models import Role, UserProfile
from apps.suppliers.models import Supplier
from apps.products.models import Category, Product, ProductVariety
from apps.purchases.models import PurchaseOrder, PurchaseOrderItem
from apps.inventory.models import InventoryLot, InventoryTransaction
from apps.payments.models import SupplierLedger

class PurchaseTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.super_role, _ = Role.objects.get_or_create(code='SUPER_ADMIN', defaults={'name': 'Super Admin'})
        self.user = User.objects.create_user(username='purchaser', password='SecurePassword123!')
        UserProfile.objects.create(user=self.user, role=self.super_role)
        self.client.force_authenticate(user=self.user)

        self.category = Category.objects.create(name='Fresh Fruits')
        self.product = Product.objects.create(category=self.category, name='Apple', product_code='PROD-APP-01')
        self.variety = ProductVariety.objects.create(product=self.product, variety_name='Royal Gala')
        self.supplier = Supplier.objects.create(supplier_code='SUP-001', supplier_name='Kashmir Orchards')

    def test_create_and_receive_purchase(self):
        payload = {
            'supplier': self.supplier.id,
            'warehouse_name': 'Central Cold Hub',
            'truck_number': 'JK01AB1234',
            'purchase_date': str(datetime.date.today()),
            'status': 'DRAFT',
            'items': [
                {
                    'product': self.product.id,
                    'variety': self.variety.id,
                    'quantity_boxes': 100,
                    'purchase_rate': 120,
                }
            ]
        }
        res = self.client.post('/api/v1/purchases/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        po_id = res.data['id']

        # Receive the purchase
        recv_res = self.client.post(f'/api/v1/purchases/{po_id}/receive/')
        self.assertEqual(recv_res.status_code, status.HTTP_200_OK)
        self.assertEqual(recv_res.data['status'], 'RECEIVED')

        # Check Inventory Lot created
        lot = InventoryLot.objects.filter(truck_number='JK01AB1234', product=self.product).first()
        self.assertIsNotNone(lot)
        self.assertEqual(lot.received_boxes, 100)
        self.assertEqual(lot.available_boxes, 100)

        # Check Inventory Transaction created
        tx = InventoryTransaction.objects.filter(lot=lot, transaction_type='PURCHASE_RECEIPT').first()
        self.assertIsNotNone(tx)

        # Check Supplier Ledger created
        ledger = SupplierLedger.objects.filter(supplier=self.supplier, transaction_type='PURCHASE_BILL').first()
        self.assertIsNotNone(ledger)

    def test_duplicate_receive_rejected(self):
        po = PurchaseOrder.objects.create(
            purchase_no='PO-TEST-001',
            supplier=self.supplier,
            purchase_date=datetime.date.today(),
            status='RECEIVED',
            grand_total=Decimal('1000')
        )
        res = self.client.post(f'/api/v1/purchases/{po.id}/receive/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_excel_import_endpoint(self):
        rows = [
            {
                'Supplier': 'Simla Farms',
                'Truck': 'HP01CD9999',
                'Fruit': 'Shimla Apple',
                'Variety': 'Golden',
                'Boxes': 50,
                'PurchaseRate': 95
            }
        ]
        res = self.client.post('/api/v1/purchases/import_excel/', {'rows': rows}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['success'], 1)

        # Check supplier and lot were dynamically created from row data
        sup = Supplier.objects.filter(supplier_name='Simla Farms').first()
        self.assertIsNotNone(sup)
        lot = InventoryLot.objects.filter(truck_number='HP01CD9999').first()
        self.assertIsNotNone(lot)
        self.assertEqual(lot.available_boxes, 50)
