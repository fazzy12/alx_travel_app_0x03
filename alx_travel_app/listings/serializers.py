from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Listing, Booking, Payment


class ListingSerializer(serializers.ModelSerializer):
    """Serializer for Listing model"""
    
    class Meta:
        model = Listing
        fields = [
            'listing_id', 'host_id', 'name', 'description', 
            'location', 'price_per_night', 'created_at', 'updated_at'
        ]
        read_only_fields = ['listing_id', 'created_at', 'updated_at']
    
    def validate_price_per_night(self, value):
        """Validate price per night is positive"""
        if value <= 0:
            raise serializers.ValidationError("Price per night must be greater than 0.")
        return value


class BookingSerializer(serializers.ModelSerializer):
    """Serializer for Booking model"""
    
    class Meta:
        model = Booking
        fields = [
            'booking_id', 'property_id', 'user_id',
            'start_date', 'end_date', 'total_price', 'status', 'created_at'
        ]
        read_only_fields = ['booking_id', 'created_at']
    
    def validate(self, data):
        """Custom validation for booking dates"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date:
            if end_date <= start_date:
                raise serializers.ValidationError("End date must be after start date.")
        
        return data
    
    def validate_total_price(self, value):
        """Validate total price is positive"""
        if value <= 0:
            raise serializers.ValidationError("Total price must be greater than 0.")
        return value
    
class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model"""

    class Meta:
        model = Payment
        fields = [
            'payment_id', 'booking_id', 'user_id', 'amount', 'tx_ref', 
            'chapa_transaction_id', 'status', 'checkout_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['payment_id', 'chapa_transaction_id', 'status', 'checkout_url', 'created_at', 'updated_at']
        
    def validate_amount(self, value):
        """Validate total price is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value
