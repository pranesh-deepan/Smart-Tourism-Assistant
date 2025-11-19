from rest_framework import serializers
from .models import TourismUser, Product,Order

class TourismUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TourismUser
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    vendor_location = serializers.CharField(source="vendor.location", read_only=True)

    image_url_final = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "vendor",
            "vendor_name",
            "vendor_location",
            "name",
            "category",
            "description",
            "price",
            "stock",
            "image",
            "image_url",
            "image_url_final",
        ]

    def get_image_url_final(self, obj):
        if obj.image_url:
            return obj.image_url
        if obj.image:
            return obj.image.url
        return "/media/default-product.jpg"

class OrderSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    vendor_name = serializers.SerializerMethodField()
    quantity = serializers.IntegerField(source='quantity', read_only=True)  # ensure present

    class Meta:
        model = Order
        fields = ['id', 'total_price', 'status', 'created_at', 'product_name', 'product_image', 'vendor_name', 'quantity', 'delivery_address', 'phone']

    def get_product_name(self, obj):
        return obj.product.name if obj.product else ""

    def get_product_image(self, obj):
        if obj.product and obj.product.image_url:
            return obj.product.image_url
        if obj.product and obj.product.image:
            return obj.product.image.url
        return ""

    def get_vendor_name(self, obj):
        return obj.vendor_user.name if obj.vendor_user else (obj.product.vendor.name if obj.product and obj.product.vendor else "")