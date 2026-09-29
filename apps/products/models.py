from django.db import models
from apps.core.models import AuditModel

class Category(AuditModel):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

class Unit(AuditModel):
    unit_name = models.CharField(max_length=50, unique=True)
    symbol = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.unit_name} ({self.symbol})"

class Product(AuditModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=150)
    product_code = models.CharField(max_length=50, unique=True)
    default_unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.name} [{self.product_code}]"

class ProductVariety(AuditModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='varieties')
    variety_name = models.CharField(max_length=100)
    grade = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Product Varieties'
        unique_together = ('product', 'variety_name', 'grade')

    def __str__(self):
        return f"{self.product.name} - {self.variety_name} ({self.grade or 'Standard'})"
