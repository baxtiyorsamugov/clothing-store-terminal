from django.db import models
import qrcode
from io import BytesIO
import base64
from django.core.exceptions import ValidationError
from PIL import Image, ImageDraw, ImageFont

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
        # 1) Генерация чистого QR
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(self.sku)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        # 2) Подписи — две строки
        lines = [
            f"SKU: {self.sku}",
            f"Size: {self.size}   Price: {self.price}"
        ]

        # 3) Шрифт: пробуем загрузить DejaVu Sans Bold размером 16,
        #    если нет — fallback на load_default()
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 16)
        except IOError:
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(qr_img)

        # 4) Замеряем каждую строку
        bboxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
        widths  = [bx[2] - bx[0] for bx in bboxes]
        heights = [bx[3] - bx[1] for bx in bboxes]
        text_width  = max(widths)
        text_height = sum(heights) + (len(lines) - 1) * 4  # плюс 4px между строками

        # 5) Новый холст
        new_width  = max(qr_img.width, text_width + 20)
        new_height = qr_img.height + text_height + 10
        new_img = Image.new("RGB", (new_width, new_height), "white")

        # 6) Вставляем QR в центр
        qr_x = (new_width - qr_img.width) // 2
        new_img.paste(qr_img, (qr_x, 0))

        # 7) Рисуем текст под QR
        draw = ImageDraw.Draw(new_img)
        y = qr_img.height + 5
        for i, line in enumerate(lines):
            line_width  = widths[i]
            x = (new_width - line_width) // 2
            draw.text((x, y), line, fill="black", font=font)
            y += heights[i] + 4  # следующий y

        # 8) Сохраняем в PNG→base64
        buffer = BytesIO()
        new_img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

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
    transaction_type = models.CharField(max_length=3, choices=TYPE_CHOICES, default=OUT)
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
