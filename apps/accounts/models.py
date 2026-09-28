from django.db import models
from django.contrib.auth.models import User
from apps.core.models import AuditModel

class Role(models.Model):
    ROLES = (
        ('SUPER_ADMIN', 'Super Admin'),
        ('ADMIN', 'Admin'),
        ('PURCHASE_MANAGER', 'Purchase Manager'),
        ('SALES_MANAGER', 'Sales Manager'),
        ('WAREHOUSE_MANAGER', 'Warehouse Manager'),
        ('ACCOUNTANT', 'Accountant'),
        ('DATA_OPERATOR', 'Data Entry Operator'),
    )
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=50, choices=ROLES, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class UserProfile(AuditModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    employee_code = models.CharField(max_length=30, blank=True, null=True)
    status = models.CharField(max_length=20, default='ACTIVE')

    def __str__(self):
        return f"{self.user.username} ({self.role.name if self.role else 'No Role'})"

