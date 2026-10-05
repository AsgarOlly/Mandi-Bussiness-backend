from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
import datetime
from apps.accounts.models import Role, UserProfile
from apps.suppliers.models import Supplier
from apps.products.models import Category, Product, ProductVariety
from apps.inventory.models import InventoryLot, InventoryTransaction

class InventoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.super_role, _ = Role.objects.get_or_create(code='SUPER_ADMIN', defaults={'name': 'Super Admin'})
        self.user = User.objects.create_user(username='warehousemgr', password='SecurePassword123!')
        UserProfile.objects.create(user=self.user, role=self.super_role)
        self.client.force_authenticate(user=self.user)

        self.category = Category.objects.create(name='Dry Fruits')
        self.product = Product.objects.create(category=self.category, name='Walnut', product_code='PROD-WLN-01')
        self.variety = ProductVariety.objects.create(product=self.product, variety_name='Kashmiri Giri')
        self.supplier = Supplier.objects.create(supplier_code='SUP-WLN', supplier_name='Himalayan Nuts')

        self.lot = InventoryLot.objects.create(
            lot_number='LOT-WLN-01',
            supplier=self.supplier,
            truck_number='JK03TR1234',
            product=self.product,
            variety=self.variety,
            warehouse_name='Central Cold Hub',
            purchase_date=datetime.date.today(),
            received_boxes=100,
            available_boxes=100,
            received_weight=2000,
            available_weight=2000,
            landed_cost_per_box=Decimal('1200'),
            landed_cost_per_kg=Decimal('60'),
            status='ACTIVE'
        )

    def test_record_wastage_deducts_lot_stock(self):
        payload = {
            'boxes': 5,
            'weight_kg': 100,
            'notes': 'Moisture damage during transport'
        }
        res = self.client.post(f'/api/v1/inventory/lots/{self.lot.id}/record_wastage/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.lot.refresh_from_db()
        self.assertEqual(self.lot.available_boxes, 95)

        tx = InventoryTransaction.objects.filter(lot=self.lot, transaction_type='WASTAGE').first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.quantity_boxes, -5)

    def test_stock_adjustment(self):
        payload = {
            'new_boxes': 98,
            'notes': 'Physical audit discrepancy'
        }
        res = self.client.post(f'/api/v1/inventory/lots/{self.lot.id}/adjust_stock/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.lot.refresh_from_db()
        self.assertEqual(self.lot.available_boxes, 98)

        tx = InventoryTransaction.objects.filter(lot=self.lot, transaction_type='STOCK_ADJUSTMENT').first()
        self.assertIsNotNone(tx)
