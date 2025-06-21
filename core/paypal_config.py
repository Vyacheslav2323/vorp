import paypalrestsdk
from django.conf import settings
from django.urls import reverse
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

class PayPalError(Exception):
    """Custom exception for PayPal-related errors."""
    def __init__(self, message, technical_details=None):
        self.message = message  # User-friendly message
        self.technical_details = technical_details  # Technical details for logging
        super().__init__(self.message)

def get_absolute_url(request, view_name):
    """Get absolute URL including domain for PayPal callbacks."""
    relative_url = reverse(view_name)
    if settings.DEBUG:
        domain = "http://localhost:8000"
    else:
        # Use HTTPS in production
        domain = "https://vorp.onrender.com"
    return urljoin(domain, relative_url)

def configure_paypal():
    """Configure PayPal SDK with credentials."""
    mode = "sandbox" if settings.DEBUG else "live"
    logger.info(f"Configuring PayPal in {mode} mode")
    paypalrestsdk.configure({
        "mode": mode,
        "client_id": settings.PAYPAL_CLIENT_ID,
        "client_secret": settings.PAYPAL_CLIENT_SECRET
    })
    logger.info("PayPal configuration successful")

def create_subscription_plan(request):
    """Create a PayPal billing plan for premium subscription."""
    billing_plan = paypalrestsdk.BillingPlan({
        "name": "Premium Vocabulary Learning Subscription",
        "description": "Monthly subscription for premium features",
        "type": "INFINITE",
        "payment_definitions": [{
            "name": "Monthly Premium Subscription",
            "type": "REGULAR",
            "frequency": "MONTH",
            "frequency_interval": "1",
            "amount": {
                "value": "19.99",  # Monthly subscription price
                "currency": "USD"
            },
            "cycles": "0"
        }],
        "merchant_preferences": {
            "setup_fee": {
                "value": "0",
                "currency": "USD"
            },
            "return_url": get_absolute_url(request, 'execute_subscription'),
            "cancel_url": get_absolute_url(request, 'cancel_subscription'),
            "auto_bill_amount": "YES",
            "initial_fail_amount_action": "CONTINUE",
            "max_fail_attempts": "3"
        }
    })
    
    logger.info("Creating PayPal billing plan")
    if billing_plan.create():
        logger.info(f"Billing plan created successfully with ID: {billing_plan.id}")
        return billing_plan
    else:
        error_msg = "Failed to create subscription plan"
        logger.error(f"{error_msg}: {billing_plan.error}")
        raise PayPalError(error_msg, billing_plan.error)
