import paypalrestsdk
from django.conf import settings

def configure_paypal():
    """Configure PayPal SDK with credentials."""
    paypalrestsdk.configure({
        "mode": "sandbox" if settings.DEBUG else "live",  # sandbox or live
        "client_id": settings.PAYPAL_CLIENT_ID,
        "client_secret": settings.PAYPAL_CLIENT_SECRET
    })

def create_subscription_plan():
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
            "return_url": "http://localhost:8000/subscription/execute",
            "cancel_url": "http://localhost:8000/subscription/cancel",
            "auto_bill_amount": "YES",
            "initial_fail_amount_action": "CONTINUE",
            "max_fail_attempts": "3"
        }
    })
    
    if billing_plan.create():
        return billing_plan
    else:
        raise Exception(billing_plan.error) 