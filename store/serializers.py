from rest_framework import serializers
from .models import Product, Category, SaleReservation
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category; fields = ['id','name','parent']
class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer()
    class Meta:
        model = Product; fields = ['id','local_id','uuid','sku','name','description','buy_price','sell_price','quantity','is_offer','created_at','updated_at','category']
class SaleReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleReservation; fields = ['id','uuid','user','full_name','phone','items','total','status','created_at']
