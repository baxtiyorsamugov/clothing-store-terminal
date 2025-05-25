from django.db import models
import qrcode
from io import BytesIO
import base64
from django.core.exceptions import ValidationError

class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        related_name='subcategories', on_delete=models.CASCADE
    )

    def __str__(self):
        return self.name if not self.parent else f"{self.parent} → {self.name}"

class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(
        Category, null=True, blank=True,
        related_name='products', on_delete=models.SET_NULL
    )

    def __str__(self):
        return self.name

class Variant(models.Model):
    product = models.ForeignKey(
        Product, related_name='variants', on_delete=models.CASCADE
    )
    sku = models.CharField(max_length=100, unique=True)
    size = models.CharField(max_length=50)
    color = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)

    def qr_code_base64(self):
        """
        Возвращает PNG QR-код, закодированный в base64,
        со значением self.sku.
        """
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(self.sku)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        img_b64 = base64.b64encode(buf.getvalue()).decode()
        return img_b64

    def __str__(self):
        return f"{self.product.name} ({self.size}, {self.color})"

class StockTransaction(models.Model):
    IN = 'IN'
    OUT = 'OUT'
    TYPE_CHOICES = [
        (IN, 'Приёмка'),
        (OUT, 'Продажа'),
    ]

    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    quantity = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True)

    def clean(self):
        if self.transaction_type == self.OUT and self.quantity > self.variant.stock:
            raise ValidationError("Недостаточно на складе для списания.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        if self.transaction_type == self.IN:
            self.variant.stock += self.quantity
        else:
            self.variant.stock -= self.quantity
        self.variant.save()
