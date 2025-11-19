from django.shortcuts import render
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import viewsets
from .models import TourismUser, FavoritePlace,Order
from .serializers import TourismUserSerializer
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.db import models
from .models import Product,TourismUser
from .serializers import ProductSerializer
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from .models import Feedback
from django.db.models import Avg, Count
from .models import Feedback, TourismUser
from .models import Booking, TourismUser
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.http import JsonResponse
import json
from datetime import datetime
from django.conf import settings
from django.core.mail import EmailMultiAlternatives


# ============================
# USER VIEWSET
# ============================
class TourismUserViewSet(viewsets.ModelViewSet):
    queryset = TourismUser.objects.all()
    serializer_class = TourismUserSerializer

    def create(self, request, *args, **kwargs):
        data = request.data

        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        role = data.get("role")

        # 1. Prevent duplicate email registration
        if User.objects.filter(username=email).exists():
            return Response({"success": False, "message": "Email already registered"}, status=400)

        # 2. Create user in Django auth_user table
        auth_user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name
        )

        # 3. Create a TourismUser record (main table)
        tourism_user = TourismUser.objects.create(
            auth_user=auth_user,
            role=role,
            name=name,
            email=email,
            phone=data.get("phone"),
            password=password,  # (Later we will hash it)

            # FIELDS IF USER IS A GUIDE
            language=data.get("language"),
            area_of_expertise=data.get("area_of_expertise"),

            # FIELDS IF USER IS A VENDOR
            business_name=data.get("business_name"),
            business_category=data.get("business_category"),
            location=data.get("location"),   # <-- LOCATION ADDED HERE
        )

        serializer = self.get_serializer(tourism_user)

        return Response(
            {
                "success": True,
                "message": "Signup successful",
                "user": serializer.data
            },
            status=201
        )


# ============================
# LOGIN
# ============================
@csrf_exempt
def login_user(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            email = data.get("email")
            password = data.get("password")

            if not email or not password:
                return JsonResponse({"ok": False, "message": "Email and password required"}, status=400)

            try:
                user = TourismUser.objects.get(email=email)
            except TourismUser.DoesNotExist:
                return JsonResponse({"ok": False, "message": "User not found"}, status=404)

            if user.password != password:
                return JsonResponse({"ok": False, "message": "Incorrect password"}, status=400)

            return JsonResponse({
                "ok": True,
                "message": "Login successful",
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role
                }
            }, status=200)

        except Exception as e:
            return JsonResponse({"ok": False, "message": str(e)}, status=500)

    return JsonResponse({"ok": False, "message": "Invalid request"}, status=400)


# ============================
# DASHBOARD STATS
# ============================
@csrf_exempt
def tourist_stats(request, user_id):
    try:
        from .models import Order  # ensure import

        favorites = FavoritePlace.objects.filter(user_id=user_id).count()
        orders = Order.objects.filter(tourist_id=user_id).count()

        stats = {
            "favorites": favorites,
            "orders": orders,
            "visited": 0,
            "reviews": 0,
        }

        return JsonResponse(stats)

    except:
        return JsonResponse({"error": "Invalid ID"}, status=400)



# ============================
# GET FAVORITE PLACES
# ============================
@csrf_exempt
def get_favorite_places(request, user_id):
    if request.method == "GET":
        favorites = FavoritePlace.objects.filter(user_id=user_id)

        data = []
        for fav in favorites:
            data.append({
                "id": fav.id,
                "place_name": fav.place_name,
                "city": fav.city,
                "rating": fav.rating,
                "image_url": fav.image_url,
            })

        return JsonResponse({"favorites": data})

    return JsonResponse({"error": "Only GET allowed"}, status=400)


# ============================
# DELETE FAVORITE PLACE
# ============================
@csrf_exempt
def delete_favorite(request, fav_id):
    if request.method == "DELETE":
        try:
            fav = FavoritePlace.objects.get(id=fav_id)
            fav.delete()
            return JsonResponse({"success": True})
        except FavoritePlace.DoesNotExist:
            return JsonResponse({"success": False, "error": "Favorite not found"})

    return JsonResponse({"success": False, "error": "Invalid method"})

@csrf_exempt
def add_favorite(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            user_id = data.get("user_id")
            place_name = data.get("place_name")
            city = data.get("city")
            rating = data.get("rating")
            image_url = data.get("image_url")

            # Prevent duplicates
            exists = FavoritePlace.objects.filter(user_id=user_id, place_name=place_name).exists()
            if exists:
                return JsonResponse({"success": False, "message": "Already added to favorites"})

            fav = FavoritePlace.objects.create(
                user_id=user_id,
                place_name=place_name,
                city=city,
                rating=rating,
                image_url=image_url
            )

            return JsonResponse({"success": True, "message": "Added to favorites"})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid method"})

@csrf_exempt
def place_order(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            user_id = data.get("user_id")
            item_name = data.get("item_name")
            vendor_name = data.get("vendor_name")
            quantity = data.get("quantity", 1)
            price = data.get("price", 0)
            image_url = data.get("image_url")

            # ============================
            # CHECK IF VENDOR EXISTS
            # ============================
            try:
                vendor = TourismUser.objects.get(name=vendor_name, role="vendor")
            except TourismUser.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "message": "Vendor does not exist. Please order only from registered vendors."
                }, status=400)

            # ============================
            # CREATE ORDER
            # ============================
            order = Order.objects.create(
                user_id=user_id,
                item_name=item_name,
                vendor_name=vendor_name,
                quantity=quantity,
                price=price,
                status="Processing",
                image_url=image_url
            )

            return JsonResponse({"success": True, "message": "Order placed successfully!"})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid method"})

@csrf_exempt
def vendor_dashboard(request, vendor_id):
    try:
        vendor = TourismUser.objects.get(id=vendor_id, role="vendor")

        # Count products
        total_products = Product.objects.filter(vendor=vendor).count()

        # Total revenue
        total_revenue = Order.objects.filter(vendor_name=vendor.name, status="Delivered") \
                                     .aggregate(models.Sum("price"))["price__sum"] or 0

        # Pending orders
        pending_orders = Order.objects.filter(vendor_name=vendor.name, status="Processing").count()

        # Recent orders (latest 5)
        recent_orders_qs = Order.objects.filter(vendor_name=vendor.name).order_by("-id")[:5]

        recent_orders = []
        for o in recent_orders_qs:
            recent_orders.append({
                "item_name": o.item_name,
                "buyer_name": o.user.first_name if o.user else "Unknown",
                "status": o.status
            })

        return JsonResponse({
            "success": True,
            "dashboard": {
                "total_products": total_products,
                "pending_orders": pending_orders,
                "total_revenue": total_revenue,
                "recent_orders": recent_orders
            }
        })

    except TourismUser.DoesNotExist:
        return JsonResponse({"success": False, "message": "Vendor not found"}, status=404)

@csrf_exempt
def add_product(request):
    if request.method == "POST":
        vendor_id = request.POST.get("vendor_id")
        name = request.POST.get("name")
        category = request.POST.get("category")
        description = request.POST.get("description")
        price = request.POST.get("price")
        stock = request.POST.get("stock", 0)

        image = request.FILES.get("image")  # <-- VERY IMPORTANT

        try:
            vendor = TourismUser.objects.get(id=vendor_id)
        except TourismUser.DoesNotExist:
            return JsonResponse({"success": False, "message": "Vendor not found"})

        product = Product.objects.create(
            vendor=vendor,
            name=name,
            category=category,
            description=description,
            price=price,
            stock=stock,
            image=image,      # <-- MUST BE SAVED HERE
        )

        # If image exists, store its URL
        if image:
            product.image_url = request.build_absolute_uri(product.image.url)
            product.save()

        return JsonResponse({"success": True, "message": "Product added successfully!"})

    return JsonResponse({"success": False, "message": "Invalid method"})



@csrf_exempt
def list_vendor_products(request, vendor_id):
    try:
        products = Product.objects.filter(vendor_id=vendor_id)
        serializer = ProductSerializer(products, many=True)
        return JsonResponse({"products": serializer.data})
    except:
        return JsonResponse({"products": []})


@csrf_exempt
def update_product(request, product_id):
    if request.method == "PUT":
        try:
            product = Product.objects.get(id=product_id)
            data = json.loads(request.body.decode("utf-8"))

            product.name = data.get("name", product.name)
            product.price = data.get("price", product.price)
            product.category = data.get("category", product.category)
            product.description = data.get("description", product.description)
            product.image_url = data.get("image_url", product.image_url)
            product.save()

            return JsonResponse({"success": True, "message": "Product updated!"})

        except Product.DoesNotExist:
            return JsonResponse({"success": False, "message": "Product not found"})

    return JsonResponse({"success": False, "message": "Invalid method"})


@csrf_exempt
def delete_product(request, product_id):
    if request.method == "DELETE":
        try:
            product = Product.objects.get(id=product_id)
            product.delete()
            return JsonResponse({"success": True, "message": "Product deleted"})
        except Product.DoesNotExist:
            return JsonResponse({"success": False, "message": "Product not found"})

    return JsonResponse({"success": False, "message": "Invalid method"})

@csrf_exempt
def get_products_by_location(request, location):
    # location is coming from URL path

    if not location:
        return JsonResponse({"success": False, "message": "Location required"}, status=400)

    # Find vendors
    vendors = TourismUser.objects.filter(role="vendor", location__icontains=location)

    if not vendors.exists():
        return JsonResponse({"success": True, "products": []})

    # Get all products for these vendors
    products = Product.objects.filter(vendor__in=vendors)

    serializer = ProductSerializer(products, many=True)

    return JsonResponse({"success": True, "products": serializer.data})

@csrf_exempt
def create_order(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Only POST allowed"})

    data = json.loads(request.body)

    tourist_id = data.get("tourist_id")
    product_id = data.get("product_id")
    quantity = data.get("quantity")
    address = data.get("delivery_address")
    phone = data.get("phone")

    if not all([tourist_id, product_id, quantity, address, phone]):
        return JsonResponse({"success": False, "message": "Missing required fields"})

    try:
        tourist = TourismUser.objects.get(id=tourist_id)
        product = Product.objects.get(id=product_id)
        vendor_user = product.vendor
    except TourismUser.DoesNotExist:
        return JsonResponse({"success": False, "message": "Tourist not found"})
    except Product.DoesNotExist:
        return JsonResponse({"success": False, "message": "Product not found"})

    total_price = product.price * int(quantity)

    order = Order.objects.create(
        tourist=tourist,
        vendor_user=vendor_user,
        product=product,
        quantity=quantity,
        delivery_address=address,
        phone=phone,
        total_price=total_price
    )

    return JsonResponse({"success": True, "order_id": order.id})
    
@csrf_exempt
def get_tourist_orders(request, tourist_id):
    try:
        orders = Order.objects.filter(tourist_id=tourist_id).select_related("product", "vendor_user")

        order_list = []
        for o in orders:
            order_list.append({
                "id": o.id,
                "product_name": o.product.name if o.product else "",
                "vendor_name": o.vendor_user.name if o.vendor_user else "",
                "total_price": o.total_price,
                "quantity": o.quantity,
                "status": o.status,
                "created_at": o.created_at.strftime("%Y-%m-%d"),
                "image_url": o.product.image_url if o.product else "",
                "image": o.product.image.url if o.product and o.product.image else ""
            })

        return JsonResponse({"success": True, "orders": order_list})

    except Exception as e:
        print("ERROR:", e)
        return JsonResponse({"success": False, "message": "Error fetching orders"})
    
@api_view(["GET"])
def vendor_orders(request, vendor_id):
    try:
        orders = Order.objects.filter(vendor_user_id=vendor_id).order_by("-id")

        response = []
        for o in orders:
            response.append({
                "id": o.id,
                "product_name": o.product.name,
                "image": o.product.image.url if o.product.image else "",
                "image_url": o.product.image_url,
                "buyer_name": o.tourist.name if o.tourist else "",
                "delivery_address": o.delivery_address,
                "phone": o.phone,
                "quantity": o.quantity,
                "total_price": o.total_price,
                "status": o.status,
                "date": o.created_at.strftime("%Y-%m-%d")
            })

        return Response({"success": True, "orders": response})

    except Exception as e:
        return Response({"success": False, "error": str(e)})

    
@api_view(["POST"])
def update_order_status(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({"success": False, "message": "Order not found"})

    new_status = request.data.get("status")

    if not new_status:
        return Response({"success": False, "message": "No status provided"})

    order.status = new_status
    order.save()

    return Response({"success": True, "message": "Status updated successfully"})

    
@api_view(["GET"])
def vendor_dashboard(request, vendor_id):
    try:
        vendor = TourismUser.objects.get(id=vendor_id, role="vendor")

        products = Product.objects.filter(vendor=vendor)
        orders = Order.objects.filter(vendor_user=vendor)

        pending_orders = orders.filter(status="Pending").count()

        # CORRECT REVENUE CALCULATION 👇
        total_revenue = 0
        for o in orders:
            if o.status == "Delivered":
                total_revenue += o.quantity * o.product.price

        # recent 5 orders
        recent = orders.order_by("-id")[:5]

        recent_orders = [
            {
                "item_name": o.product.name,
                "buyer_name": o.tourist.name if o.tourist else "Unknown",
                "status": o.status,
                "date": o.created_at.strftime("%Y-%m-%d"),
            }
            for o in recent
        ]

        return Response({
            "success": True,
            "dashboard": {
                "total_products": products.count(),
                "pending_orders": pending_orders,
                "total_revenue": total_revenue,
                "recent_orders": recent_orders
            }
        })

    except TourismUser.DoesNotExist:
        return Response({"success": False, "message": "Vendor not found"})

    
@api_view(["POST"])
def cancel_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)

        # ❌ If already delivered, cannot cancel
        if order.status == "Delivered":
            return Response({"success": False, "message": "Delivered orders cannot be cancelled"})

        order.status = "Cancelled"
        order.save()

        return Response({"success": True, "message": "Order cancelled successfully"})

    except Order.DoesNotExist:
        return Response({"success": False, "message": "Order not found"})
    
@api_view(["POST"])
def submit_feedback(request):
    try:
        user_id = request.data.get("user_id")
        rating = request.data.get("rating")
        feedback_type = request.data.get("feedback_type")
        subject = request.data.get("subject")
        feedback_text = request.data.get("feedback")
        recommend = request.data.get("recommend")

        if not user_id:
            return Response({"success": False, "message": "User ID missing"})

        user = TourismUser.objects.get(id=user_id)

        fb = Feedback.objects.create(
            user=user,
            rating=rating,
            feedback_type=feedback_type,
            subject=subject,
            feedback=feedback_text,
            recommend=recommend
        )

        return Response({"success": True, "message": "Feedback submitted!"})

    except Exception as e:
        return Response({"success": False, "message": str(e)})
    
@api_view(["GET"])
def get_user_feedback(request, user_id):
    feedbacks = Feedback.objects.filter(user_id=user_id).order_by("-id")

    response = []
    for fb in feedbacks:
        response.append({
            "rating": fb.rating,
            "type": fb.feedback_type,
            "subject": fb.subject,
            "feedback": fb.feedback,
            "recommend": fb.recommend,
            "created_at": fb.created_at.strftime("%b %d, %Y")
        })

    return Response({"success": True, "feedbacks": response})

def get_feedback_stats(request, user_id):
    feedbacks = Feedback.objects.filter(user_id=user_id)

    total_reviews = feedbacks.count()
    avg_rating = feedbacks.aggregate(avg=Avg("rating"))["avg"] or 0

    return JsonResponse({
        "success": True,
        "reviews": total_reviews,
        "avg_rating": round(avg_rating, 1)
    })


@csrf_exempt
def create_booking(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid method"})

    data = json.loads(request.body)

    try:
        tourist_id = data.get("tourist_id")
        tourist = TourismUser.objects.get(id=tourist_id)

        booking = Booking.objects.create(
            tourist=tourist,
            package_name=data.get("package_name"),
            location=data.get("location"),
            date=datetime.strptime(data.get("date"), "%Y-%m-%d"),
            travelers=data.get("travelers"),
            email=data.get("email")
        )

        # SEND EMAIL
        send_mail(
            subject="Your Booking Confirmed!",
            message=(
                f"Hello {tourist.name},\n\n"
                f"Your booking for {booking.package_name} is confirmed.\n"
                "Wait for the next mail for further process.\n"
                "Get tuned and stay with us!\n\n"
                "Smart Tourism Assistant Team"
            ),
            from_email="smarttourismassistant@gmail.com",
            recipient_list=[booking.email],
            fail_silently=False,
        )

        return JsonResponse({"success": True, "message": "Booking Saved & Email Sent"})

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})
    
@csrf_exempt
def send_booking_email(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))

        name = data.get('name', 'Traveler')
        email = data.get('email')
        package_name = data.get('package_name', 'Travel Package')

        subject = "🎉 Your Booking is Confirmed! – Smart Tourism Assistant"

        html_content = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; background:#f5f7fa;">

            <div style="max-width: 600px; margin: auto; background: white; padding: 25px; 
                         border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">

                <h2 style="color:#2563eb; text-align:center; margin-bottom:10px;">
                    Smart Tourism Assistant
                </h2>

                <p style="font-size: 16px; color:#333;">Hello <b>{name}</b>,</p>

                <p style="font-size: 15px; color:#444;">
                    We're excited to let you know that your booking has been 
                    <span style="color: green;"><b>successfully confirmed!</b></span>
                </p>

                <div style="
                    background:#f0f9ff;
                    padding:15px; 
                    margin:20px 0;
                    border-left:4px solid #2563eb;
                    border-radius:6px;">
                    <p style="margin:0; font-size:16px; color:#2563eb;">
                        <b>📌 Booking Details</b>
                    </p>
                    <p style="margin:5px 0 0; font-size:15px; color:#333;">
                        <b>Package:</b> {package_name}<br>
                        <b>Status:</b> Confirmed
                    </p>
                </div>

                <p style="font-size:15px; color:#444;">
                    Our team is preparing the next steps for your trip.
                    You will receive another email soon with detailed travel instructions.
                </p>

                <p style="font-size:15px; color:#444; margin-top:20px;">
                    Thank you for choosing <b>Smart Tourism Assistant</b>!  
                    <br>We are excited to be part of your journey. 🌍✨
                </p>

                <hr style="margin:25px 0; border:0; border-top:1px solid #ddd;">

                <p style="text-align:center; font-size:13px; color:#777;">
                    © 2025 Smart Tourism Assistant<br>
                    Making your travel smarter, easier & memorable.
                </p>
            </div>
        </div>
        """

        # Send HTML email
        email_msg = EmailMultiAlternatives(
            subject=subject,
            body="Your booking is confirmed.",  # fallback for non-HTML clients
            from_email=settings.EMAIL_HOST_USER,
            to=[email]
        )
        email_msg.attach_alternative(html_content, "text/html")
        email_msg.send()

        return JsonResponse({"success": True})

    except Exception as e:
        print("Email Sending Error:", e)
        return JsonResponse({"success": False, "message": str(e)}, status=500)