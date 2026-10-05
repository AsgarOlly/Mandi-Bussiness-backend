from django.db import models
from apps.core.models import AuditModel
from apps.customers.models import Customer
from apps.products.models import Product, ProductVariety
from decimal import Decimal

class SalesOrder(AuditModel):
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('CONFIRMED', 'Confirmed'),
        ('PACKED', 'Packed'),
        ('DISPATCHED', 'Dispatched'),
        ('DELIVERED', 'Delivered'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )

    PAYMENT_TERMS = (
        ('CASH', 'Cash'),
        ('UPI', 'UPI Payment'),
        ('BANK_TRANSFER', 'Bank Transfer / NEFT'),
        ('CREDIT', 'Credit (7-14 Days)'),
        ('CHEQUE', 'Cheque'),
    )

    sales_order_no = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sales_orders')
    truck_number = models.CharField(max_length=50, blank=True, default='')
    order_date = models.DateField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='DRAFT')
    payment_terms = models.CharField(max_length=30, choices=PAYMENT_TERMS, default='CREDIT')

    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    transport_charge = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    loading_charge = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    due_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def calculate_totals(self):
        items = self.items.all()
        sub = sum(item.line_total for item in items)
        self.subtotal = sub
        charges = self.transport_charge + self.loading_charge
        self.grand_total = max(Decimal('0'), sub + charges)
        self.due_amount = max(Decimal('0'), self.grand_total - self.paid_amount)
        self.save()

    def __str__(self):
        return f"{self.sales_order_no} - {self.customer.customer_name}"

class SalesOrderItem(AuditModel):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variety = models.ForeignKey(ProductVariety, on_delete=models.CASCADE)

    quantity_boxes = models.IntegerField(default=0)
    selling_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.line_total = Decimal(str(self.quantity_boxes)) * self.selling_rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sales_order.sales_order_no} - {self.product.name} ({self.quantity_boxes} boxes)"
