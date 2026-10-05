from rest_framework import serializers
from .models import InventoryLot, InventoryTransaction
from apps.products.serializers import ProductSerializer, ProductVarietySerializer
from apps.suppliers.serializers import SupplierSerializer

class InventoryLotSerializer(serializers.ModelSerializer):
    supplier_details = SupplierSerializer(source='supplier', read_only=True)
    product_details = ProductSerializer(source='product', read_only=True)
    variety_details = ProductVarietySerializer(source='variety', read_only=True)

    class Meta:
        model = InventoryLot
        fields = '__all__'


class InventoryTransactionSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    variety_name = serializers.ReadOnlyField(source='variety.variety_name')

    class Meta:
        model = InventoryTransaction
        fields = '__all__'
