from django.db import models
from django.contrib.auth.models import User


class TourismUser(models.Model):
    auth_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

    ROLE_CHOICES = (
        ('tourist', 'Tourist'),
        ('guide', 'Guide'),
        ('vendor', 'Vendor'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    password = models.CharField(max_length=200)

    language = models.CharField(max_length=100, blank=True, null=True)
    area_of_expertise = models.CharField(max_length=200, blank=True, null=True)

    business_name = models.CharField(max_length=200, blank=True, null=True)
    business_category = models.CharField(max_length=200, blank=True, null=True)
    location = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.role})"


class Product(models.Model):
    vendor = models.ForeignKey(TourismUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    price = models.FloatField()
    stock = models.IntegerField(default=0)
    category = models.CharField(max_length=100)

    image_url = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)

    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.vendor.name})"


class Order(models.Model):
    tourist = models.ForeignKey(TourismUser, on_delete=models.CASCADE, null=True, blank=True)
    vendor_user = models.ForeignKey(TourismUser, related_name="vendor_orders", on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)

    quantity = models.IntegerField(default=1)
    total_price = models.FloatField(default=0)

    delivery_address = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)

    status = models.CharField(max_length=50, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)


class FavoritePlace(models.Model):
    user = models.ForeignKey(TourismUser, on_delete=models.CASCADE)
    place_name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    rating = models.FloatField(default=0)
    image_url = models.TextField()

    def __str__(self):
        return f"{self.user.name} - {self.place_name}"


class Feedback(models.Model):
    user = models.ForeignKey(TourismUser, on_delete=models.CASCADE)
    rating = models.IntegerField()
    feedback_type = models.CharField(max_length=50)
    subject = models.CharField(max_length=200)
    feedback = models.TextField()
    recommend = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.subject

class Booking(models.Model):
    tourist = models.ForeignKey(TourismUser, on_delete=models.CASCADE)
    package_name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    date = models.DateField()
    travelers = models.IntegerField(default=1)
    email = models.EmailField()
    status = models.CharField(max_length=50, default="Confirmed")  # Confirmed / Cancelled
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.package_name} - {self.tourist.name}"