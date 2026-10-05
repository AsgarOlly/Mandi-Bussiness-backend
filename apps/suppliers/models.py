from django.db import models
from apps.core.models import AuditModel

class Supplier(AuditModel):
    supplier_code = models.CharField(max_length=50, unique=True)
    supplier_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True, default='')
    bank_name = models.CharField(max_length=100, blank=True, default='')
    account_number = models.CharField(max_length=50, blank=True, default='')
    ifsc_code = models.CharField(max_length=30, blank=True, default='')
    branch_name = models.CharField(max_length=100, blank=True, default='')
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default='ACTIVE')

    def __str__(self):
        return f"{self.supplier_name} ({self.supplier_code})"
