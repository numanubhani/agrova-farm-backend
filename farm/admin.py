from django.contrib import admin

from .models import Customer, Delivery, Expense, Farm, Payment, Production


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'rate', 'qty', 'active']
    list_filter = ['active']
    search_fields = ['name', 'phone']


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ['customer', 'date', 'liters']
    list_filter = ['date']
    autocomplete_fields = ['customer']


@admin.register(Production)
class ProductionAdmin(admin.ModelAdmin):
    list_display = ['date', 'am', 'pm']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['date', 'category', 'amount', 'note']
    list_filter = ['category']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['customer', 'date', 'amount', 'note']
    autocomplete_fields = ['customer']
