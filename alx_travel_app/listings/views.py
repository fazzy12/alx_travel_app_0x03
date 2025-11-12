import requests
import logging
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Listing, Booking, Payment
from .serializers import ListingSerializer, BookingSerializer, PaymentSerializer
from .tasks import send_confirmation_email_task
from django.shortcuts import get_object_or_404
from django.db import transaction



# Setup logger
logger = logging.getLogger(__name__)



    
# --- Chapa API Wrapper Constants ---
CHAPA_API_URL = "https://api.chapa.co/v1"
CHAPA_SECRET_KEY = settings.CHAPA_SECRET_KEY

class ListingViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for viewing, creating, updating, and deleting property Listings.
    Allows read access (GET) to all users and requires authentication 
    for CUD (Create, Update, Delete) operations.
    """
    queryset = Listing.objects.all().order_by('-created_at')
    serializer_class = ListingSerializer
    # Allows read access to all, but requires authentication for CUD operations
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def perform_create(self, serializer):
        """Set the host_id to the authenticated user making the request upon creation."""
        serializer.save(host_id=self.request.user)


class BookingViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for viewing, creating, updating, and deleting Bookings.
    Requires authentication (IsAuthenticated) for all operations.
    Modified to initiate Chapa payment upon creation.
    """
    queryset = Booking.objects.all().order_by('-created_at')
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        """Set the user_id (guest) to the authenticated user making the booking."""
        # Note: We save here, but the transaction will rollback if payment initiation fails
        serializer.save(user_id=self.request.user)
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Creates a booking, then immediately initiates a Chapa payment for it.
        """
        # 1. Create the Booking
        booking_serializer = self.get_serializer(data=request.data)
        booking_serializer.is_valid(raise_exception=True)
        self.perform_create(booking_serializer)
        booking = booking_serializer.instance
        
        try:
            # 2. Create an initial 'pending' Payment record
            tx_ref = f"ALX-TRAVEL-{booking.booking_id.hex}"
            
            payment = Payment.objects.create(
                booking_id=booking,
                user_id=request.user,
                amount=booking.total_price,
                tx_ref=tx_ref,
                status='pending'
            )
            
            # 3. Initiate Chapa Payment
            chapa_response = self._initiate_chapa_payment(payment, request.user, request)
            
            if chapa_response.status_code == 200:
                data = chapa_response.json().get('data', {})
                checkout_url = data.get('checkout_url')
                
                payment.checkout_url = checkout_url
                payment.save()
                
                # 4. Return booking details and the payment link
                response_data = booking_serializer.data
                response_data['payment_status'] = payment.status
                response_data['payment_link'] = checkout_url
                
                return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                # Payment initiation failed, cancel the created booking and payment
                payment.status = 'failed'
                payment.save()
                booking.status = 'canceled'
                booking.save()
                
                logger.error(f"Chapa initiation failed for booking {booking.booking_id}: {chapa_response.text}")
                return Response(
                    {"error": "Booking created but payment initiation failed.", "details": chapa_response.json()}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            # Rollback transaction and return error
            logger.exception(f"Exception during payment initiation for booking {booking.booking_id}: {str(e)}")
            # Ensure booking is canceled if any error occurs
            booking.status = 'canceled'
            booking.save()
            return Response({"error": "An internal error occurred during payment processing.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _initiate_chapa_payment(self, payment, user, request):
        """Helper to call the Chapa API for payment initiation."""
        headers = {
            'Authorization': f"Bearer {CHAPA_SECRET_KEY}",
            'Content-Type': 'application/json',
        }
        
        # NOTE: Using 'ETB' as the currency for the Chapa API example.
        currency = 'ETB' 
        
        data = {
            "amount": str(payment.amount),
            "currency": currency,
            "email": user.email or f"{user.username}@example.com",
            "first_name": user.first_name or user.username,
            "last_name": user.last_name or user.username,
            "tx_ref": payment.tx_ref,
            # The return URL is crucial for Chapa to redirect the user back.
            "callback_url": request.build_absolute_uri(f'/api/payments/{payment.tx_ref}/verify/'),
            "customization": {
                "title": f"Booking Payment for {payment.booking_id.property_id.name}",
                "description": f"Payment for booking {payment.booking_id.booking_id}"
            }
        }
        
        try:
            response = requests.post(f"{CHAPA_API_URL}/initialize", json=data, headers=headers, timeout=10)
            return response
        except requests.RequestException as e:
            logger.error(f"Chapa API Request failed: {e}")
            raise


class PaymentViewSet(viewsets.GenericViewSet, 
                     viewsets.mixins.ListModelMixin, 
                     viewsets.mixins.RetrieveModelMixin):
    """
    A ViewSet for managing payment records and verification via Chapa.
    """
    queryset = Payment.objects.all().order_by('-created_at')
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'tx_ref'
    
    def get_queryset(self):
        """Filter queryset to only show payments for the authenticated user."""
        return self.queryset.filter(user_id=self.request.user)

    @action(detail=True, methods=['get'], url_path='verify', permission_classes=[AllowAny])
    @transaction.atomic
    def verify_payment(self, request, tx_ref=None):
        """
        API endpoint to verify the payment status with Chapa and update the local record.
        This serves as the callback URL from Chapa. It uses AllowAny as it's a callback,
        but we check the Payment's user_id before confirmation.
        """
        # We allow a callback from Chapa's server without authentication.
        # However, a robust implementation would use a webhook and secret hash verification.
        try:
            payment = Payment.objects.get(tx_ref=tx_ref)
        except Payment.DoesNotExist:
            return Response({"error": "Transaction not found."}, status=status.HTTP_404_NOT_FOUND)

        # 1. Call Chapa Verification API
        headers = {
            'Authorization': f"Bearer {CHAPA_SECRET_KEY}",
        }
        
        try:
            response = requests.get(f"{CHAPA_API_URL}/verify/{tx_ref}", headers=headers, timeout=10)
            
            if response.status_code != 200:
                payment.status = 'failed'
                payment.save()
                logger.error(f"Chapa Verification Failed for {tx_ref}: Status {response.status_code}")
                # For a public callback, a 200 is often preferred even on failure to avoid retries
                return Response({"status": "Payment verification failed with Chapa."}, status=status.HTTP_200_OK)
                
            data = response.json()
            chapa_status = data.get('data', {}).get('status', 'failed').lower() # 'success', 'failed', 'reverted', etc.

            if data.get('status') != 'success' or chapa_status != 'success':
                # Payment was initiated but failed or is pending, update status but don't confirm booking
                payment.status = chapa_status
                payment.save()
                
                # Canceled the booking if payment is definitively failed
                if chapa_status not in ['pending', 'failed']:
                    payment.booking_id.status = 'canceled'
                    payment.booking_id.save()

                return Response({"status": payment.status, "message": data.get('message')}, status=status.HTTP_200_OK)


            # Payment is successful
            payment.status = 'completed'
            payment.chapa_transaction_id = data.get('data', {}).get('id')
            payment.save()

            # 2. Update Booking Status
            booking = payment.booking_id
            booking.status = 'confirmed'
            booking.save()
                
            send_confirmation_email_task.delay(str(booking.booking_id), booking.user_id.email)

            return Response({
                "status": "Payment completed and booking confirmed.",
                "booking_id": str(booking.booking_id),
                "transaction_id": payment.chapa_transaction_id
            }, status=status.HTTP_200_OK)

        except requests.RequestException as e:
            logger.error(f"Chapa API Request failed during verification for {tx_ref}: {e}")
            # Do not change the status here, let it remain 'pending' for manual review
            return Response({"error": "Payment verification failed due to network error."}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"Internal error during payment verification for {tx_ref}: {e}")
            return Response({"error": "An internal error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)