import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.accounts.models import Role, UserProfile
from apps.products.models import Category, Unit, Product, ProductVariety
from apps.suppliers.models import Supplier
from apps.customers.models import Customer
from apps.transport.models import Truck
from apps.warehouse.models import Warehouse
from apps.purchases.models import PurchaseOrder, PurchaseOrderItem, SupplierTruckPayment
from apps.sales.models import SalesOrder, SalesOrderItem, SalesInvoice
from apps.inventory.models import InventoryBatch, InventoryStock
from apps.payments.models import CustomerLedger, SupplierLedger, Payment

print("=== CLEANING BUSINESS DATA ===")

# Delete transactional and operational data
SupplierTruckPayment.objects.all().delete()
print("Cleared SupplierTruckPayment")

SalesInvoice.objects.all().delete()
SalesOrderItem.objects.all().delete()
SalesOrder.objects.all().delete()
print("Cleared SalesOrder, Items, Invoices")

PurchaseOrderItem.objects.all().delete()
PurchaseOrder.objects.all().delete()
print("Cleared PurchaseOrder and Items")

CustomerLedger.objects.all().delete()
SupplierLedger.objects.all().delete()
Payment.objects.all().delete()
print("Cleared Payments and Ledgers")

InventoryStock.objects.all().delete()
InventoryBatch.objects.all().delete()
print("Cleared Inventory Batches and Stock")

Truck.objects.all().delete()
print("Cleared Trucks")

ProductVariety.objects.all().delete()
Product.objects.all().delete()
print("Cleared Products and Varieties")

Customer.objects.all().delete()
print("Cleared Customers")

Supplier.objects.all().delete()
print("Cleared Suppliers")

Warehouse.objects.all().delete()
print("Cleared Warehouses")

print("\n=== SETTING UP CLEAN MASTER ESSENTIALS ===")
# Ensure master categories & units exist so new entries have valid foreign keys
cat1, _ = Category.objects.get_or_create(id=1, defaults={'name': 'Fresh Fruits'})
cat2, _ = Category.objects.get_or_create(id=2, defaults={'name': 'Dry Fruits & Nuts'})
print(f"Categories ready: {cat1.name}, {cat2.name}")

u1, _ = Unit.objects.get_or_create(id=1, defaults={'unit_name': 'Kilogram', 'symbol': 'KG'})
u2, _ = Unit.objects.get_or_create(id=2, defaults={'unit_name': 'Box', 'symbol': 'BX'})
print(f"Units ready: {u1.unit_name}, {u2.unit_name}")

wh, _ = Warehouse.objects.get_or_create(id=1, defaults={'warehouse_code': 'WH-001', 'warehouse_name': 'Main Mandi Storage', 'city': 'Delhi'})
print(f"Default Warehouse ready: {wh.warehouse_name}")

# Ensure admin user is active with password 'admin123'
admin_user, created = User.objects.get_or_create(username='admin', defaults={'is_superuser': True, 'is_staff': True, 'first_name': 'Aziz', 'last_name': 'Admin'})
admin_user.set_password('admin123')
admin_user.is_superuser = True
admin_user.is_staff = True
admin_user.save()

super_role, _ = Role.objects.get_or_create(name='Super Admin', defaults={'description': 'System Administrator'})
UserProfile.objects.get_or_create(user=admin_user, defaults={'role': super_role, 'phone': '9876543210'})
print("Admin user ready with credentials (admin / admin123)")

print("\n=== VERIFYING FINAL COUNTS ===")
from django.apps import apps
for m in apps.get_models():
    if not m._meta.app_label.startswith('django') and m._meta.app_label not in ('auth', 'contenttypes', 'sessions', 'admin'):
        print(f"{m._meta.label}: {m.objects.count()}")
