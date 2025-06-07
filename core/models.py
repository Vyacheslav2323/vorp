from django.db import models
from django.contrib.auth.models import User
from classification.models import WordClassificationHistory, LearningMetrics

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
