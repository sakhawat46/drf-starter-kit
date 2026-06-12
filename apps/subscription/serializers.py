from rest_framework import serializers
from .models import SubscriptionPackage, Features, Subscription

# Subscription Package Features
class FeaturesSerializer(serializers.ModelSerializer):

    class Meta:
        model = Features
        fields = [
            'order',
            'text', 
            'include',
            ]

# Subscription Package
class SubscriptionPackageSerializer(serializers.ModelSerializer): 
    features = FeaturesSerializer(many=True, read_only=True)

    class Meta:
        model = SubscriptionPackage
        fields = [
            'id', 
            'billing_cycle',
            'price',
            'stripe_price_id',
            'stripe_product_id',
            'is_active', 
            'features',
            ]

# Subscription Plan
class SubscriptionPlanSerializer(serializers.ModelSerializer):

    class Meta:
        model = SubscriptionPackage
        fields = [
            'id', 
            'billing_cycle',
            'price',
            'is_active',
            ]

# Current Subscription Plan
class CurrentPlanSerializer(serializers.ModelSerializer):
    subscriptionpackage = SubscriptionPlanSerializer()

    class Meta:
        model = Subscription
        fields = [
            'id',
            'subscriptionpackage',
            'status',
            'start_date',
            'end_date',
            ]
