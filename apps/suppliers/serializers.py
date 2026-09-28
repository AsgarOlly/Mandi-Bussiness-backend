from rest_framework import serializers
from .models import Supplier

class SupplierSerializer(serializers.ModelSerializer):
    supplier_code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Supplier
        fields = '__all__'

    def create(self, validated_data):
        if not validated_data.get('supplier_code'):
            count = Supplier.objects.count() + 1
            code = f"SUP-{count:04d}"
            while Supplier.objects.filter(supplier_code=code).exists():
                count += 1
                code = f"SUP-{count:04d}"
            validated_data['supplier_code'] = code
        return super().create(validated_data)

