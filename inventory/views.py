from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, TemplateView, ListView
)

from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse_lazy
from django.db.models import Q
from .models import Category, Product, Variant, StockTransaction
from .forms import (
    CategoryForm, ProductForm, VariantForm,
    StockInForm, SaleForm
)
from django.shortcuts import get_object_or_404
from django.http import JsonResponse

class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('variant-list')  # после создания перенаправим на список вариантов

class VariantListView(ListView):
    model = Variant
    template_name = 'inventory/variant_list.html'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('product')
        cat = self.request.GET.get('category')
        if cat:
            qs = qs.filter(product__category_id=cat)
        sort = self.request.GET.get('sort')
        if sort in ['price','-price','stock','-stock']:
            qs = qs.order_by(sort)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Список корневых категорий
        ctx['root_categories'] = Category.objects.filter(parent__isnull=True)
        # Чтобы форма «сохранила» выбранные фильтры
        ctx['selected_category'] = self.request.GET.get('category', '')
        ctx['selected_sort']     = self.request.GET.get('sort', '')
        return ctx

class DashboardView(TemplateView):
    template_name = 'inventory/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # общее число товарных вариантов
        ctx['total_variants'] = Variant.objects.count()
        # суммарный остаток по всем вариантам
        agg = Variant.objects.aggregate(total_stock=Sum('stock'))
        ctx['total_stock'] = agg['total_stock'] or 0
        # общее число транзакций
        ctx['total_transactions'] = StockTransaction.objects.count()
        return ctx

class CategoryListView(ListView):
    model = Category
    template_name = 'inventory/category_list.html'

class CategoryCreateView(CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/category_form.html'
    success_url = reverse_lazy('category-list')

class ProductListView(ListView):
    model = Product
    template_name = 'inventory/product_list.html'
    paginate_by = 20

    def get_queryset(self):
        qs = Product.objects.select_related('category').all()
        q = self.request.GET.get('q', '').strip()
        cat = self.request.GET.get('category', '').strip()

        # поиск по имени
        if q:
            qs = qs.filter(name__icontains=q)

        # фильтр по категории
        if cat:
            qs = qs.filter(category_id=cat)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = Category.objects.filter(parent__isnull=True)
        ctx['selected_q'] = self.request.GET.get('q', '')
        ctx['selected_cat'] = self.request.GET.get('category', '')
        return ctx

class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('variant-list')

class VariantCreateView(CreateView):
    model = Variant
    form_class = VariantForm
    template_name = 'inventory/variant_form.html'
    success_url = reverse_lazy('variant-list')

class StockInView(CreateView):
    model = StockTransaction
    form_class = StockInForm
    template_name = 'inventory/stockin_form.html'
    success_url = reverse_lazy('variant-list')

class SaleView(CreateView):
    model = StockTransaction
    form_class = SaleForm
    template_name = 'inventory/sale_form.html'
    success_url = reverse_lazy('variant-list')

class TransactionListView(ListView):
    model = StockTransaction
    template_name = 'inventory/transaction_list.html'
    paginate_by = 30
    ordering = ['-timestamp']


def variant_api(request, sku):
    v = get_object_or_404(Variant, sku=sku)
    return JsonResponse({
        'id': v.id,
        'sku': v.sku,
        'product': v.product.name,
        'size': v.size,
        'color': v.color,
        'price': float(v.price),
        'stock': v.stock,
    })
