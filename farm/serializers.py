from rest_framework import serializers

from .models import Customer, Delivery, Expense, Farm, Payment, Production


class FarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = ['id', 'name']


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'phone', 'rate', 'qty', 'active']

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError('Name is required.')
        return value.strip()

    def validate_rate(self, value):
        if value <= 0:
            raise serializers.ValidationError('Rate must be greater than 0.')
        return value


class DeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = ['id', 'customer', 'date', 'liters']


class ProductionSerializer(serializers.ModelSerializer):
    total = serializers.SerializerMethodField()

    class Meta:
        model = Production
        fields = ['id', 'date', 'am', 'pm', 'total']

    def get_total(self, obj):
        return obj.am + obj.pm


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['id', 'date', 'category', 'amount', 'note']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than 0.')
        return value


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'customer', 'date', 'amount', 'note']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than 0.')
        return value
