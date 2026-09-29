from django.db import models
from apps.core.models import AuditModel

class Customer(AuditModel):
    customer_code = models.CharField(max_length=50, unique=True)
    customer_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True, default='')
    address = models.TextField(blank=True, default='')
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default='ACTIVE')

    def __str__(self):
        return f"{self.customer_name} ({self.customer_code})"
