# inventory/forms.py
from django import forms
from .models import Category, Product, Variant, StockTransaction

class BootstrapFormMixin:
    """
    Навешивает class="form-control" на все виджеты полей.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing + ' form-control').strip()


class CategoryForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent']


class ProductForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category']


class VariantForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Variant
        fields = ['product', 'sku', 'size', 'color', 'price', 'stock']


class StockInForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ['variant', 'quantity', 'note']

    def save(self, commit=True):
        inst = super().save(commit=False)
        inst.transaction_type = StockTransaction.IN
        if commit:
            inst.save()
        return inst


class SaleForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ['variant', 'quantity', 'note']

    def clean(self):
        data = super().clean()
        v = data.get('variant')
        q = data.get('quantity')
        if v and q and q > v.stock:
            raise forms.ValidationError("На складе недостаточно товара.")
        return data

    def save(self, commit=True):
        inst = super().save(commit=False)
        inst.transaction_type = StockTransaction.OUT
        if commit:
            inst.save()
        return inst
