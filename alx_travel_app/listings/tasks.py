import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404
from listings.models import Booking

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def send_confirmation_email_task(self, booking_id_str, user_email):
    """
    Celery shared task to send a booking confirmation email asynchronously.
    """
    try:
        # Fetch the Booking object using the UUID string
        booking = get_object_or_404(Booking, booking_id=booking_id_str)

        subject = f"Booking Confirmation for {booking.property_id.name}"
        message = (
            f"Dear {booking.user_id.username},\n\n"
            f"Your booking (Ref: {booking.booking_id}) for {booking.property_id.name} "
            f"from {booking.start_date} to {booking.end_date} has been confirmed.\n"
            f"Total Price Paid: {booking.total_price}.\n\n"
            f"Thank you for booking with ALX Travel App!"
        )
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL, 
            [user_email],               
            fail_silently=False,
        )

        logger.info(f"✅ CONFIRMATION EMAIL SENT (Task ID: {self.request.id}): Email successfully sent to {user_email} for booking {booking_id_str}")
        return True

    except Booking.DoesNotExist:
        logger.error(f"❌ CONFIRMATION EMAIL FAILED (Task ID: {self.request.id}): Booking {booking_id_str} not found.")
        return False
    except Exception as e:
        logger.exception(f"❌ CONFIRMATION EMAIL FAILED (Task ID: {self.request.id}): Error sending email for booking {booking_id_str}: {e}")
        return self.retry(exc=e, countdown=60, max_retries=3)