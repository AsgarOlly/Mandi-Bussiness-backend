from rest_framework import serializers
from .models import PurchaseOrder, PurchaseOrderItem, SupplierTruckPayment
from decimal import Decimal

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    variety_name = serializers.CharField(source='variety.variety_name', read_only=True)
    batch_number = serializers.CharField(default='', read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = '__all__'

    def validate(self, data):
        qty = data.get('quantity_boxes', 0)
        if qty < 0:
            raise serializers.ValidationError({'quantity_boxes': 'Quantity boxes cannot be negative.'})

        rate = data.get('purchase_rate', Decimal('0'))
        if rate < 0:
            raise serializers.ValidationError({'purchase_rate': 'Purchase rate cannot be negative.'})

        dmg = data.get('damage_boxes', 0)
        if dmg > qty:
            raise serializers.ValidationError({'damage_boxes': 'Damage boxes cannot exceed total boxes.'})

        acc = data.get('accepted_boxes', qty)
        if acc > qty:
            raise serializers.ValidationError({'accepted_boxes': 'Accepted boxes cannot exceed total boxes.'})

        return data


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

    def validate(self, data):
        boxes = data.get('no_of_boxes', 0)
        if boxes < 0:
            raise serializers.ValidationError({'no_of_boxes': 'Boxes cannot be negative.'})
        pay = data.get('pay', Decimal('0'))
        if pay < 0:
            raise serializers.ValidationError({'pay': 'Payment cannot be negative.'})
        return data
