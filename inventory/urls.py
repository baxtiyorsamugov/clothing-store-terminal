from django.urls import path
from .views import (
    DashboardView,
    CategoryListView, CategoryCreateView,
    ProductListView, VariantListView, ProductCreateView,
    VariantCreateView,
    StockInView, SaleView,
    TransactionListView,
    variant_api,   
)

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),

    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/add/', CategoryCreateView.as_view(), name='category-add'),

    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/add/', ProductCreateView.as_view(), name='product-add'),

    path('variants/', VariantListView.as_view(), name='variant-list'),
    path('variants/add/', VariantCreateView.as_view(), name='variant-add'),

    path('stock/in/', StockInView.as_view(), name='stockin'),
    path('stock/sale/', SaleView.as_view(), name='sale'),

    path('transactions/', TransactionListView.as_view(), name='transaction-list'),

    path('api/variant/<str:sku>/', variant_api, name='variant-api'),
]
