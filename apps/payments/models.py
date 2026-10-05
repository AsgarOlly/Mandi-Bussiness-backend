from django.db import models
from apps.core.models import AuditModel
from apps.customers.models import Customer
from apps.suppliers.models import Supplier

class CustomerLedger(AuditModel):
    TRANSACTION_TYPES = (
        ('SALES_INVOICE', 'Sales Invoice'),
        ('PAYMENT_RECEIVED', 'Payment Received'),
        ('SALES_RETURN', 'Sales Return Credit'),
        ('OPENING_BALANCE', 'Opening Balance'),
        ('ADJUSTMENT', 'Ledger Adjustment'),
    )

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='ledger_entries')
    transaction_date = models.DateField()
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    reference_type = models.CharField(max_length=50, blank=True, null=True)
    reference_id = models.CharField(max_length=50, blank=True, null=True)
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0) # Increases customer receivable
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0) # Decreases customer receivable
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['transaction_date', 'id']

    def __str__(self):
        return f"{self.customer.customer_name} - {self.transaction_type}: ₹{self.debit or self.credit}"

class SupplierLedger(AuditModel):
    TRANSACTION_TYPES = (
        ('PURCHASE_BILL', 'Purchase Bill'),
        ('PAYMENT_MADE', 'Payment Made'),
        ('PURCHASE_RETURN', 'Purchase Return Debit'),
        ('OPENING_BALANCE', 'Opening Balance'),
        ('ADJUSTMENT', 'Ledger Adjustment'),
    )

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='ledger_entries')
    transaction_date = models.DateField()
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    reference_type = models.CharField(max_length=50, blank=True, null=True)
    reference_id = models.CharField(max_length=50, blank=True, null=True)
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0) # Decreases supplier payable
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0) # Increases supplier payable
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['transaction_date', 'id']

    def __str__(self):
        return f"{self.supplier.supplier_name} - {self.transaction_type}: ₹{self.debit or self.credit}"
