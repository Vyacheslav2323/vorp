import paypalrestsdk
from django.conf import settings
from django.urls import reverse
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

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
    
    try:
        paypalrestsdk.configure({
            "mode": mode,
            "client_id": settings.PAYPAL_CLIENT_ID,
            "client_secret": settings.PAYPAL_CLIENT_SECRET
        })
        logger.info("PayPal configuration successful")
    except Exception as e:
        logger.error(f"PayPal configuration error: {str(e)}")
        raise

def create_subscription_plan(request):
    """Create a PayPal billing plan for premium subscription."""
    try:
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
                    "value": "9.99",  # Monthly subscription price
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
            error_msg = billing_plan.error
            logger.error(f"Failed to create billing plan: {error_msg}")
            raise Exception(error_msg)
            
    except Exception as e:
        logger.error(f"Error creating subscription plan: {str(e)}")
        raise 