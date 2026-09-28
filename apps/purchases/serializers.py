from rest_framework import serializers
from .models import PurchaseOrder, PurchaseOrderItem, SupplierTruckPayment

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    variety_name = serializers.CharField(source='variety.variety_name', read_only=True)
    batch_number = serializers.CharField(default='', read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = '__all__'

class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.supplier_name', read_only=True)
    warehouse_name = serializers.CharField(required=False, default='Central Cold Hub')
    truck_number = serializers.CharField(required=False, allow_blank=True, default='-')
    items = PurchaseOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = '__all__'

class SupplierTruckPaymentSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.supplier_name', read_only=True)

    class Meta:
        model = SupplierTruckPayment
        fields = '__all__'
