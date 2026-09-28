from rest_framework import serializers
from .models import Customer

class CustomerSerializer(serializers.ModelSerializer):
    customer_code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Customer
        fields = '__all__'

    def create(self, validated_data):
        if not validated_data.get('customer_code'):
            count = Customer.objects.count() + 1
            code = f"CUST-{count:04d}"
            while Customer.objects.filter(customer_code=code).exists():
                count += 1
                code = f"CUST-{count:04d}"
            validated_data['customer_code'] = code
        return super().create(validated_data)

