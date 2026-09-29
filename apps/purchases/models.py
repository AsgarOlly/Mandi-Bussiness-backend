from django.db import models
from apps.core.models import AuditModel
from apps.suppliers.models import Supplier
from apps.products.models import Product, ProductVariety

class PurchaseOrder(AuditModel):
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('ORDERED', 'Ordered'),
        ('TRUCK_ARRIVED', 'Truck Arrived'),
        ('RECEIVING', 'Receiving Goods'),
        ('QUALITY_CHECK', 'Quality Check'),
        ('RECEIVED', 'Goods Received'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )

    purchase_no = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchases')
    warehouse_name = models.CharField(max_length=100, default='Central Cold Hub', blank=True)
    truck_number = models.CharField(max_length=50, blank=True, default='')
    purchase_date = models.DateField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='DRAFT')

    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    transport_charge = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    loading_charge = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unloading_charge = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    commission_charge = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    due_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)

    def calculate_totals(self):
        items = self.items.all()
        sub = sum(item.line_total for item in items)
        self.subtotal = sub
        taxes = sum(item.tax_amount for item in items)
        self.tax_amount = taxes
        total_charges = self.transport_charge + self.loading_charge + self.unloading_charge + self.commission_charge
        self.grand_total = max(0, sub - self.discount + total_charges + taxes)
        self.due_amount = max(0, self.grand_total - self.paid_amount)
        self.save()

    def __str__(self):
        return f"{self.purchase_no} - {self.supplier.supplier_name}"

class PurchaseOrderItem(AuditModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variety = models.ForeignKey(ProductVariety, on_delete=models.CASCADE)

    quantity_boxes = models.IntegerField(default=0)
    gross_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tare_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    purchase_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0) # Rate per KG
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0) # %
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    landed_cost_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    quality_grade = models.CharField(max_length=50, default='Grade A')
    damage_boxes = models.IntegerField(default=0)
    accepted_boxes = models.IntegerField(default=0)
    damage_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    accepted_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if self.net_weight == 0 and self.gross_weight > self.tare_weight:
            self.net_weight = self.gross_weight - self.tare_weight
        if self.accepted_boxes == 0 and self.quantity_boxes > 0 and self.damage_boxes == 0:
            self.accepted_boxes = self.quantity_boxes
        if self.accepted_weight == 0 and self.net_weight > 0 and self.damage_weight == 0:
            self.accepted_weight = self.net_weight

        base_cost = (self.net_weight * self.purchase_rate) - self.discount
        self.tax_amount = (base_cost * (self.tax_rate / 100)) if self.tax_rate > 0 else 0
        self.line_total = base_cost + self.tax_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.purchase_order.purchase_no} - {self.product.name} ({self.quantity_boxes} boxes)"

class SupplierTruckPayment(AuditModel):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='truck_payments')
    truck_number = models.CharField(max_length=50)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='truck_payments')
    payment_date = models.DateField()
    fruit_name = models.CharField(max_length=100)
    variety = models.CharField(max_length=100, blank=True, default='')
    no_of_boxes = models.IntegerField(default=0)
    pay = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    rate_per_box = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    transport_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0) # TF
    loading_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0) # Kuli
    unloading_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    landed_cost_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    landed_cost_per_box = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=50, default='BANK_TRANSFER')
    transaction_ref = models.CharField(max_length=100, blank=True, default='')
    notes = models.TextField(blank=True, default='')

    def save(self, *args, **kwargs):
        from decimal import Decimal
        total_charges = (
            self.transport_charge +
            self.loading_charge +
            self.unloading_charge +
            self.commission_charge -
            self.discount
        )
        produce_cost = self.pay if self.pay > 0 else (Decimal(str(self.no_of_boxes)) * self.rate_per_box)
        self.landed_cost_total = max(Decimal('0'), produce_cost + total_charges)
        if self.no_of_boxes > 0:
            self.landed_cost_per_box = round(self.landed_cost_total / Decimal(str(self.no_of_boxes)), 2)
        else:
            self.landed_cost_per_box = Decimal('0')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.supplier.supplier_name} - Truck {self.truck_number} - {self.fruit_name} (₹{self.pay})"
