from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from apps.core.models import AuditModel
from apps.suppliers.models import Supplier
from apps.products.models import Product, ProductVariety

class InventoryLot(AuditModel):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('DEPLETED', 'Depleted'),
        ('ON_HOLD', 'On Hold'),
    )

    lot_number = models.CharField(max_length=60, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='inventory_lots')
    truck_number = models.CharField(max_length=50, blank=True, default='')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_lots')
    variety = models.ForeignKey(ProductVariety, on_delete=models.CASCADE, related_name='inventory_lots')
    warehouse_name = models.CharField(max_length=100, default='Central Cold Hub')
    purchase_order_item = models.ForeignKey(
        'purchases.PurchaseOrderItem',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='inventory_lots'
    )
    purchase_date = models.DateField()

    received_boxes = models.IntegerField(default=0)
    available_boxes = models.IntegerField(default=0)
    received_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    available_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    landed_cost_per_box = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    landed_cost_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')

    class Meta:
        ordering = ['-purchase_date', '-id']

    def __str__(self):
        return f"Lot {self.lot_number} - {self.product.name} ({self.available_boxes}/{self.received_boxes} BX)"

    def update_status(self):
        if self.available_boxes <= 0 and self.available_weight <= 0:
            self.status = 'DEPLETED'
        elif self.status == 'DEPLETED' and (self.available_boxes > 0 or self.available_weight > 0):
            self.status = 'ACTIVE'
        self.save()


class InventoryTransaction(AuditModel):
    TRANSACTION_TYPES = (
        ('PURCHASE_RECEIPT', 'Purchase Receipt'),
        ('SALES_ISSUE', 'Sales Issue'),
        ('SALES_RETURN', 'Sales Return'),
        ('PURCHASE_RETURN', 'Purchase Return'),
        ('WASTAGE', 'Wastage / Damage'),
        ('STOCK_ADJUSTMENT', 'Stock Adjustment'),
        ('WAREHOUSE_TRANSFER', 'Warehouse Transfer'),
    )

    date_time = models.DateTimeField(default=timezone.now)
    lot = models.ForeignKey(
        InventoryLot,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_transactions')
    variety = models.ForeignKey(ProductVariety, on_delete=models.CASCADE, related_name='inventory_transactions')
    warehouse_name = models.CharField(max_length=100, default='Central Cold Hub')
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    reference_type = models.CharField(max_length=50, blank=True, default='')
    reference_id = models.CharField(max_length=60, blank=True, default='')

    quantity_boxes = models.IntegerField(default=0)
    weight_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-date_time', '-id']

    def __str__(self):
        return f"{self.transaction_type}: {self.product.name} ({self.quantity_boxes} BX) Ref: {self.reference_id}"
