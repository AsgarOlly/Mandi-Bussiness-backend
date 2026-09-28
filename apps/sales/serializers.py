from rest_framework import serializers
from .models import SalesOrder, SalesOrderItem, SalesInvoice

class SalesOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    variety_name = serializers.CharField(source='variety.variety_name', read_only=True)
    batch_number = serializers.CharField(source='lot_reference', default='', read_only=True)

    class Meta:
        model = SalesOrderItem
        fields = '__all__'

class SalesInvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.customer_name', read_only=True)

    class Meta:
        model = SalesInvoice
        fields = '__all__'

class SalesOrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.customer_name', read_only=True)
    warehouse_name = serializers.CharField(required=False, default='Central Cold Hub')
    truck_number = serializers.CharField(required=False, allow_blank=True, default='-')
    items = SalesOrderItemSerializer(many=True, read_only=True)
    invoice = SalesInvoiceSerializer(read_only=True)

    class Meta:
        model = SalesOrder
        fields = '__all__'
