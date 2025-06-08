from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from datetime import date
from django.views.decorators.http import require_POST
from django.utils import timezone

from .theme_config import get_theme_context
from vocabulary.models import UserVocabulary
from translation.word_processor import word_processor
from translation.vocabulary_service import vocabulary_service
from .text_utils import demo_highlight_text, highlight_text_html_with_lemmas
from .models import WordClassificationHistory, LearningMetrics, DailyAnalysisUsage, Subscription, PaymentHistory
from .paypal_config import configure_paypal, create_subscription_plan
import paypalrestsdk

import logging
logger = logging.getLogger(__name__)


def index(request):
    context = get_theme_context()
    return render(request, 'core/index.html', context)


def login_view(request):
    context = get_theme_context()
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if not remember:
                request.session.set_expiry(0)
            return redirect('index')
        else:
            context['error'] = "Invalid username or password. Please try again."

    return render(request, 'core/login.html', context)


def logout_view(request):
    logout(request)
    return redirect('login')


def register_view(request):
    context = get_theme_context()
    context['native_languages'] = [
        {'code': 'en', 'name': 'English'},
        {'code': 'ko', 'name': 'Korean'},
        {'code': 'zh', 'name': 'Chinese'},
        {'code': 'ru', 'name': 'Russian'},
    ]
    context['target_languages'] = [
        {'code': 'en', 'name': 'English'},
        {'code': 'ko', 'name': 'Korean'},
    ]

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        native_language = request.POST.get('native_language')
        target_language = request.POST.get('target_language')

        if not (username and email and password1 and password2 and native_language and target_language):
            context['error'] = "All fields are required."
            return render(request, 'core/register.html', context)

        if password1 != password2:
            context['error'] = "Passwords do not match."
            return render(request, 'core/register.html', context)

        if native_language == target_language:
            context['error'] = "Native and target languages cannot be the same."
            return render(request, 'core/register.html', context)

        if User.objects.filter(username=username).exists():
            context['error'] = "Username already exists."
            return render(request, 'core/register.html', context)

        if User.objects.filter(email=email).exists():
            context['error'] = "Email already registered."
            return render(request, 'core/register.html', context)

        try:
            user = User.objects.create_user(username=username, email=email, password=password1)
            # (In a real app, you'd save native/target in a profile model.)
            user = authenticate(request, username=username, password=password1)
            if user:
                login(request, user)
                return redirect('index')
            else:
                return redirect('login')
        except Exception as e:
            context['error'] = f"Registration error: {e}"
            return render(request, 'core/register.html', context)

    return render(request, 'core/register.html', context)


@login_required
def vocabulary_test(request):
    """
    Vocabulary test view for Korean → English translation using OpenAI word processing.

    On POST: store the submitted text into session so that after marking words
    as "learning" or "learned," a page refresh will re-analyse the same text.
    """
    # Get theme context (dark/light mode)
    context = get_theme_context()
    context['title'] = 'Vocabulary Test - Korean → English'

    source_lang = 'ko'
    target_lang = 'en'

    # Check daily limit on POST requests
    if request.method == 'POST':
        # Check if user has reached their daily limit
        if not DailyAnalysisUsage.can_analyze(request.user):
            time_until_reset = DailyAnalysisUsage.get_time_until_reset()
            hours, remainder = divmod(time_until_reset.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            messages.error(
                request, 
                f"You've reached your daily limit of 5 analyses. The limit will reset in {hours:02d}:{minutes:02d}:{seconds:02d}."
            )
            return redirect('vocabulary_test')
        
        user_text = request.POST.get('text', '').strip()
        # Save whatever the user submitted into the session (even if blank string)
        request.session['vocab_last_text'] = user_text
        
        # Increment the usage counter
        usage = DailyAnalysisUsage.get_today_usage(request.user)
        usage.increment()
    else:
        # On GET, try to reuse the last‐submitted text from session
        user_text = request.session.get('vocab_last_text', '').strip()

    # Get the current usage count for display
    current_usage = DailyAnalysisUsage.get_today_usage(request.user)
    context['analyses_remaining'] = max(5 - current_usage.count, 0)
    context['analyses_used'] = current_usage.count

    # Get time until next reset
    time_until_reset = DailyAnalysisUsage.get_time_until_reset()
    hours, remainder = divmod(time_until_reset.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    context['reset_in'] = {
        'hours': hours,
        'minutes': minutes,
        'seconds': seconds
    }

    # 2️⃣ If there's no text in session (or user submitted blank), fall back to sample:
    if not user_text:
        user_text = """부서지마! 바라봐 주세요.
안녕하세요. 저는 한국어를 공부하고 있어요.
먹고 싶어요. 가고 싶어요."""

    context['original_text'] = user_text

    # 3️⃣ Build the user_vocabulary dict from the database:
    user_vocabulary = {}
    if request.user.is_authenticated:
        vocab_qs = UserVocabulary.objects.filter(user=request.user, language=source_lang)
        user_vocabulary = {
            vocab.lemma: {
                'status': vocab.status,
                'translation': vocab.translation or '',
                'word': vocab.word,
                'vocabulary_form': vocab.vocabulary_form or vocab.lemma
            }
            for vocab in vocab_qs
        }

    # 4️⃣ Run the OpenAI‐powered processing on exactly this `user_text`:
    if user_text:
        result = word_processor.process_text_for_vocabulary_test(user_text, user_vocabulary)
        context.update({
            'highlighted_html': result['html'],
            'stats': result['stats'],
            'word_analysis': result.get('word_analysis', {}),
            'matched_words': result.get('matched_words', {}),
        })

    return render(request, 'core/vocabulary_test.html', context)


@login_required
def subscription_page(request):
    """Display subscription options and current status."""
    try:
        subscription = Subscription.objects.get(user=request.user)
    except Subscription.DoesNotExist:
        subscription = None

    context = {
        'subscription': subscription,
        'is_premium': subscription.is_premium if subscription else False,
    }
    return render(request, 'core/subscription.html', context)

@login_required
def create_subscription(request):
    """Create a PayPal subscription."""
    try:
        configure_paypal()
        billing_plan = create_subscription_plan()
        
        # Activate the plan
        if billing_plan.state == 'CREATED':
            billing_plan.activate()

        # Create agreement
        agreement = paypalrestsdk.BillingAgreement({
            "name": "Premium Vocabulary Learning Subscription",
            "description": "Monthly subscription for premium features",
            "start_date": (timezone.now() + timezone.timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "plan": {
                "id": billing_plan.id
            },
            "payer": {
                "payment_method": "paypal"
            }
        })

        if agreement.create():
            for link in agreement.links:
                if link.rel == "approval_url":
                    return redirect(link.href)
        else:
            logger.error(f"Failed to create agreement: {agreement.error}")
            return JsonResponse({'error': 'Failed to create subscription'}, status=400)

    except Exception as e:
        logger.error(f"Subscription creation error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def execute_subscription(request):
    """Execute the PayPal subscription agreement."""
    token = request.GET.get('token')
    if not token:
        return JsonResponse({'error': 'No token provided'}, status=400)

    try:
        agreement = paypalrestsdk.BillingAgreement.execute(token)
        
        # Create or update subscription
        subscription, created = Subscription.objects.get_or_create(
            user=request.user,
            defaults={
                'subscription_type': 'premium',
                'is_active': True,
                'paypal_subscription_id': agreement.id,
                'end_date': timezone.now() + timezone.timedelta(days=30)
            }
        )

        if not created:
            subscription.subscription_type = 'premium'
            subscription.is_active = True
            subscription.paypal_subscription_id = agreement.id
            subscription.end_date = timezone.now() + timezone.timedelta(days=30)
            subscription.save()

        # Record payment
        PaymentHistory.objects.create(
            user=request.user,
            subscription=subscription,
            amount=9.99,
            currency='USD',
            paypal_transaction_id=agreement.id
        )

        return redirect('subscription_success')

    except Exception as e:
        logger.error(f"Subscription execution error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def cancel_subscription(request):
    """Cancel the PayPal subscription."""
    try:
        subscription = Subscription.objects.get(user=request.user)
        if subscription.paypal_subscription_id:
            agreement = paypalrestsdk.BillingAgreement.find(subscription.paypal_subscription_id)
            if agreement.cancel():
                subscription.is_active = False
                subscription.save()
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'error': agreement.error}, status=400)
    except Exception as e:
        logger.error(f"Subscription cancellation error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

# (Other views remain unchanged…)
