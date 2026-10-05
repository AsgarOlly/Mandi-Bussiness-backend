from rest_framework import serializers
from .models import SalesOrder, SalesOrderItem
from decimal import Decimal

class SalesOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    variety_name = serializers.CharField(source='variety.variety_name', read_only=True)

    class Meta:
        model = SalesOrderItem
        fields = '__all__'

    def validate(self, data):
        qty = data.get('quantity_boxes', 0)
        if qty < 0:
            raise serializers.ValidationError({'quantity_boxes': 'Quantity boxes cannot be negative.'})

        rate = data.get('selling_rate', Decimal('0'))
        if rate < 0:
            raise serializers.ValidationError({'selling_rate': 'Selling rate cannot be negative.'})

        return data

class SalesOrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.customer_name', read_only=True)
    truck_number = serializers.CharField(required=False, allow_blank=True, default='-')
    items = SalesOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = SalesOrder
        fields = '__all__'
