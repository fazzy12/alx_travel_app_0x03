from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ListingViewSet, BookingViewSet, PaymentViewSet

# A router to register our viewsets with it.
router = DefaultRouter()
router.register(r'listings', ListingViewSet, basename='listing')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'payments', PaymentViewSet, basename='payment')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    # This includes routes like /listings/, /listings/{id}/, /bookings/, etc.
    path('', include(router.urls)),
]