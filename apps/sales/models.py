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
    warehouse_name = models.CharField(max_length=100, default='Central Cold Hub', blank=True)
    truck_number = models.CharField(max_length=50, blank=True, default='')
    order_date = models.DateField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='DRAFT')
    payment_terms = models.CharField(max_length=30, choices=PAYMENT_TERMS, default='CREDIT')

    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    transport_charge = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    loading_charge = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    due_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_margin = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)

    def calculate_totals(self):
        items = self.items.all()
        sub = sum(item.line_total for item in items)
        self.subtotal = sub
        taxes = sum(item.tax_amount for item in items)
        self.tax_amount = taxes
        margin = sum(item.gross_margin for item in items)
        self.total_margin = margin
        charges = self.transport_charge + self.loading_charge
        self.grand_total = max(0, sub - self.discount + charges + taxes)
        self.due_amount = max(0, self.grand_total - self.paid_amount)
        self.save()

    def __str__(self):
        return f"{self.sales_order_no} - {self.customer.customer_name}"

class SalesOrderItem(AuditModel):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variety = models.ForeignKey(ProductVariety, on_delete=models.CASCADE)
    lot_reference = models.CharField(max_length=100, blank=True, default='')

    quantity_boxes = models.IntegerField(default=0)
    gross_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tare_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gross_margin = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    quality_grade = models.CharField(max_length=50, default='Grade A')

    def save(self, *args, **kwargs):
        if self.net_weight == 0 and self.gross_weight > self.tare_weight:
            self.net_weight = self.gross_weight - self.tare_weight

        # Support box-based selling rate (₹/box) when net_weight is 0 or boxes used
        if self.quantity_boxes > 0 and self.net_weight == 0:
            units = Decimal(str(self.quantity_boxes))
        else:
            units = self.net_weight if self.net_weight > 0 else Decimal(str(self.quantity_boxes))

        base_amount = (units * self.selling_rate) - self.discount
        self.tax_amount = (base_amount * (self.tax_rate / 100)) if self.tax_rate > 0 else 0
        self.line_total = base_amount + self.tax_amount
        self.gross_margin = (self.selling_rate - self.cost_rate) * units - self.discount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sales_order.sales_order_no} - {self.product.name} ({self.quantity_boxes} boxes)"

class SalesInvoice(AuditModel):
    STATUS_CHOICES = (
        ('UNPAID', 'Unpaid'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('PAID', 'Paid In Full'),
        ('CANCELLED', 'Cancelled'),
    )

    invoice_no = models.CharField(max_length=50, unique=True)
    sales_order = models.OneToOneField(SalesOrder, on_delete=models.CASCADE, related_name='invoice')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices')
    invoice_date = models.DateField()
    due_date = models.DateField()
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    transport_charge = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    other_charge = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    due_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNPAID')

    def __str__(self):
        return f"{self.invoice_no} [{self.customer.customer_name}] - ₹{self.grand_total}"
