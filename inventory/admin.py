from django.contrib import admin
from .models import Category, Product, Variant, StockTransaction

admin.site.register(Category)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)

@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'sku', 'size', 'color', 'price', 'stock')
    list_filter = ('product__category', 'size', 'color')

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('variant', 'transaction_type', 'quantity', 'timestamp', 'note')
    list_filter = ('transaction_type',)
    date_hierarchy = 'timestamp'
