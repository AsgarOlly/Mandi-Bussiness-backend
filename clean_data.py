import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.accounts.models import Role, UserProfile
from apps.products.models import Category, Unit, Product, ProductVariety
from apps.suppliers.models import Supplier
from apps.customers.models import Customer
from apps.purchases.models import PurchaseOrder, PurchaseOrderItem, SupplierTruckPayment
from apps.sales.models import SalesOrder, SalesOrderItem, SalesInvoice
from apps.payments.models import CustomerLedger, SupplierLedger, Payment

print("=== CLEANING / SEEDING BUSINESS DATA ===")

# Delete transactional data if resetting
# SupplierTruckPayment.objects.all().delete()
# SalesInvoice.objects.all().delete()
# SalesOrderItem.objects.all().delete()
# SalesOrder.objects.all().delete()
# PurchaseOrderItem.objects.all().delete()
# PurchaseOrder.objects.all().delete()
# CustomerLedger.objects.all().delete()
# SupplierLedger.objects.all().delete()
# Payment.objects.all().delete()

print("\n=== SETTING UP ROLES & ADMIN USER ===")
roles = [
    ('SUPER_ADMIN', 'Super Admin', 'System Administrator with full access'),
    ('ADMIN', 'Admin', 'Business Administrator'),
    ('PURCHASE_MANAGER', 'Purchase Manager', 'Handles truck arrival and supplier procurement'),
    ('SALES_MANAGER', 'Sales Manager', 'Handles wholesale and customer billing'),
    ('WAREHOUSE_MANAGER', 'Warehouse Manager', 'Manages lot storage and crate movements'),
    ('ACCOUNTANT', 'Accountant', 'Manages mandi ledger and settlements'),
    ('DATA_OPERATOR', 'Data Entry Operator', 'Mandi gate pass and entry operator'),
]

for code, name, desc in roles:
    Role.objects.get_or_create(code=code, defaults={'name': name, 'description': desc})

super_role = Role.objects.get(code='SUPER_ADMIN')

admin_user, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'is_superuser': True,
        'is_staff': True,
        'first_name': 'Aziz',
        'last_name': 'Admin',
        'email': 'admin@fruiterp.com'
    }
)
admin_user.set_password('admin123')
admin_user.is_superuser = True
admin_user.is_staff = True
admin_user.save()

profile, _ = UserProfile.objects.get_or_create(
    user=admin_user,
    defaults={'role': super_role, 'phone': '9876543210', 'employee_code': 'EMP-001'}
)
print("Super Admin user verified: (username: admin / password: admin123)")

print("\n=== SETTING UP MASTER CATEGORIES & UNITS ===")
cat1, _ = Category.objects.get_or_create(name='Fresh Fruits', defaults={'description': 'Fresh seasonal produce and fruits'})
cat2, _ = Category.objects.get_or_create(name='Dry Fruits & Nuts', defaults={'description': 'Premium dry fruits and packaged nuts'})
cat3, _ = Category.objects.get_or_create(name='Citrus & Berries', defaults={'description': 'High vitamin-C citrus and fresh berries'})
cat4, _ = Category.objects.get_or_create(name='Exotic Fruits', defaults={'description': 'Imported and premium exotic fruit varieties'})

u_kg, _ = Unit.objects.get_or_create(unit_name='Kilogram', defaults={'symbol': 'KG', 'unit_type': 'WEIGHT', 'conversion_factor': 1.0})
u_box, _ = Unit.objects.get_or_create(unit_name='Box', defaults={'symbol': 'BX', 'unit_type': 'PACKAGING', 'conversion_factor': 20.0})
u_crate, _ = Unit.objects.get_or_create(unit_name='Crate', defaults={'symbol': 'CR', 'unit_type': 'PACKAGING', 'conversion_factor': 25.0})
u_qtl, _ = Unit.objects.get_or_create(unit_name='Quintal', defaults={'symbol': 'QTL', 'unit_type': 'WEIGHT', 'conversion_factor': 100.0})

print("\n=== SETTING UP MASTER PRODUCTS & VARIETIES ===")
products_data = [
    {
        'category': cat1,
        'name': 'Kashmiri Apple',
        'code': 'PRD-APP-001',
        'unit': u_box,
        'varieties': [
            ('Royal Delicious', 'Grade A', 'India', 'Jammu & Kashmir', 'Medium', 'Deep Red'),
            ('Golden Delicious', 'Grade A', 'India', 'Jammu & Kashmir', 'Large', 'Yellow-Green'),
            ('Kullu Delicious', 'Grade B', 'India', 'Himachal Pradesh', 'Medium', 'Red Striped'),
        ]
    },
    {
        'category': cat1,
        'name': 'Ratnagiri Alphonso Mango',
        'code': 'PRD-MNG-002',
        'unit': u_box,
        'varieties': [
            ('Alphonso (Hapus)', 'Grade A', 'India', 'Maharashtra', 'Large', 'Golden Yellow'),
            ('Kesar', 'Grade A', 'India', 'Gujarat', 'Medium', 'Saffron Yellow'),
        ]
    },
    {
        'category': cat3,
        'name': 'Nagpur Orange',
        'code': 'PRD-ORG-003',
        'unit': u_box,
        'varieties': [
            ('Nagpur Mandarin', 'Grade A', 'India', 'Maharashtra', 'Standard', 'Bright Orange'),
            ('Kinnow', 'Grade B', 'India', 'Punjab', 'Large', 'Deep Orange'),
        ]
    },
    {
        'category': cat1,
        'name': 'Robusta Banana',
        'code': 'PRD-BAN-004',
        'unit': u_crate,
        'varieties': [
            ('Grand Naine (G9)', 'Grade A', 'India', 'Maharashtra', 'Premium 8 Inch', 'Green-Yellow'),
            ('Yelakki (Cardamom)', 'Grade A', 'India', 'Karnataka', 'Small', 'Yellow'),
        ]
    },
    {
        'category': cat1,
        'name': 'Bhagwa Pomegranate',
        'code': 'PRD-POM-005',
        'unit': u_box,
        'varieties': [
            ('Bhagwa Ruby', 'Super Grade', 'India', 'Maharashtra', 'Heavy (>300g)', 'Ruby Red'),
            ('Arakta', 'Grade A', 'India', 'Karnataka', 'Medium', 'Red'),
        ]
    },
    {
        'category': cat1,
        'name': 'Thompson Seedless Grapes',
        'code': 'PRD-GRP-006',
        'unit': u_box,
        'varieties': [
            ('Thompson White Seedless', 'Export Grade', 'India', 'Maharashtra (Nashik)', 'Long Berry', 'Light Green'),
            ('Sharad Black Seedless', 'Grade A', 'India', 'Maharashtra (Sangli)', 'Round Berry', 'Dark Purple'),
        ]
    },
    {
        'category': cat4,
        'name': 'Hayward Kiwi',
        'code': 'PRD-KIW-007',
        'unit': u_box,
        'varieties': [
            ('Hayward Green Kiwi', 'Grade A', 'New Zealand', '', 'Jumbo 30s', 'Brown/Green'),
            ('Zespri SunGold Kiwi', 'Super Grade', 'New Zealand', '', '36 Count', 'Golden Yellow'),
        ]
    },
    {
        'category': cat2,
        'name': 'California Almonds',
        'code': 'PRD-ALM-008',
        'unit': u_kg,
        'varieties': [
            ('Nonpareil Supreme 27/30', 'Grade A', 'USA', 'California', '27/30 Count', 'Golden Brown'),
            ('Mamra Almonds', 'Super Premium', 'Iran', '', 'Natural Medium', 'Light Brown'),
        ]
    }
]

for pdata in products_data:
    p, _ = Product.objects.get_or_create(
        product_code=pdata['code'],
        defaults={
            'name': pdata['name'],
            'category': pdata['category'],
            'default_unit': pdata['unit'],
            'min_stock': 50,
            'max_stock': 5000
        }
    )
    for vname, vgrade, vcountry, vstate, vsize, vcolor in pdata['varieties']:
        ProductVariety.objects.get_or_create(
            product=p,
            variety_name=vname,
            grade=vgrade,
            defaults={
                'origin_country': vcountry or 'India',
                'origin_state': vstate,
                'size': vsize,
                'color': vcolor
            }
        )

print("Products and Varieties seeded successfully!")

print("\n=== SETTING UP MASTER SUPPLIERS ===")
suppliers_data = [
    {
        'supplier_code': 'SUP-001',
        'supplier_name': 'Kashmir Valley Orchard Farms',
        'company_name': 'Kashmir Valley Orchards Ltd.',
        'phone': '9876543211',
        'city': 'Sopore',
        'state': 'Jammu & Kashmir',
        'credit_limit': 1500000,
        'opening_balance': 120000,
        'current_balance': 120000,
    },
    {
        'supplier_code': 'SUP-002',
        'supplier_name': 'Ratnagiri Farmers Federation',
        'company_name': 'Ratnagiri Mango Growers Co.',
        'phone': '9876543212',
        'city': 'Ratnagiri',
        'state': 'Maharashtra',
        'credit_limit': 2000000,
        'opening_balance': 85000,
        'current_balance': 85000,
    },
    {
        'supplier_code': 'SUP-003',
        'supplier_name': 'Nashik Agro Grape Syndicate',
        'company_name': 'Nashik Fresh Export LLP',
        'phone': '9876543213',
        'city': 'Nashik',
        'state': 'Maharashtra',
        'credit_limit': 1800000,
        'opening_balance': 95000,
        'current_balance': 95000,
    },
    {
        'supplier_code': 'SUP-004',
        'supplier_name': 'Nagpur Citrus Producers Union',
        'company_name': 'Nagpur Orange Mandi Hub',
        'phone': '9876543214',
        'city': 'Nagpur',
        'state': 'Maharashtra',
        'credit_limit': 1200000,
        'opening_balance': 40000,
        'current_balance': 40000,
    },
    {
        'supplier_code': 'SUP-005',
        'supplier_name': 'Solapur Bhagwa Growers',
        'company_name': 'Solapur Pomegranate Agro',
        'phone': '9876543215',
        'city': 'Solapur',
        'state': 'Maharashtra',
        'credit_limit': 1000000,
        'opening_balance': 60000,
        'current_balance': 60000,
    }
]

for sdata in suppliers_data:
    Supplier.objects.get_or_create(
        supplier_code=sdata['supplier_code'],
        defaults=sdata
    )

print("Suppliers seeded successfully!")

print("\n=== SETTING UP MASTER CUSTOMERS ===")
customers_data = [
    {
        'customer_code': 'CUST-001',
        'customer_name': 'Azadpur Wholesale Mandi Traders',
        'company_name': 'Azadpur Fruits Co.',
        'phone': '9811223344',
        'customer_type': 'WHOLESALER',
        'credit_limit': 2500000,
        'opening_balance': 185000,
        'current_balance': 185000,
    },
    {
        'customer_code': 'CUST-002',
        'customer_name': 'Delhi Fresh Hypermarket Chain',
        'company_name': 'Delhi Retail Mart Ltd.',
        'phone': '9822334455',
        'customer_type': 'SUPERMARKET',
        'credit_limit': 1500000,
        'opening_balance': 92000,
        'current_balance': 92000,
    },
    {
        'customer_code': 'CUST-003',
        'customer_name': 'Grand Oberoi Luxury Kitchens',
        'company_name': 'Oberoi Hospitality Group',
        'phone': '9833445566',
        'customer_type': 'HOTEL',
        'credit_limit': 800000,
        'opening_balance': 45000,
        'current_balance': 45000,
    },
    {
        'customer_code': 'CUST-004',
        'customer_name': 'FreshBazaar Quick Commerce Hub',
        'company_name': 'FreshBazaar Express Tech Pvt Ltd',
        'phone': '9844556677',
        'customer_type': 'DISTRIBUTOR',
        'credit_limit': 3000000,
        'opening_balance': 240000,
        'current_balance': 240000,
    },
    {
        'customer_code': 'CUST-005',
        'customer_name': 'Chandni Chowk Retail Fruit Mart',
        'company_name': 'Chowk Fresh Fruits',
        'phone': '9855667788',
        'customer_type': 'RETAILER',
        'credit_limit': 500000,
        'opening_balance': 28000,
        'current_balance': 28000,
    }
]

for cdata in customers_data:
    Customer.objects.get_or_create(
        customer_code=cdata['customer_code'],
        defaults=cdata
    )

print("Customers seeded successfully!")

print("\n=== VERIFYING FINAL MASTER COUNTS ===")
from django.apps import apps
for m in apps.get_models():
    if not m._meta.app_label.startswith('django') and m._meta.app_label not in ('auth', 'contenttypes', 'sessions', 'admin'):
        print(f"  {m._meta.label}: {m.objects.count()} records")

print("\n=== SYSTEM SEED & AUDIT COMPLETE ===")
