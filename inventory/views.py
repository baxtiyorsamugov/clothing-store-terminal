from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, TemplateView, ListView
)
import json
from django.views import View
from django.shortcuts import redirect, render
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
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db.models import F

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

        # 1) Основные карточки
        ctx['total_variants']     = Variant.objects.count()
        ctx['total_stock']        = Variant.objects.aggregate(total=Sum('stock'))['total'] or 0
        ctx['total_transactions'] = StockTransaction.objects.count()

        # 2) Данные для линейного графика: продажи (OUTGOING) за последние 7 дней
        today = timezone.localdate()
        labels = []
        data_sales = []
        for i in range(6, -1, -1):
            day = today - timezone.timedelta(days=i)
            labels.append(day.strftime('%d.%m'))
            day_sales = (
                StockTransaction.objects
                .filter(transaction_type=StockTransaction.OUT,
                        timestamp__date=day)
                .aggregate(total=Sum('quantity'))['total']
                or 0
            )
            data_sales.append(day_sales)
        ctx['chart_sales_labels'] = labels      # ['19.05','20.05',...]
        ctx['chart_sales_data']   = data_sales  # [3, 5, 2, ...]

        # 3) Остатки по категориям верхнего уровня
        top_categories = Category.objects.filter(parent__isnull=True)
        pie_labels = []
        pie_data = []

        for cat in top_categories:
            # собираем все id: сам cat + его прямые subcategories
            subcats = list(cat.subcategories.all())
            ids = [cat.id] + [sc.id for sc in subcats]

            total_stock = (
                    Variant.objects
                    .filter(product__category__in=ids)
                    .aggregate(s=Sum('stock'))['s']
                    or 0
            )
            pie_labels.append(cat.name)
            pie_data.append(total_stock)

        ctx['chart_stock_labels'] = pie_labels
        ctx['chart_stock_data'] = pie_data

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

class SaleView(View):
    template_name = 'inventory/sale_form.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        items = json.loads(request.POST.get('items_json', '[]'))
        for entry in items:
            vid = entry['variant']
            qty = int(entry['quantity'])
            variant = Variant.objects.get(id=vid)

            # создаём транзакцию «Продажа» с положительным qty
            StockTransaction.objects.create(
                variant=variant,
                transaction_type=StockTransaction.OUT,
                quantity=qty,
            )
            # уменьшаем остаток
            Variant.objects.filter(id=vid).update(stock=F('stock') - qty)

        messages.success(request, f"Продано {len(items)} позиций.")
        return redirect('transaction-list')

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
