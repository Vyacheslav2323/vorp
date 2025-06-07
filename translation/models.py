from django.db import models
from django.contrib.auth.models import User

class TranslationCache(models.Model):
    """
    Cache translations to avoid repeated API calls
    """
    word = models.CharField(max_length=200)
    source_language = models.CharField(max_length=10)
    target_language = models.CharField(max_length=10)
    translation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['word', 'source_language', 'target_language']
        indexes = [
            models.Index(fields=['word', 'source_language', 'target_language']),
        ]
    
    def __str__(self):
        return f"{self.word} ({self.source_language} → {self.target_language}): {self.translation}"

class UserTranslationPreference(models.Model):
    """
    Store user preferences for translation settings
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    default_source_language = models.CharField(max_length=10, default='auto')
    default_target_language = models.CharField(max_length=10, default='en')
    enable_auto_translation = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username}'s translation preferences"
