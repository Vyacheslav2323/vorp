from django.db import models
from django.contrib.auth.models import User
from classification.models import WordClassificationHistory, LearningMetrics
from django.utils import timezone
from datetime import datetime, time, timedelta

# Word status choices
STATUS_CHOICES = (
    ('unknown', 'Unknown'),
    ('learning', 'Learning'),
    ('learned', 'Learned'),
)

class UserVocabulary(models.Model):
    """Model for storing a user's vocabulary words and their status."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vocabulary_words')
    word = models.CharField(max_length=100)
    translation = models.CharField(max_length=200, blank=True, null=True, help_text="Translation of the word in the user's native language")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Vocabulary'
        verbose_name_plural = 'User Vocabularies'
        unique_together = ['user', 'word']  # Each word can only appear once per user
        ordering = ['word']  # Default ordering
    
    def __str__(self):
        return f"{self.user.username}'s word: {self.word} ({self.status})"

class DailyAnalysisUsage(models.Model):
    """Model for tracking how many times a user has used the analyze feature per day."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    count = models.IntegerField(default=0)

    RESET_TIME = time(0, 0, 0)  # Midnight (00:00:00)

    class Meta:
        verbose_name = 'Daily Analysis Usage'
        verbose_name_plural = 'Daily Analysis Usages'
        unique_together = ('user', 'date')

    @classmethod
    def get_today_usage(cls, user):
        current_time = timezone.now()
        # If current time is before reset time, use previous day's date
        if current_time.time() < cls.RESET_TIME:
            today = (current_time - timedelta(days=1)).date()
        else:
            today = current_time.date()
        usage, _ = cls.objects.get_or_create(user=user, date=today)
        return usage

    @classmethod
    def can_analyze(cls, user):
        usage = cls.get_today_usage(user)
        return usage.count < 5  # 5 times per day limit

    @classmethod
    def get_time_until_reset(cls):
        """Get the time remaining until the next reset."""
        now = timezone.now()
        if now.time() < cls.RESET_TIME:
            # Reset is today
            next_reset = datetime.combine(now.date(), cls.RESET_TIME)
        else:
            # Reset is tomorrow
            next_reset = datetime.combine(now.date() + timedelta(days=1), cls.RESET_TIME)
        
        # Convert to timezone-aware datetime
        next_reset = timezone.make_aware(next_reset)
        return next_reset - now

    def increment(self):
        self.count += 1
        self.save()

    def __str__(self):
        return f"{self.user.username}'s analysis usage for {self.date}: {self.count} times"

class Subscription(models.Model):
    """Model for managing user subscriptions."""
    SUBSCRIPTION_TYPES = (
        ('free', 'Free'),
        ('premium', 'Premium'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_TYPES, default='free')
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    paypal_subscription_id = models.CharField(max_length=100, null=True, blank=True)
    last_payment_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'

    @property
    def is_premium(self):
        """Check if user has an active premium subscription."""
        return (
            self.subscription_type == 'premium' and 
            self.is_active and 
            (self.end_date is None or self.end_date > timezone.now())
        )

    def __str__(self):
        return f"{self.user.username}'s {self.subscription_type} subscription"

class PaymentHistory(models.Model):
    """Model for tracking payment history."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    paypal_transaction_id = models.CharField(max_length=100)
    status = models.CharField(max_length=20, default='completed')

    class Meta:
        verbose_name = 'Payment History'
        verbose_name_plural = 'Payment Histories'
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment of {self.amount} {self.currency} by {self.user.username}"
