from django.db import models
from apps.core.models import AuditModel

class Customer(AuditModel):
    CUSTOMER_TYPES = (
        ('RETAILER', 'Retailer'),
        ('WHOLESALER', 'Wholesaler'),
        ('DISTRIBUTOR', 'Distributor'),
        ('HOTEL', 'Hotel / Restaurant'),
        ('SUPERMARKET', 'Supermarket'),
        ('EXPORTER', 'Exporter'),
        ('OTHER', 'Other'),
    )

    customer_code = models.CharField(max_length=50, unique=True)
    customer_name = models.CharField(max_length=150)
    company_name = models.CharField(max_length=150, blank=True, null=True)
    phone = models.CharField(max_length=20)
    alternate_phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    # city = models.CharField(max_length=100, default='Delhi')
    # state = models.CharField(max_length=100, default='Delhi')
    # pincode = models.CharField(max_length=20, blank=True, null=True)
    gst_number = models.CharField(max_length=30, blank=True, null=True)
    pan_number = models.CharField(max_length=30, blank=True, null=True)
    customer_type = models.CharField(max_length=50, choices=CUSTOMER_TYPES, default='WHOLESALER')
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    payment_terms = models.CharField(max_length=50, default='7 Days')
    status = models.CharField(max_length=20, default='ACTIVE')

    def __str__(self):
        return f"{self.customer_name} ({self.customer_code})"
