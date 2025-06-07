from django.db import models
from django.contrib.auth.models import User

class WordClassificationRule(models.Model):
    """
    Rules for automatically classifying words based on various criteria
    """
    RULE_TYPES = [
        ('frequency', 'Word Frequency'),
        ('length', 'Word Length'),
        ('pattern', 'Word Pattern'),
        ('pos', 'Part of Speech'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    criteria = models.JSONField()  # Store rule criteria as JSON
    target_status = models.CharField(max_length=20, choices=[
        ('unknown', 'Unknown'),
        ('learning', 'Learning'),
        ('learned', 'Learned'),
    ])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}: {self.name}"

class WordClassificationHistory(models.Model):
    """
    Track history of word status changes
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    word = models.CharField(max_length=200)
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by_rule = models.ForeignKey(WordClassificationRule, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'word']),
            models.Index(fields=['changed_at']),
        ]
    
    def __str__(self):
        return f"{self.word}: {self.old_status} → {self.new_status}"

class LearningMetrics(models.Model):
    """
    Track learning metrics and progress
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    words_learned = models.IntegerField(default=0)
    words_reviewed = models.IntegerField(default=0)
    time_spent_minutes = models.IntegerField(default=0)
    accuracy_percentage = models.FloatField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'date']
    
    def __str__(self):
        return f"{self.user.username} - {self.date}: {self.words_learned} learned"
